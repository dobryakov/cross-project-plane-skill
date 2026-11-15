#!/usr/bin/env python3
"""Add a comment (optional wishes) to an existing Plane work item."""

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
    html_escape,
    plain_to_html,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace-slug", required=True)
    p.add_argument("--project-id", required=True)
    p.add_argument("--work-item-id", required=True)
    p.add_argument("--project-identifier", default=None)
    p.add_argument("--sequence-id", default=None)
    p.add_argument("--comment", default=None, help="Plain text comment")
    p.add_argument("--comment-html", default=None)
    p.add_argument("--consumer-name", default=None)
    p.add_argument("--dependency-key", default=None)
    p.add_argument("--skip-if-duplicate-fingerprint", action="store_true")
    p.add_argument("--list-first", action="store_true", help="Include existing comments in output")
    args = p.parse_args()

    if not args.comment and not args.comment_html:
        fail(EXIT_API, "provide --comment or --comment-html")

    client = PlaneClient()
    existing = None
    if args.list_first or args.skip_if_duplicate_fingerprint:
        st, existing = client.list_comments(
            args.workspace_slug, args.project_id, args.work_item_id
        )
        if st != 200:
            existing = None

    fp = fingerprint(
        args.dependency_key or "",
        args.work_item_id,
        args.comment or args.comment_html or "",
    )
    if args.skip_if_duplicate_fingerprint and existing is not None:
        # best-effort: scan audit instead would be better; here skip if identical html seen
        results = existing.get("results", existing if isinstance(existing, list) else [])
        needle = (args.comment_html or plain_to_html(args.comment or "")).strip()
        for c in results or []:
            if (c.get("comment_html") or "").strip() == needle:
                append_audit(
                    {
                        "event": "skipped_duplicate_ping",
                        "dependency_key": args.dependency_key,
                        "plane": {
                            "workspace_slug": args.workspace_slug,
                            "project_id": args.project_id,
                            "work_item_id": args.work_item_id,
                        },
                        "request_fingerprint": fp,
                    }
                )
                emit(
                    {
                        "ok": True,
                        "skipped": True,
                        "reason": "duplicate_comment_html",
                        "request_fingerprint": fp,
                    },
                    EXIT_OK,
                )

    if args.comment_html:
        html = args.comment_html
    else:
        lead = ""
        if args.consumer_name:
            lead = f"<p><b>From consumer {html_escape(args.consumer_name)}:</b></p>"
        html = lead + plain_to_html(args.comment or "")

    status, data = client.add_comment(
        args.workspace_slug, args.project_id, args.work_item_id, html
    )
    if status not in (200, 201):
        append_audit(
            {
                "event": "error",
                "action": "work_item_commented",
                "status": status,
                "message": "add_comment failed",
            }
        )
        fail(EXIT_API, "add_comment failed", status=status, body=data)

    append_audit(
        {
            "event": "work_item_commented",
            "dependency_key": args.dependency_key,
            "consumer": {"name": args.consumer_name},
            "plane": {
                "workspace_slug": args.workspace_slug,
                "project_id": args.project_id,
                "project_identifier": args.project_identifier,
                "work_item_id": args.work_item_id,
                "sequence_id": args.sequence_id,
            },
            "dedup": {"action": "comment"},
            "request_fingerprint": fp,
        }
    )

    out = {
        "ok": True,
        "comment_id": (data or {}).get("id") if isinstance(data, dict) else None,
        "work_item_id": args.work_item_id,
        "request_fingerprint": fp,
    }
    if args.list_first:
        out["existing_comments_status"] = "fetched"
    emit(out, EXIT_OK)


if __name__ == "__main__":
    main()
