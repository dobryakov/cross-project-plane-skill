#!/usr/bin/env python3
"""Append or query the local audit log."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_plane import EXIT_OK, append_audit, emit, home, utc_now


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("append", help="Append a JSON event")
    a.add_argument("--event", required=True)
    a.add_argument("--json", default="{}", help="Extra fields as JSON object")

    q = sub.add_parser("query", help="Query recent events")
    q.add_argument("--dependency-key", default=None)
    q.add_argument("--event", default=None)
    q.add_argument("--fingerprint", default=None)
    q.add_argument("--limit", type=int, default=20)

    args = p.parse_args()
    if args.cmd == "append":
        extra = json.loads(args.json)
        if not isinstance(extra, dict):
            emit({"ok": False, "error": "--json must be object"}, 2)
        event = {"event": args.event, "ts": utc_now(), **extra}
        append_audit(event)
        emit({"ok": True, "event": event}, EXIT_OK)

    path = home() / "audit.jsonl"
    rows = []
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if args.dependency_key:
        rows = [r for r in rows if r.get("dependency_key") == args.dependency_key]
    if args.event:
        rows = [r for r in rows if r.get("event") == args.event]
    if args.fingerprint:
        rows = [r for r in rows if r.get("request_fingerprint") == args.fingerprint]
    rows = rows[-args.limit :]
    emit({"ok": True, "count": len(rows), "events": rows}, EXIT_OK)


if __name__ == "__main__":
    main()
