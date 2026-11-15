#!/usr/bin/env python3
"""Create a Plane work item (no assignee by default)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_plane import (
    EXIT_API,
    EXIT_OK,
    PlaneClient,
    append_audit,
    emit,
    fail,
    fingerprint,
    load_config,
    plain_to_html,
    work_item_url,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace-slug", required=True)
    p.add_argument("--project-id", required=True)
    p.add_argument("--project-identifier", default=None)
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="", help="Plain text; converted to HTML")
    p.add_argument("--description-html", default=None)
    p.add_argument("--dependency-key", default=None)
    p.add_argument("--external-id", default=None)
    p.add_argument("--consumer-path", default=None)
    p.add_argument("--consumer-name", default=None)
    args = p.parse_args()

    cfg = load_config()
    html = args.description_html or plain_to_html(args.description or args.name)
    ext_id = args.external_id
    if not ext_id and args.dependency_key:
        ext_id = fingerprint(args.dependency_key, args.name)

    body = {
        "name": args.name,
        "description_html": html,
        "external_source": "cross-project-plane",
    }
    if ext_id:
        # Plane may expect shorter external_id; keep hash digest only
        body["external_id"] = ext_id.replace("sha256:", "")[:64]

    client = PlaneClient()
    status, data = client.create_work_item(
        args.workspace_slug, args.project_id, body
    )
    if status not in (200, 201) or not isinstance(data, dict):
        append_audit(
            {
                "event": "error",
                "action": "work_item_created",
                "status": status,
                "message": "create_work_item failed",
            }
        )
        fail(EXIT_API, "create_work_item failed", status=status, body=data)

    seq = data.get("sequence_id")
    ident = args.project_identifier
    url = work_item_url(cfg, args.workspace_slug, ident, seq)
    key = f"{ident}-{seq}" if ident and seq is not None else None

    append_audit(
        {
            "event": "work_item_created",
            "dependency_key": args.dependency_key,
            "consumer": {"path": args.consumer_path, "name": args.consumer_name},
            "plane": {
                "workspace_slug": args.workspace_slug,
                "project_id": args.project_id,
                "project_identifier": ident,
                "work_item_id": data.get("id"),
                "sequence_id": seq,
                "url": url,
            },
            "dedup": {"action": "create"},
            "request_fingerprint": fingerprint(
                args.dependency_key or "", args.name, args.description or ""
            ),
        }
    )

    emit(
        {
            "ok": True,
            "work_item": {
                "id": data.get("id"),
                "name": data.get("name"),
                "sequence_id": seq,
                "key": key,
                "url": url,
            },
            "raw_keys": list(data.keys()),
        },
        EXIT_OK,
    )


if __name__ == "__main__":
    main()
