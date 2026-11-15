# 01 — Overview

## Problem

While implementing work in a consumer project, an agent often discovers that a fix or enhancement belongs elsewhere: an internal library, a shared API service, or an MCP server owned by another Plane project. Today that insight dies in chat or becomes an ad-hoc note. There is no durable, cross-project way to:

1. Capture the external change request.
2. Route it to the correct Plane project.
3. Avoid duplicate work items.
4. Attach extra wishes when a similar item already exists.

Hard-coding Plane project GUIDs per repository does not scale. Putting Plane credentials into every project's `.env` is operationally painful on multi-project servers.

## Goals

1. **Detect external need** — When the agent needs a change outside the current repo/workspace, formulate a clear change request (not a full work-item template).
2. **Resolve Plane target** — Determine workspace slug + project UUID for the dependency via a **central registry**, with **heuristic Plane search** when missing; **write successful resolutions back** into the registry.
3. **Deduplicate** — Search existing work items heuristically; on doubt, ask the user.
4. **Act** — If a similar open item exists → add an optional wish as a **comment**. If not → **create** a work item (no assignee, no rigid template).
5. **Respect foreign systems** — If no matching Plane project can be found on the configured instance(s), treat the dependency as **foreign** and **do not** file issues elsewhere (no GitHub, no upstream trackers).
6. **Store secrets once** — Plane API credentials live under the user config dir, not in per-project `.env` files.
7. **Audit** — Persist a local action log for cross-session awareness and light idempotency.

## Non-goals (v1)

- Hard-coded maps of all org projects inside the skill markdown.
- Mandatory issue templates, assignees, cycles, modules, or priority schemes.
- Filing tickets against third-party / OSS trackers.
- Multi-user credential vaults or per-project API keys.
- Guaranteed semantic dedup (no embedding service required in v1).
- Automatic implementation of the external change (filing only).

## Locked decisions

| Topic | Decision |
| --- | --- |
| Skill location | Personal skill only (`~/.cursor/skills/…`, Claude personal skills equivalent) |
| Trigger | Agent initiates when it hits an external dependency need (not only on explicit user command) |
| Plane | Plane Cloud (`https://api.plane.so`); typically one workspace, possibly more |
| Auth | Single user's Personal Access Token (API key) |
| Integration | Prefer **REST + thin CLI scripts** (see architecture); MCP optional later |
| Project mapping | Central registry + heuristic discovery; learn into registry |
| Credentials path | `~/.config/cross-project-plane/` |
| Dedup | Heuristics; **ask user when unsure**; wishes go to **comments** |
| Issue body | Free-form; no forced template; no assignee |
| Unknown target | Foreign → skip (report only) |
| Logging | Always on |

## Success criteria

- From any consumer project, with credentials configured once, the agent can create or comment on a Plane work item in the dependency's project without editing that consumer's `.env`.
- After the first successful heuristic match for a dependency key, subsequent runs resolve via registry without re-searching (unless forced).
- Ambiguous matches never silently create duplicates; the agent asks.
- Foreign dependencies produce a clear "out of Plane scope" message and no side effects.
