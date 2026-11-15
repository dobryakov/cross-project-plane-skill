# 03 — Credentials and Config

## Location

All machine-local state for this skill lives under:

```text
~/.config/cross-project-plane/
```

Override root with `CROSS_PROJECT_PLANE_HOME` (tests / unusual layouts only).

### Layout

```text
~/.config/cross-project-plane/
├── credentials          # secrets; mode 0600
├── config.json          # non-secret preferences
├── registry.json        # dependency → Plane project map
└── audit.jsonl          # append-only action log
```

Create the directory on first successful setup (`mkdir -p`, `chmod 700` on the directory).

## `credentials` file

**Format:** dotenv-like, one `KEY=VALUE` per line. No JSON (easier to edit by hand, easier to `chmod`).

```dotenv
PLANE_API_BASE=https://api.plane.so
PLANE_API_KEY=plane_api_xxxxxxxx
```

| Key | Required | Description |
| --- | --- | --- |
| `PLANE_API_BASE` | Yes | Default `https://api.plane.so` (Plane Cloud) |
| `PLANE_API_KEY` | Yes | Personal Access Token from Profile Settings → Personal Access Tokens |

**Auth header for requests:** `X-Api-Key: <PLANE_API_KEY>` (Plane Cloud v2). Scripts may also send `X-API-Key` as an alias if needed for v1 paths; prefer v2 + `X-Api-Key`.

### Rules

- File mode **0600**; refuse to run (or warn loudly) if group/world-readable.
- Never copy this file into a project repo.
- Never echo the key into chat, audit log payloads, or registry entries.
- One user identity for v1 (the PAT owner). All creates/comments appear as that user in Plane.

### Bootstrap (human)

1. Create a PAT in Plane Cloud.
2. Write `credentials` as above.
3. Run `scripts/plane_auth_check.py` → expect HTTP 200 from `/api/v2/users/me/`.

## `config.json`

Non-secret preferences:

```json
{
  "workspace_slugs": ["my-main-workspace"],
  "search": {
    "max_projects_per_workspace": 200,
    "work_item_page_size": 100,
    "max_work_item_pages": 5,
    "prefer_open_states_only": true
  },
  "behavior": {
    "ask_on_ambiguous_project": true,
    "ask_on_ambiguous_work_item": true,
    "auto_write_registry_on_confident_match": true,
    "min_confidence_to_act_without_ask": 0.75
  },
  "ui": {
    "plane_app_base": "https://app.plane.so"
  }
}
```

| Field | Meaning |
| --- | --- |
| `workspace_slugs` | Workspaces to search when registry misses. Empty → discover via API if available; otherwise require user to fill this once. |
| `prefer_open_states_only` | Dedup search ignores completed/cancelled groups when true |
| `min_confidence_to_act_without_ask` | Below this → ask user (see dedup/resolution) |
| `plane_app_base` | For building human-facing work item URLs in replies |

`workspace_slugs` is **not** a hard-coded project list; it only scopes which workspaces the PAT may search. Projects themselves are learned into `registry.json`.

## Environment overrides (optional)

| Env var | Overrides |
| --- | --- |
| `CROSS_PROJECT_PLANE_HOME` | Config root |
| `PLANE_API_KEY` | Key from `credentials` (useful in CI of the skill itself) |
| `PLANE_API_BASE` | API base |

Project `.env` files are **out of scope** and must not be required.

## Multi-workspace note

v1 assumes "usually one workspace" but `workspace_slugs` is an array. Resolution searches configured workspaces in order. Registry entries always store the winning `workspace_slug` + `project_id`.
