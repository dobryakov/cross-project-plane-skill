# Cross-Project Plane

Personal agent skill (Cursor IDE and Claude) that routes upstream change requests into the right [Plane](https://plane.so) Cloud project — without hard-coding project lists or stuffing Plane credentials into every repo’s `.env`.
## The problem

While working in a consumer project, an agent often discovers that a fix belongs elsewhere: an internal library, a shared API, or an MCP server owned by another team. That insight usually dies in chat. Filing it well means knowing *which* Plane project owns the dependency, avoiding duplicate work items, and storing API credentials once per machine — not once per repository.

## What this skill does

1. Detect when progress depends on a change **outside** the current project.
2. Resolve the dependency to a Plane `workspace` + `project_id` via a **user-level registry**, with heuristic Plane search (and optional dependency `.plane.json`) when the registry misses — then **write successful matches back**.
3. Search open work items for a similar request (PQL / keywords + judgment on same root cause).
4. **Comment** optional wishes on an existing item, or **create** a new one if none fits.
5. If no Plane project matches → treat the dependency as **foreign** and leave it alone (no GitHub/upstream filing).

## Design highlights

| Concern | Approach |
| --- | --- |
| Credentials | `~/.config/cross-project-plane/` (not per-project `.env`) |
| Project map | Central `registry.json`, learned over time — no hard-coded UUID tables in the skill |
| Integration | REST + thin Python helpers first; Plane MCP optional later |
| Dedup | Heuristics; **ask the user when unsure** |
| Issue shape | Free-form name/description; no mandatory assignee, labels, or template |
| Scope | Personal skill only (`~/.cursor/skills/…` and Claude equivalent) |

## Install (Cursor personal skill)

```bash
mkdir -p ~/.cursor/skills
ln -sfn /path/to/this/repo/skill ~/.cursor/skills/cross-project-plane
```

Configure once:

```bash
mkdir -p ~/.config/cross-project-plane && chmod 700 ~/.config/cross-project-plane
# credentials + config.json — see skill/reference-config.md
python3 skill/scripts/plane_auth_check.py
```

Skill package: **[skill/](skill/)** (`SKILL.md` + `scripts/`) · Design: **[specs/README.md](specs/README.md)**
## Specs

| Spec | Topic |
| --- | --- |
| [01-overview](specs/01-overview.md) | Goals, non-goals, locked decisions |
| [02-architecture](specs/02-architecture.md) | Components, REST vs MCP |
| [03-credentials-and-config](specs/03-credentials-and-config.md) | Secrets and config layout |
| [04-registry](specs/04-registry.md) | Dependency → Plane project registry |
| [05-project-resolution](specs/05-project-resolution.md) | How project GUIDs are resolved |
| [06-dedup-and-actions](specs/06-dedup-and-actions.md) | Create vs comment |
| [07-agent-workflow](specs/07-agent-workflow.md) | End-to-end agent procedure |
| [08-skill-contract](specs/08-skill-contract.md) | Packaging for Cursor and Claude |
| [09-logging](specs/09-logging.md) | Audit log |
| [10-plane-api-binding](specs/10-plane-api-binding.md) | Plane Cloud API assumptions |

Also: [skill/reference-config.md](skill/reference-config.md), [skill/reference-heuristics.md](skill/reference-heuristics.md).

## Non-goals (for now)

- Tracking deferred work *inside* the current project (use a dedicated in-project Plane skill for that)
- Worklogs, close-out state machines, or mandatory label taxonomies
- Filing tickets against third-party / OSS trackers when Plane has no matching project

## License

No license file has been added yet. Treat the specs as documentation until a license is chosen.
