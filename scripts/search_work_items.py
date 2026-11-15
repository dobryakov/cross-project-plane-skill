#!/usr/bin/env python3
"""Search open work items and score similarity for dedup."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_plane import (
    EXIT_AMBIGUOUS,
    EXIT_OK,
    PlaneClient,
    emit,
    fingerprint,
    is_open_item,
    load_config,
    score_work_item,
    work_item_url,
)


def decide(scored, T: float):
    if not scored:
        return "create", None
    best = scored[0]
    second = scored[1] if len(scored) > 1 else None
    if best["score"] >= T and (second is None or best["score"] - second["score"] >= 0.1):
        return "comment", best
    close = [c for c in scored if c["score"] >= 0.5]
    if len(close) >= 2 and close[0]["score"] - close[-1]["score"] <= 0.1:
        return "ask", None
    if 0.45 <= best["score"] < T:
        return "ask", None
    return "create", None


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace-slug", required=True)
    p.add_argument("--project-id", required=True)
    p.add_argument("--project-identifier", default=None)
    p.add_argument("--query", required=True, help="Title + key tokens for similarity")
    p.add_argument("--external-id", default=None)
    p.add_argument("--dependency-key", default=None)
    args = p.parse_args()

    cfg = load_config()
    search = cfg.get("search") or {}
    behavior = cfg.get("behavior") or {}
    T = float(behavior.get("min_confidence_to_act_without_ask", 0.75))
    prefer_open = bool(search.get("prefer_open_states_only", True))
    per_page = int(search.get("work_item_page_size", 100))
    max_pages = int(search.get("max_work_item_pages", 5))

    client = PlaneClient()
    items = client.list_work_items(
        args.workspace_slug,
        args.project_id,
        per_page=per_page,
        max_pages=max_pages,
    )
    scored = []
    for item in items:
        if not is_open_item(item, prefer_open):
            continue
        s = score_work_item(item, args.query, args.external_id)
        seq = item.get("sequence_id")
        scored.append(
            {
                "score": round(s, 4),
                "id": item.get("id"),
                "name": item.get("name"),
                "sequence_id": seq,
                "key": (
                    f"{args.project_identifier}-{seq}"
                    if args.project_identifier and seq is not None
                    else None
                ),
                "state": (item.get("state") or {}).get("name")
                if isinstance(item.get("state"), dict)
                else item.get("state"),
                "updated_at": item.get("updated_at"),
                "url": work_item_url(
                    cfg, args.workspace_slug, args.project_identifier, seq
                ),
                "external_id": item.get("external_id"),
            }
        )
    scored.sort(key=lambda x: x["score"], reverse=True)
    action, match = decide(scored, T)
    fp = None
    if args.dependency_key:
        fp = fingerprint(args.dependency_key, args.query)

    payload = {
        "ok": True,
        "decision": action,
        "threshold": T,
        "query": args.query,
        "request_fingerprint": fp,
        "match": match,
        "candidates": scored[:10],
        "total_scanned": len(items),
        "total_open_scored": len(scored),
    }
    code = EXIT_AMBIGUOUS if action == "ask" else EXIT_OK
    emit(payload, code)


if __name__ == "__main__":
    main()
