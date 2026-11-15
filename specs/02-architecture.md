# 02 — Architecture

## High-level picture

```
┌─────────────────────────────┐
│ Consumer project (any repo) │
│ Agent hits external need    │
└──────────────┬──────────────┘
               │ reads personal skill
               ▼
┌─────────────────────────────┐     ┌──────────────────────────────────┐
│ Personal skill              │────▶│ ~/.config/cross-project-plane/   │
│ cross-project-plane         │     │ credentials, config, registry,   │
│ SKILL.md + scripts/         │     │ audit log                        │
└──────────────┬──────────────┘     └──────────────────────────────────┘
               │ HTTPS REST
               ▼
┌─────────────────────────────┐
│ Plane Cloud API             │
│ api.plane.so                │
└─────────────────────────────┘
```

## Integration choice: REST first (not MCP)

**Decision:** implement Plane access as **REST calls** from small helper scripts shipped with the skill (or invoked via shell/`curl`/`python`). Do **not** require a Plane MCP server for v1.

### Why REST

| Factor | REST + scripts | Plane MCP |
| --- | --- | --- |
| Works in Cursor + Claude personal skills | Yes | Only if MCP is configured in each host |
| Same auth path (`X-Api-Key`) | Yes | Depends on MCP packaging |
| Debuggable / testable offline | Easy (`curl`, unit tests) | Harder |
| Rate-limit / pagination control | Explicit | Opaque |
| Future MCP wrap | Can wrap the same scripts | — |

MCP may be added later as a thin facade over the same helpers. The skill contract must not assume MCP tools exist. If a Plane MCP is present, discover its server id dynamically; note that MCP cloud auth headers can differ from REST (`Bearer` + workspace slug vs `X-Api-Key`).

## Components

### 1. Personal skill (`cross-project-plane`)

- `SKILL.md` — when to trigger, workflow, ask-on-doubt rules, foreign-skip policy.
- `scripts/` — deterministic helpers the agent **executes**, not re-implements:
  - `plane_auth_check.py` — validate API key (`GET /api/v2/users/me/`).
  - `registry_lookup.py` / `registry_upsert.py` — read/write registry.
  - `resolve_project.py` — registry then heuristic search across configured workspaces.
  - `search_work_items.py` — list/filter candidates for dedup.
  - `create_work_item.py` — create work item (name + description only by default).
  - `add_comment.py` — post comment HTML/text.
  - `audit_log.py` — append structured log lines.

Prefer **Python 3** if available; fall back guidance in the skill if not. Scripts read config only from `~/.config/cross-project-plane/` (override via env for tests).

### 2. User config directory

Single machine-local store for secrets, registry, and logs. Shared by all projects the user opens. See [03-credentials-and-config.md](03-credentials-and-config.md) and [04-registry.md](04-registry.md).

### 3. Plane Cloud

Source of truth for projects and work items. The skill never caches work-item bodies long-term beyond the audit log references (id, URL, action).

## Trust boundaries

| Data | Location | Shared across projects? |
| --- | --- | --- |
| API key | `credentials` file (mode `0600`) | Yes (user machine) |
| Project registry | `registry.json` | Yes |
| Audit log | `audit.jsonl` | Yes |
| Consumer repo secrets | unchanged | No Plane key required |
| Skill markdown | personal skills dir | Yes |

Do not commit `~/.config/cross-project-plane/` anywhere. Do not print the API key in agent replies.

## Hosts

| Host | Skill path (illustrative) |
| --- | --- |
| Cursor IDE | `~/.cursor/skills/cross-project-plane/` |
| Claude (personal skills) | User's Claude skills directory for the same skill tree |

Both hosts run the same scripts against the same config dir so behavior stays consistent.

## Failure modes (architectural)

| Failure | Behavior |
| --- | --- |
| Missing credentials | Stop; tell user how to create the config file |
| API 401 | Stop; ask to rotate/regenerate PAT |
| Rate limit 429 | Retry with backoff once or twice; then stop and report |
| No project match | Foreign → no create/comment |
| Ambiguous project or issue match | Ask user; do not write |
