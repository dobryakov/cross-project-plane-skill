# Config reference

All machine-local state lives under `~/.config/cross-project-plane/`
(override with `CROSS_PROJECT_PLANE_HOME`).

```text
~/.config/cross-project-plane/
├── credentials      # mode 0600
├── config.json
├── registry.json
└── audit.jsonl
```

## credentials

```dotenv
PLANE_API_BASE=https://api.plane.so
PLANE_API_KEY=plane_api_…
```

Create a Personal Access Token in Plane: Profile Settings → Personal Access Tokens.
Env overrides: `PLANE_API_KEY`, `PLANE_API_BASE`.

## config.json

```json
{
  "workspace_slugs": ["dobryakov"],
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

`workspace_slugs` scopes API search only — it is not a hard-coded project list.

## registry.json

Maps dependency keys (`npm:…`, `name:…`, `mcp:…`, …) to
`workspace_slug` + `project_id`. Successful resolutions write back here.
See specs/04-registry.md.

## Bootstrap

```bash
mkdir -p ~/.config/cross-project-plane && chmod 700 ~/.config/cross-project-plane
# write credentials + config.json
chmod 600 ~/.config/cross-project-plane/credentials
python3 scripts/plane_auth_check.py
```

## Install skill (Cursor)

```bash
mkdir -p ~/.cursor/skills
ln -sfn /path/to/cross-project-plane ~/.cursor/skills/cross-project-plane
```

Same idea for Claude personal skills if needed. Repo root must contain `SKILL.md`.
