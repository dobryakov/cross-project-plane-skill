#!/usr/bin/env python3
"""Look up dependency keys in the central registry."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_plane import (
    EXIT_FOREIGN,
    EXIT_OK,
    emit,
    load_registry,
    norm_key,
    registry_lookup,
    save_registry,
    utc_now,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "keys",
        nargs="+",
        help="Dependency keys, e.g. name:ai-multi-search npm:@acme/foo",
    )
    p.add_argument(
        "--touch",
        action="store_true",
        help="Update last_used_at on hit",
    )
    args = p.parse_args()
    reg = load_registry()
    key, entry = registry_lookup(reg, args.keys)
    if not entry:
        emit(
            {
                "ok": False,
                "found": False,
                "tried": [norm_key(k) for k in args.keys],
            },
            EXIT_FOREIGN,
        )
    if args.touch and key:
        entry["last_used_at"] = utc_now()
        reg["entries"][key] = entry
        save_registry(reg)
    emit({"ok": True, "found": True, "key": key, "entry": entry}, EXIT_OK)


if __name__ == "__main__":
    main()
