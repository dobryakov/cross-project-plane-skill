---
name: cross-project-plane
description: >-
  Files or updates Plane Cloud work items when the current project needs a
  change in an external dependency, internal API, or MCP server. Resolves the
  target Plane project via a user-level registry and heuristics, deduplicates
  existing work items, comments wishes or creates a new item. Use when blocked
  on an out-of-repo dependency, when an upstream change is required, or when
  the user asks to file something in Plane for another project.
---

# Cross-project Plane

When work in the **current** project depends on a change **elsewhere**, file it
in the owning Plane Cloud project. Prefer running `scripts/*.py` (JSON on
stdout) over ad-hoc HTTP.

## When to use

- Bug/gap in an internal library, shared HTTP API, or MCP server
- User asks to file an upstream request in Plane for another project

## When not to use

- Change belongs entirely in the current repo
- You are fixing the dependency **in this same turn** (file only what remains deferred)
- Vague wishes with no concrete dependency
- No matching Plane project (**foreign**) → report and **stop** (no GitHub/OSS tickets)

## Prerequisites

User-level config (not per-repo `.env`):

```text
~/.config/cross-project-plane/credentials   # PLANE_API_KEY, PLANE_API_BASE
~/.config/cross-project-plane/config.json     # workspace_slugs, thresholds
~/.config/cross-project-plane/registry.json
~/.config/cross-project-plane/audit.jsonl
```

Auth check:

```bash
python3 scripts/plane_auth_check.py
```

Details: [reference-config.md](reference-config.md)

## Security

- Never print or commit `PLANE_API_KEY`
- `credentials` must be mode `0600` (scripts refuse world/group-readable)
- Do not store secrets in consumer repos or this skill markdown

## Workflow

```text
External change request
- [ ] 1. Formulate need (one actionable line + context)
- [ ] 2. Ensure credentials (plane_auth_check.py)
- [ ] 3. Pick dependency key(s) + signals
- [ ] 4. resolve_project.py → resolved | ask | foreign
- [ ] 5. search_work_items.py → comment | create | ask
- [ ] 6. Ask user if decision is ask / ambiguous
- [ ] 7. create_work_item.py OR add_comment.py
- [ ] 8. Report {IDENTIFIER}-N + URL; registry/audit already updated by scripts
```

### 1. Formulate

Free-form (no rigid template): what / why / where it hurts in the consumer /
optional wishes. No assignee unless the user asks.

### 3. Dependency keys

Prefer specific keys: `npm:…`, `pypi:…`, `git:…`, `mcp:…`, `http:…`,
`plane:workspace/ID`, `name:…`. Gather signals (package names, git remotes,
MCP names, path to dependency `.plane.json`).

### 4. Resolve project

```bash
python3 scripts/resolve_project.py \
  --key 'name:ai-multi-search' \
  --signals-json '{"names":["ai-multi-search"],"package_names":["ai-multi-search"]}' \
  --plane-json /path/to/dep/.plane.json
```

Exit codes: `0` resolved, `3` ask (candidates in JSON), `4` foreign, `2` config, `5` API.

On **foreign**: stop. On **ask**: show top candidates; after the user picks,
`registry_upsert.py` with `--source user_confirmed`.

Heuristics: [reference-heuristics.md](reference-heuristics.md)

### 5–7. Dedup and act

```bash
python3 scripts/search_work_items.py \
  --workspace-slug SLUG \
  --project-id UUID \
  --project-identifier PREFIX \
  --query 'short title and distinctive tokens' \
  --dependency-key 'name:…'
```

Use `SLUG` / `UUID` / `PREFIX` from step 4 JSON — never hardcode project UUIDs in the skill.
| `decision` | Action |
| --- | --- |
| `comment` | `add_comment.py` with consumer context + optional wishes |
| `create` | `create_work_item.py` with `--name` + `--description` |
| `ask` | Ask user (candidates + create new) |

Duplicate = same root cause / deliverable, not shared keywords only. When unsure,
ask — never silently create a second task.

```bash
python3 scripts/create_work_item.py \
  --workspace-slug SLUG --project-id UUID --project-identifier ID \
  --name '…' --description '…' --dependency-key '…' --consumer-path "$PWD"

python3 scripts/add_comment.py \
  --workspace-slug SLUG --project-id UUID --work-item-id UUID \
  --consumer-name my-app --comment 'Optional wish…' --dependency-key '…' \
  --list-first
```

### 8. Reply

Briefly: `created` | `commented` | `skipped_foreign` | `cancelled`, plus
`{IDENTIFIER}-N` and URL. Mention if registry was updated.

## Script exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success / clear decision |
| 2 | Config / credentials |
| 3 | Ambiguous — ask user (candidates on stdout) |
| 4 | Foreign / not found |
| 5 | Plane API error |

## Anti-patterns

- Hardcoding project/state UUIDs in the skill or consumer `.env` for Plane auth
- Filing GitHub issues for foreign deps
- Creating a task for work finished in this turn
- Inventing assignees, labels, or deadlines unless the user asks
