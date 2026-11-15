# 09 — Logging and Audit

## Purpose

Keep a durable, machine-local record of what the skill did so later sessions can:

- Avoid double-creating the same request
- Show the user prior Plane links for a dependency
- Debug resolution and dedup decisions

## File

`~/.config/cross-project-plane/audit.jsonl`

Append-only JSON Lines. Never store `PLANE_API_KEY`. Truncate description fields to a short hash or ≤ 200 chars preview if needed.

## Event schema

```json
{
  "ts": "2026-11-15T12:34:56Z",
  "event": "work_item_created",
  "dependency_key": "npm:@acme/payments-sdk",
  "consumer": {
    "path": "/home/ubuntu/apps/shop-api",
    "git_remote": "github.com/acme/shop-api",
    "name": "shop-api"
  },
  "plane": {
    "workspace_slug": "acme",
    "project_id": "4af68566-94a4-4eb3-94aa-50dc9427067b",
    "project_identifier": "PAY",
    "work_item_id": "550e8400-e29b-41d4-a716-446655440000",
    "sequence_id": 42,
    "url": "https://app.plane.so/acme/browse/PAY-42/"
  },
  "dedup": {
    "action": "create",
    "best_score": 0.12,
    "asked_user": false
  },
  "registry": {
    "wrote": true,
    "source": "heuristic"
  },
  "request_fingerprint": "sha256:…"
}
```

### Event types

| `event` | When |
| --- | --- |
| `auth_ok` / `auth_failed` | Credential check |
| `project_resolved` | Registry or heuristic success |
| `project_foreign` | No match |
| `project_ask` | Ambiguous project; awaiting user |
| `work_item_created` | Create succeeded |
| `work_item_commented` | Comment succeeded |
| `work_item_ask` | Ambiguous dedup |
| `skipped_duplicate_ping` | Same wish fingerprint already commented recently |
| `error` | API or local failure (`message` without secrets) |

## Fingerprint

`request_fingerprint = sha256(dependency_key + "\n" + normalized_title + "\n" + normalized_core_wish)`

Before create, scripts/agent should scan the last N days of audit for the same fingerprint + `work_item_created`. If found, prefer commenting on that work item or asking instead of creating another.

## Retention

v1: unbounded append. Optional later: rotate when file exceeds 10 MB. Do not sync to Plane.

## Consumer identity

`consumer.path` is the workspace root the agent was editing. Best-effort only; may be empty in some hosts.
