#!/usr/bin/env python3
"""Shared helpers for cross-project-plane skill scripts (stdlib only)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_AMBIGUOUS = 3
EXIT_FOREIGN = 4
EXIT_API = 5

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "when",
    "have", "has", "are", "was", "were", "will", "can", "not", "but",
    "via", "using", "use", "add", "fix", "update", "make", "need",
}


def home() -> Path:
    override = os.environ.get("CROSS_PROJECT_PLANE_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "cross-project-plane"


def ensure_home() -> Path:
    root = home()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(root, 0o700)
    except OSError:
        pass
    return root


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(obj: Any, code: int = EXIT_OK) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
    raise SystemExit(code)


def fail(code: int, error: str, **extra: Any) -> None:
    payload = {"ok": False, "error": error, **extra}
    emit(payload, code)


def load_credentials() -> dict[str, str]:
    ensure_home()
    cred_path = home() / "credentials"
    creds: dict[str, str] = {}
    if cred_path.exists():
        mode = cred_path.stat().st_mode & 0o777
        if mode & 0o077:
            fail(
                EXIT_CONFIG,
                f"credentials file is too open ({oct(mode)}); chmod 600 required",
                path=str(cred_path),
            )
        for line in cred_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            creds[k.strip()] = v.strip()
    if os.environ.get("PLANE_API_KEY"):
        creds["PLANE_API_KEY"] = os.environ["PLANE_API_KEY"]
    if os.environ.get("PLANE_API_BASE"):
        creds["PLANE_API_BASE"] = os.environ["PLANE_API_BASE"]
    creds.setdefault("PLANE_API_BASE", "https://api.plane.so")
    if not creds.get("PLANE_API_KEY"):
        fail(
            EXIT_CONFIG,
            "PLANE_API_KEY missing; create ~/.config/cross-project-plane/credentials",
            path=str(cred_path),
        )
    return creds


def load_config() -> dict[str, Any]:
    ensure_home()
    path = home() / "config.json"
    default = {
        "workspace_slugs": [],
        "search": {
            "max_projects_per_workspace": 200,
            "work_item_page_size": 100,
            "max_work_item_pages": 5,
            "prefer_open_states_only": True,
        },
        "behavior": {
            "ask_on_ambiguous_project": True,
            "ask_on_ambiguous_work_item": True,
            "auto_write_registry_on_confident_match": True,
            "min_confidence_to_act_without_ask": 0.75,
        },
        "ui": {"plane_app_base": "https://app.plane.so"},
    }
    if not path.exists():
        return default
    data = json.loads(path.read_text())
    for k, v in default.items():
        if k not in data:
            data[k] = v
        elif isinstance(v, dict):
            merged = dict(v)
            merged.update(data[k] or {})
            data[k] = merged
    return data


def load_registry() -> dict[str, Any]:
    ensure_home()
    path = home() / "registry.json"
    if not path.exists():
        return {"version": 1, "updated_at": None, "entries": {}}
    return json.loads(path.read_text())


def save_registry(reg: dict[str, Any]) -> None:
    ensure_home()
    path = home() / "registry.json"
    reg["updated_at"] = utc_now()
    path.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def append_audit(event: dict[str, Any]) -> None:
    ensure_home()
    path = home() / "audit.jsonl"
    event = dict(event)
    event.setdefault("ts", utc_now())
    with path.open("a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


class PlaneClient:
    def __init__(self, creds: dict[str, str] | None = None):
        self.creds = creds or load_credentials()
        self.base = self.creds["PLANE_API_BASE"].rstrip("/")
        self.key = self.creds["PLANE_API_KEY"]

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> tuple[int, Any]:
        url = self.base + path
        if query:
            q = {k: v for k, v in query.items() if v is not None}
            url += "?" + urllib.parse.urlencode(q)
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "X-Api-Key": self.key,
                "X-API-Key": self.key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
                if not raw:
                    return resp.status, None
                return resp.status, json.loads(raw.decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"detail": raw}
            return e.code, payload
        except urllib.error.URLError as e:
            return 0, {"detail": str(e.reason)}

    def me(self) -> tuple[int, Any]:
        return self.request("GET", "/api/v2/users/me/")

    def list_projects(self, workspace_slug: str, per_page: int = 100) -> list[dict]:
        out: list[dict] = []
        cursor = None
        while True:
            q: dict[str, Any] = {"per_page": min(per_page, 100)}
            if cursor:
                q["cursor"] = cursor
            status, data = self.request(
                "GET", f"/api/v1/workspaces/{workspace_slug}/projects/", query=q
            )
            if status != 200:
                fail(EXIT_API, "list_projects failed", status=status, body=data)
            if isinstance(data, list):
                out.extend(data)
                break
            results = data.get("results") or []
            out.extend(results)
            if not data.get("next_page_results"):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                break
            if len(out) >= per_page * 5:
                break
        return out

    def get_project(self, workspace_slug: str, project_id: str) -> tuple[int, Any]:
        return self.request(
            "GET", f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/"
        )

    def list_work_items(
        self,
        workspace_slug: str,
        project_id: str,
        *,
        per_page: int = 100,
        max_pages: int = 5,
        expand: str = "state",
    ) -> list[dict]:
        out: list[dict] = []
        cursor = None
        for _ in range(max_pages):
            q: dict[str, Any] = {
                "per_page": min(per_page, 100),
                "expand": expand,
                "fields": "id,name,sequence_id,description,description_html,description_stripped,state,updated_at,external_id,external_source,priority",
            }
            if cursor:
                q["cursor"] = cursor
            status, data = self.request(
                "GET",
                f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/",
                query=q,
            )
            if status != 200:
                fail(EXIT_API, "list_work_items failed", status=status, body=data)
            if isinstance(data, list):
                out.extend(data)
                break
            results = data.get("results") or []
            out.extend(results)
            if not data.get("next_page_results"):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                break
        return out

    def create_work_item(
        self, workspace_slug: str, project_id: str, body: dict[str, Any]
    ) -> tuple[int, Any]:
        return self.request(
            "POST",
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/",
            body=body,
        )

    def add_comment(
        self,
        workspace_slug: str,
        project_id: str,
        work_item_id: str,
        comment_html: str,
    ) -> tuple[int, Any]:
        return self.request(
            "POST",
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/comments/",
            body={"comment_html": comment_html},
        )

    def list_comments(
        self, workspace_slug: str, project_id: str, work_item_id: str
    ) -> tuple[int, Any]:
        return self.request(
            "GET",
            f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/comments/",
        )


def norm_key(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def compact(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"^@", "", s)
    s = re.sub(r"^[^/]+/", "", s) if "/" in s and not s.startswith("http") else s
    return re.sub(r"[_\-\s\.]+", "", s)


# Map variant spellings to a shared stem for overlap (not full stemming).
TOKEN_ALIASES = {
    "transcribe": "transcrib",
    "transcriber": "transcrib",
    "transcribator": "transcrib",
    "transcription": "transcrib",
    "diarization": "diariz",
    "diarisation": "diariz",
    "diarize": "diariz",
    "diarise": "diariz",
    "defaults": "default",
    "backend": "backend",
    "backends": "backend",
}


def normalize_token(tok: str) -> str:
    return TOKEN_ALIASES.get(tok, tok)


def tokenize(text: str) -> list[str]:
    toks = re.findall(r"[a-z0-9]+", text.lower())
    out = []
    for t in toks:
        if len(t) < 3 or t in STOPWORDS:
            continue
        out.append(normalize_token(t))
    return out


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def text_of_work_item(item: dict) -> str:
    parts = [
        item.get("name") or "",
        item.get("description_stripped") or "",
        item.get("description") or "",
    ]
    html = item.get("description_html") or ""
    if html:
        parts.append(re.sub(r"<[^>]+>", " ", html))
    return " ".join(parts)


def is_open_item(item: dict, prefer_open: bool) -> bool:
    if not prefer_open:
        return True
    state = item.get("state")
    if isinstance(state, dict):
        group = (state.get("group") or "").lower()
        if group in {"completed", "cancelled"}:
            return False
    return True


def work_item_url(cfg: dict, workspace: str, identifier: str | None, seq: Any) -> str | None:
    app = (cfg.get("ui") or {}).get("plane_app_base") or "https://app.plane.so"
    if identifier and seq is not None:
        return f"{app.rstrip('/')}/{workspace}/browse/{identifier}-{seq}/"
    return f"{app.rstrip('/')}/{workspace}/"


def html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def plain_to_html(text: str) -> str:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    if not paras:
        return "<p></p>"
    out = []
    for p in paras:
        lines = "<br/>".join(html_escape(line) for line in p.splitlines())
        out.append(f"<p>{lines}</p>")
    return "".join(out)


def fingerprint(dependency_key: str, title: str, wish: str = "") -> str:
    raw = f"{norm_key(dependency_key)}\n{norm_key(title)}\n{norm_key(wish)}"
    return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()


def read_plane_json(path: str | Path) -> dict[str, Any] | None:
    p = Path(path).expanduser()
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not data.get("project_id") or not data.get("workspace_slug"):
        return None
    return data


def registry_lookup(reg: dict, keys: list[str]) -> tuple[str | None, dict | None]:
    entries = reg.get("entries") or {}
    normed = [norm_key(k) for k in keys if k]
    for k in normed:
        if k in entries:
            return k, entries[k]
        # case variants
        for ek, ev in entries.items():
            if norm_key(ek) == k:
                return ek, ev
    for k in normed:
        short = k.split(":", 1)[-1]
        for ek, ev in entries.items():
            aliases = [norm_key(a) for a in (ev.get("aliases") or [])]
            if k in aliases or short in aliases or norm_key(short) in aliases:
                return ek, ev
            signals = ev.get("signals") or {}
            pkgs = [norm_key(x) for x in (signals.get("package_names") or [])]
            remotes = [norm_key(x) for x in (signals.get("git_remotes") or [])]
            if short in pkgs or k in pkgs or short in remotes or k in remotes:
                return ek, ev
    return None, None


def score_project(project: dict, signals: dict[str, Any]) -> float:
    score = 0.0
    name = project.get("name") or ""
    ident = project.get("identifier") or ""
    desc = project.get("description") or ""
    c_name = compact(name)
    c_ident = compact(ident)

    for code in signals.get("identifiers") or []:
        if compact(code) and compact(code) == c_ident:
            score += 0.55
    for human in signals.get("names") or []:
        if compact(human) and compact(human) == c_name:
            score += 0.50
        elif len(compact(human)) >= 4 and (
            compact(human) in c_name or c_name in compact(human)
        ):
            score += 0.35
    for pkg in signals.get("package_names") or []:
        cp = compact(pkg.split("/")[-1])
        if len(cp) >= 4 and (cp in c_name or c_name in cp or cp == c_ident):
            score += 0.35
    for remote in signals.get("git_remotes") or []:
        parts = re.split(r"[/:]", remote.rstrip("/"))
        tokens = {compact(p) for p in parts if p and compact(p)}
        if c_name in tokens or c_ident in tokens:
            score += 0.25
        elif tokens & set(tokenize(name)):
            score += 0.15
    for mcp in signals.get("mcp_names") or []:
        cm = compact(mcp)
        if cm and (cm in c_name or c_name in cm or cm == c_ident):
            score += 0.25
    name_toks = set(tokenize(name))
    sig_toks = set()
    for group in ("names", "package_names", "mcp_names"):
        for v in signals.get(group) or []:
            sig_toks.update(tokenize(v))
    if jaccard(name_toks, sig_toks) >= 0.5:
        score += 0.15
    for pkg in signals.get("package_names") or []:
        if pkg.lower() in desc.lower():
            score += 0.10
    return min(score, 1.0)


def score_work_item_details(
    item: dict, query: str, external_id: str | None = None
) -> dict[str, Any]:
    """Lexical + thematic overlap score for dedup.

    Returns score in [0,1] plus diagnostics used by decide():
    shared_count, title_coverage, shared_tokens.
    """
    title = item.get("name") or ""
    body = text_of_work_item(item)
    q_toks = set(tokenize(query))
    t_toks = set(tokenize(title))
    b_toks = set(tokenize(body))
    all_item = t_toks | b_toks
    shared = q_toks & all_item
    shared_title = q_toks & t_toks
    title_coverage = (len(shared_title) / len(t_toks)) if t_toks else 0.0

    score = 0.0
    score += 0.55 * jaccard(q_toks, t_toks)
    score += 0.25 * jaccard(q_toks, b_toks)

    # Contiguous phrase in raw title (pre-alias), keep as soft boost.
    q_list = tokenize(query)
    title_norm = " ".join(tokenize(title))
    if len(q_list) >= 2:
        for i in range(len(q_list) - 1):
            phrase = f"{q_list[i]} {q_list[i + 1]}"
            if phrase in title_norm:
                score += 0.25
                break

    # Thematic boosts: title mostly covered by query, or several shared tokens.
    if title_coverage >= 0.7 and len(shared_title) >= 3:
        score += 0.40
    elif title_coverage >= 0.6 and len(shared_title) >= 2:
        score += 0.25
    elif len(shared) >= 3:
        score += 0.30
    elif len(shared) >= 2:
        score += 0.15

    if external_id and item.get("external_id") == external_id:
        score += 0.40
    if len(title.strip()) <= 6 and title.strip().lower() in {"fix", "update", "bug"}:
        score -= 0.20

    return {
        "score": max(0.0, min(score, 1.0)),
        "shared_count": len(shared),
        "shared_title_count": len(shared_title),
        "title_coverage": round(title_coverage, 4),
        "shared_tokens": sorted(shared),
    }


def score_work_item(item: dict, query: str, external_id: str | None = None) -> float:
    return float(score_work_item_details(item, query, external_id)["score"])


def recent_audit_work_item_ids(dependency_key: str | None, limit: int = 50) -> set[str]:
    """Work item ids previously created/commented for this dependency key."""
    if not dependency_key:
        return set()
    path = home() / "audit.jsonl"
    if not path.exists():
        return set()
    found: set[str] = set()
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    for row in rows[-limit:]:
        if row.get("dependency_key") != dependency_key:
            continue
        if row.get("event") not in {"work_item_created", "work_item_commented"}:
            continue
        wid = (row.get("plane") or {}).get("work_item_id")
        if wid:
            found.add(wid)
    return found


def parse_signals_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    if raw.startswith("@"):
        return json.loads(Path(raw[1:]).read_text())
    return json.loads(raw)
