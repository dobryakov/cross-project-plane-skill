# 08 — Skill Contract (Cursor + Claude)

## Name and description

Suggested skill directory name: `cross-project-plane`

Suggested YAML description (third person, WHAT + WHEN):

```yaml
name: cross-project-plane
description: >-
  Files or updates Plane Cloud work items when the current project needs a
  change in an external dependency, internal API, or MCP server. Resolves the
  target Plane project via a user-level registry and heuristics, deduplicates
  existing work items, comments wishes or creates a new item. Use when blocked
  on an out-of-repo dependency, when an upstream change is required, or when
  the user asks to file something in Plane for another project.
```

**Invocation:** omit `disable-model-invocation` (or set false) so the agent can auto-apply when the description matches. Personal skill scope only.

## Install locations

| Host | Path |
| --- | --- |
| Cursor | `~/.cursor/skills/cross-project-plane/` |
| Claude | Personal skills directory equivalent (same tree) |

Do **not** install under `~/.cursor/skills-cursor/` (Cursor reserved).

## Package layout

```text
cross-project-plane/
├── SKILL.md                 # workflow + rules (keep < 500 lines)
├── reference-config.md      # points at ~/.config/cross-project-plane layout
├── reference-heuristics.md  # scoring details (progressive disclosure)
└── scripts/
    ├── plane_auth_check.py
    ├── registry_lookup.py
    ├── registry_upsert.py
    ├── resolve_project.py
    ├── search_work_items.py
    ├── create_work_item.py
    ├── add_comment.py
    └── audit_log.py
```

`SKILL.md` must instruct the agent to **run scripts** rather than re-implement HTTP clients ad hoc, except for trivial debugging.

## SKILL.md required sections

1. **When to use / when not to use**
2. **Config prerequisite** (`~/.config/cross-project-plane/credentials`)
3. **Workflow checklist** (from [07-agent-workflow.md](07-agent-workflow.md))
4. **Foreign skip rule**
5. **Ask-on-doubt rule**
6. **No assignee / no rigid template**
7. **Security** (never print API key; chmod expectations)
8. **Links** to reference-*.md one level deep

## Dual-host notes

- Prefer `python3` for scripts; document shebang and stdlib-only if possible (`urllib`) to avoid pip deps.
- Shell tool availability differs; scripts should be runnable as `python3 scripts/….py …` with JSON on stdout for the agent to parse.
- Exit codes: `0` ok, `2` user-config error, `3` ambiguous (JSON candidates on stdout), `4` foreign/not found, `5` API error.

## Out of skill scope

- Committing registry/credentials into any git repo
- Hard-coded org project UUID tables inside `SKILL.md`
- Creating GitHub issues for foreign deps
