#!/usr/bin/env python3
"""Insert or merge a registry entry for a dependency key."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_plane import EXIT_CONFIG, EXIT_OK, emit, fail, load_registry, save_registry, utc_now


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--key", required=True, help="Dependency key, e.g. name:ai-multi-search")
    p.add_argument("--workspace-slug", required=True)
    p.add_argument("--project-id", required=True)
    p.add_argument("--project-name", default=None)
    p.add_argument("--project-identifier", default=None)
    p.add_argument("--source", default="manual", choices=["manual", "heuristic", "user_confirmed", "plane_json"])
    p.add_argument("--confidence", type=float, default=1.0)
    p.add_argument("--alias", action="append", default=[], help="Repeatable alias")
    p.add_argument("--package-name", action="append", default=[])
    p.add_argument("--git-remote", action="append", default=[])
    p.add_argument("--plane-json", action="append", default=[])
    p.add_argument("--json", default=None, help="Extra fields as JSON object")
    args = p.parse_args()

    if not args.project_id or not args.workspace_slug:
        fail(EXIT_CONFIG, "workspace_slug and project_id are required")

    reg = load_registry()
    entries = reg.setdefault("entries", {})
    existing = dict(entries.get(args.key) or {})
    now = utc_now()

    signals = dict(existing.get("signals") or {})
    for field, values in (
        ("package_names", args.package_name),
        ("git_remotes", args.git_remote),
        ("plane_json_paths", args.plane_json),
    ):
        cur = list(signals.get(field) or [])
        for v in values:
            if v not in cur:
                cur.append(v)
        signals[field] = cur

    aliases = list(existing.get("aliases") or [])
    for a in args.alias:
        if a not in aliases:
            aliases.append(a)

    entry = {
        **existing,
        "workspace_slug": args.workspace_slug,
        "project_id": args.project_id,
        "project_name": args.project_name or existing.get("project_name"),
        "project_identifier": args.project_identifier or existing.get("project_identifier"),
        "aliases": aliases,
        "signals": signals,
        "confidence": args.confidence,
        "source": args.source,
        "created_at": existing.get("created_at") or now,
        "last_used_at": now,
        "last_verified_at": now,
    }
    if args.json:
        extra = json.loads(args.json)
        if not isinstance(extra, dict):
            fail(EXIT_CONFIG, "--json must be an object")
        entry.update(extra)

    entries[args.key] = entry
    save_registry(reg)
    emit({"ok": True, "key": args.key, "entry": entry}, EXIT_OK)


if __name__ == "__main__":
    main()
