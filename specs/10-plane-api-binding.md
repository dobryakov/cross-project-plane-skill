# 10 — Plane API Binding

## Deployment

| Setting | Value |
| --- | --- |
| Product | Plane Cloud |
| API base | `https://api.plane.so` |
| App base (links) | `https://app.plane.so` |
| Auth | Personal Access Token in `X-Api-Key` |

Prefer **API v2** where documented; fall back to **v1** paths that are known-stable for projects, work items, and comments.

## Auth check

```http
GET /api/v2/users/me/
X-Api-Key: <token>
```

Expect `200`. On `401`, abort skill actions.

## Projects

List projects in a workspace (v1 example from public docs):

```http
GET /api/v1/workspaces/{workspace_slug}/projects/
X-API-Key: <token>
```

Use pagination (`per_page`, `cursor`) as documented. Rate limit: **60 requests/minute** per key; honor `X-RateLimit-*` headers.

## Work items

Create (v1 example):

```http
POST /api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/
Content-Type: application/json

{
  "name": "…",
  "description_html": "<p>…</p>",
  "external_source": "cross-project-plane",
  "external_id": "…"
}
```

Use whichever description fields the live API accepts (`description`, `description_html`, `description_stripped`). v2 paths under `/api/v2/…` may differ in field names; **omit assignees** in v1 of this skill.

List / search for dedup:

```http
GET /api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/?per_page=100
```

When available (REST or optional later MCP), also use keyword search and **PQL**, e.g. `title ~ "<phrase>" AND stateGroup IN openStates()`, with `fields` / `expand=state`. Prefer open items only for duplicate checks.

Resolving `{IDENTIFIER}-{n}` after create/comment: use sequence + project identifier locally, or an API/MCP helper equivalent to `retrieve_work_item_by_identifier` when present.

## Comments

```http
POST /api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/{work_item_id}/comments/
```

Send `comment_html` (and/or structured JSON). Helper scripts convert plain text wishes to minimal HTML:

```html
<p><b>From consumer …:</b> …</p>
<p>Paths: <code>src/…</code></p>
```

List existing comments before posting when deduping wishes. v2 comment routes exist under  
`/api/v2/workspaces/{slug}/projects/{project_id}/work-items/{work_item_id}/comments/`.
## Human URLs

Construct browse links using config `plane_app_base`, workspace slug, and project identifier + sequence when available, e.g.:

```text
{plane_app_base}/{workspace_slug}/browse/{IDENTIFIER}-{sequence_id}/
```

If the exact URL scheme differs, prefer any `url` field returned by the API; otherwise show workspace/project/work-item UUIDs.

## Error handling

| HTTP | Skill behavior |
| --- | --- |
| 400 | Surface validation detail; do not retry blindly |
| 401 | Stop; credentials invalid |
| 404 | Stale project/work item → re-resolve or ask |
| 429 | Sleep until reset / short backoff; retry ≤ 2 |
| 5xx | Retry once; then error event |

## Version drift

Plane is evolving v1 → v2. Implementation should:

1. Centralize paths in one Python module (`plane_client.py`).
2. Pin assumptions in this doc when they change.
3. Prefer OpenAPI at `GET /api/v2/schema/` for codegen later.

## Optional MCP note (not required)

Some hosts expose a Plane MCP (often named like `user-plane`). If used later as a facade:

- Discover the server name from the host MCP list; do not hardcode it.
- Cloud MCP HTTP auth may differ from REST (`Authorization: Bearer` + `x-workspace-slug` rather than `X-Api-Key`) — keep that path isolated from the REST client.
- Useful MCP-shaped operations to mirror in REST scripts: `list_projects`, `search_work_items` / `list_work_items` (PQL), `create_work_item`, `create_work_item_comment`, `list_work_item_comments`, retrieve by identifier.

v1 of this skill remains **REST-first**; MCP is optional.

## Explicit non-use (v1)

- OAuth app flow
- Webhooks
- MCP Plane server as a hard dependency
- Mandatory labels / worklogs / close-out state machines (in-project task tracking is a different skill)