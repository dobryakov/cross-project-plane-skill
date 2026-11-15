#!/usr/bin/env python3
"""Resolve a dependency to a Plane project (registry → .plane.json → heuristic)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_plane import (
    EXIT_AMBIGUOUS,
    EXIT_FOREIGN,
    EXIT_OK,
    PlaneClient,
    append_audit,
    emit,
    load_config,
    load_registry,
    parse_signals_json,
    read_plane_json,
    registry_lookup,
    save_registry,
    score_project,
    utc_now,
)


def upsert_entry(reg, key, project, workspace, source, confidence, signals, aliases):
    entries = reg.setdefault("entries", {})
    existing = dict(entries.get(key) or {})
    now = utc_now()
    sig = dict(existing.get("signals") or {})
    for field in ("package_names", "git_remotes", "plane_json_paths", "mcp_names"):
        cur = list(sig.get(field) or [])
        for v in signals.get(field) or []:
            if v not in cur:
                cur.append(v)
        if cur:
            sig[field] = cur
    alias_list = list(existing.get("aliases") or [])
    for a in aliases:
        if a not in alias_list:
            alias_list.append(a)
    entry = {
        **existing,
        "workspace_slug": workspace,
        "project_id": project["id"],
        "project_name": project.get("name"),
        "project_identifier": project.get("identifier"),
        "aliases": alias_list,
        "signals": sig,
        "confidence": confidence,
        "source": source,
        "created_at": existing.get("created_at") or now,
        "last_used_at": now,
        "last_verified_at": now,
    }
    entries[key] = entry
    save_registry(reg)
    return entry


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--key", required=True, help="Primary dependency key")
    p.add_argument("--also-key", action="append", default=[], help="Extra keys to try in registry")
    p.add_argument("--signals-json", default=None, help='JSON or @file with signals')
    p.add_argument("--plane-json", default=None, help="Path to dependency .plane.json")
    p.add_argument("--alias", action="append", default=[])
    p.add_argument("--no-write-registry", action="store_true")
    args = p.parse_args()

    cfg = load_config()
    behavior = cfg.get("behavior") or {}
    search = cfg.get("search") or {}
    T = float(behavior.get("min_confidence_to_act_without_ask", 0.75))
    auto_write = bool(behavior.get("auto_write_registry_on_confident_match", True))
    signals = parse_signals_json(args.signals_json)
    if args.plane_json:
        signals.setdefault("plane_json_paths", [])
        if args.plane_json not in signals["plane_json_paths"]:
            signals["plane_json_paths"].append(args.plane_json)

    keys = [args.key, *args.also_key]
    reg = load_registry()
    hit_key, entry = registry_lookup(reg, keys)
    client = PlaneClient()

    if entry:
        st, proj = client.get_project(entry["workspace_slug"], entry["project_id"])
        if st == 200 and isinstance(proj, dict) and proj.get("id"):
            entry["last_used_at"] = utc_now()
            entry["last_verified_at"] = utc_now()
            if hit_key:
                reg["entries"][hit_key] = entry
                save_registry(reg)
            append_audit(
                {
                    "event": "project_resolved",
                    "dependency_key": args.key,
                    "via": "registry",
                    "plane": {
                        "workspace_slug": entry["workspace_slug"],
                        "project_id": entry["project_id"],
                        "project_identifier": entry.get("project_identifier"),
                    },
                }
            )
            emit({"ok": True, "decision": "resolved", "via": "registry", "key": hit_key, "entry": entry, "project": {
                "id": proj["id"],
                "name": proj.get("name"),
                "identifier": proj.get("identifier"),
                "workspace_slug": entry["workspace_slug"],
            }}, EXIT_OK)
        # stale — fall through

    # Dependency .plane.json
    plane_paths = list(signals.get("plane_json_paths") or [])
    if args.plane_json and args.plane_json not in plane_paths:
        plane_paths.insert(0, args.plane_json)
    for path in plane_paths:
        data = read_plane_json(path)
        if not data:
            continue
        st, proj = client.get_project(data["workspace_slug"], data["project_id"])
        if st != 200 or not isinstance(proj, dict):
            continue
        project = {
            "id": proj["id"],
            "name": proj.get("name") or data.get("project_name"),
            "identifier": proj.get("identifier") or data.get("project_identifier"),
        }
        written = None
        if auto_write and not args.no_write_registry:
            written = upsert_entry(
                reg,
                args.key,
                project,
                data["workspace_slug"],
                "plane_json",
                1.0,
                signals,
                args.alias,
            )
        append_audit(
            {
                "event": "project_resolved",
                "dependency_key": args.key,
                "via": "plane_json",
                "plane": {
                    "workspace_slug": data["workspace_slug"],
                    "project_id": project["id"],
                    "project_identifier": project.get("identifier"),
                },
                "registry": {"wrote": bool(written)},
            }
        )
        emit(
            {
                "ok": True,
                "decision": "resolved",
                "via": "plane_json",
                "plane_json": path,
                "project": {**project, "workspace_slug": data["workspace_slug"]},
                "entry": written,
            },
            EXIT_OK,
        )

    slugs = list(cfg.get("workspace_slugs") or [])
    if not slugs:
        append_audit({"event": "project_ask", "dependency_key": args.key, "reason": "no_workspace_slugs"})
        emit(
            {
                "ok": False,
                "decision": "ask",
                "reason": "config.workspace_slugs is empty; set it in ~/.config/cross-project-plane/config.json",
                "candidates": [],
            },
            EXIT_AMBIGUOUS,
        )

    max_proj = int(search.get("max_projects_per_workspace", 200))
    scored = []
    for slug in slugs:
        projects = client.list_projects(slug, per_page=min(100, max_proj))
        for proj in projects[:max_proj]:
            s = score_project(proj, signals)
            scored.append(
                {
                    "score": round(s, 4),
                    "workspace_slug": slug,
                    "project_id": proj.get("id"),
                    "name": proj.get("name"),
                    "identifier": proj.get("identifier"),
                    "description": (proj.get("description") or "")[:200],
                }
            )
    scored.sort(key=lambda x: x["score"], reverse=True)
    best = scored[0] if scored else None
    second = scored[1] if len(scored) > 1 else None

    if not best or best["score"] < 0.4:
        append_audit(
            {
                "event": "project_foreign",
                "dependency_key": args.key,
                "signals": {k: signals.get(k) for k in signals},
                "best_score": None if not best else best["score"],
            }
        )
        emit(
            {
                "ok": False,
                "decision": "foreign",
                "best": best,
                "top": scored[:5],
            },
            EXIT_FOREIGN,
        )

    gap_ok = second is None or (best["score"] - second["score"] >= 0.15)
    confident = best["score"] >= T and gap_ok
    if confident:
        project = {
            "id": best["project_id"],
            "name": best["name"],
            "identifier": best["identifier"],
        }
        written = None
        if auto_write and not args.no_write_registry:
            written = upsert_entry(
                reg,
                args.key,
                project,
                best["workspace_slug"],
                "heuristic",
                best["score"],
                signals,
                args.alias,
            )
        append_audit(
            {
                "event": "project_resolved",
                "dependency_key": args.key,
                "via": "heuristic",
                "plane": {
                    "workspace_slug": best["workspace_slug"],
                    "project_id": best["project_id"],
                    "project_identifier": best.get("identifier"),
                },
                "registry": {"wrote": bool(written)},
            }
        )
        emit(
            {
                "ok": True,
                "decision": "resolved",
                "via": "heuristic",
                "project": {**project, "workspace_slug": best["workspace_slug"], "score": best["score"]},
                "entry": written,
            },
            EXIT_OK,
        )

    append_audit(
        {
            "event": "project_ask",
            "dependency_key": args.key,
            "candidates": scored[:3],
        }
    )
    emit(
        {
            "ok": False,
            "decision": "ask",
            "reason": "ambiguous or below auto-act threshold",
            "threshold": T,
            "candidates": scored[:3],
        },
        EXIT_AMBIGUOUS,
    )


if __name__ == "__main__":
    main()
