#!/usr/bin/env python3
"""Validate Plane API credentials. Exit 0 on success."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_plane import EXIT_API, EXIT_OK, PlaneClient, append_audit, emit, fail, load_credentials

def main() -> None:
    creds = load_credentials()
    client = PlaneClient(creds)
    status, data = client.me()
    if status != 200:
        append_audit({"event": "auth_failed", "status": status})
        fail(EXIT_API, "auth failed", status=status, body=data)
    append_audit({"event": "auth_ok", "user_id": (data or {}).get("id")})
    emit(
        {
            "ok": True,
            "status": status,
            "user": {
                "id": (data or {}).get("id"),
                "email": (data or {}).get("email"),
                "display_name": (data or {}).get("display_name"),
            },
            "api_base": creds["PLANE_API_BASE"],
        },
        EXIT_OK,
    )


if __name__ == "__main__":
    main()
