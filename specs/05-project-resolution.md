# 05 — Project Resolution

## Goal

Given an external dependency described in the consumer context, obtain:

```text
{ workspace_slug, project_id, project_name?, project_identifier? }
```

or conclude **foreign** (no Plane project on the configured instance).

## Inputs (signals)

Collect whatever is available; missing signals are fine.

| Signal | Sources |
| --- | --- |
| Package name | `package.json`, lockfiles, `pyproject.toml`, imports |
| Git remote | Dependency repo URL if known; submodule; go module path |
| **Dependency `.plane.json`** | If the dependency checkout / published package / sibling clone exposes repo-root `.plane.json` with `workspace_slug`, `project_id`, `project_identifier` |
| MCP server name | Cursor/Claude MCP config, tool namespace |
| HTTP host / service name | Base URL, OpenAPI title, env var names (`BILLING_API_URL`) |
| Human name | How the user/agent refers to it in chat |
| Existing registry aliases | Prior runs |

**Borrowed practice:** many Plane-using repos bind *their own* project in repo-root `.plane.json` (IDs only; never API keys). For *this* skill that file is **not** the consumer's source of truth — credentials stay under `~/.config/…`. But a **dependency's** `.plane.json` is a high-value discovery signal and should seed the central registry.

## Resolution pipeline

```text
1. Registry lookup (exact / alias / signals)
2. If miss → try dependency `.plane.json` (if reachable) → verify project still exists via API
3. If still miss → list projects in config.workspace_slugs via Plane API
4. Score each project against signals
5. Decide: confident match | ask user | foreign
6. On success → registry write-back
```
### Step 2 — List projects

For each `workspace_slug` in config (in order):

```http
GET /api/v1/workspaces/{workspace_slug}/projects/
```

(or v2 equivalent when stable). Paginate if needed up to `max_projects_per_workspace`.

Collect per project at least: `id`, `name`, `identifier` (short key like `PAY`), optional `description`.

If `workspace_slugs` is empty, attempt workspace discovery with the PAT; if the API cannot list workspaces, **stop and ask** the user to set `workspace_slugs` once in `config.json`.

### Step 3 — Scoring (heuristic)

Normalize strings: lowercase, strip `@scope/`, replace `[_-]` with empty for comparison.

| Evidence | Score contribution (additive, cap 1.0) |
| --- | --- |
| Validated `.plane.json` `project_id` for that dependency | **1.0** (skip scoring; treat as resolved after API verify) |
| Exact match `project.identifier` ↔ known short code | +0.55 |
| Exact match `project.name` ↔ human/package name | +0.50 |
| Package/repo slug contained in `project.name` or vice versa (length ≥ 4) | +0.35 |
| Git owner/repo tokens overlap with name/identifier | +0.25 |
| MCP server name slug overlap | +0.25 |
| Fuzzy token Jaccard ≥ 0.5 on name | +0.15 |
| Description mentions package name | +0.10 |
Implementation may use simple string rules; no ML required.

### Step 4 — Decision

Let `best` be the top score, `second` the runner-up, `T = min_confidence_to_act_without_ask` (default 0.75).

| Condition | Outcome |
| --- | --- |
| `best ≥ T` and `best - second ≥ 0.15` (or no second) | **Confident match** → use project; write registry |
| `best ≥ 0.4` but not confident | **Ask user** with top 3 candidates (name, identifier, score, workspace) |
| User picks one | Use that; write registry (`user_confirmed`) |
| User says none / reject all | **Foreign** |
| `best < 0.4` | **Foreign** (do not ask unless user explicitly wants a manual pick) |

### Foreign policy

If resolution ends foreign:

- Do **not** create Plane work items in the consumer project as a substitute (unless the user separately asks).
- Do **not** open GitHub/GitLab issues.
- Report: dependency identity, signals used, and that no Plane project matched.

## Current project exclusion

If the resolved Plane project is the **same** project the consumer already tracks (optional future: registry entry for "this repo"), still allow filing only if the change is truly about that dependency's codebase hosted there. v1: no special casing required beyond agent judgment; do not block self-project filings if the user is working in a monorepo consumer that maps to the same Plane project.

## Caching

Successful resolutions update `registry.json` (see [04-registry.md](04-registry.md)). Subsequent runs should hit the registry first.
