# 04 — Central Registry

## Purpose

Map a **dependency identity** (how the consumer refers to an external system) to a **Plane project** (`workspace_slug` + `project_id` UUID), without embedding that map in skill markdown or in each consumer repo.

The registry is the **write-back cache** for successful resolutions.

## File

`~/.config/cross-project-plane/registry.json`

```json
{
  "version": 1,
  "updated_at": "2026-11-15T13:00:00Z",
  "entries": {
    "npm:@acme/payments-sdk": {
      "workspace_slug": "acme",
      "project_id": "4af68566-94a4-4eb3-94aa-50dc9427067b",
      "project_name": "Payments SDK",
      "project_identifier": "PAY",
      "aliases": ["payments-sdk", "@acme/payments-sdk"],
      "signals": {
        "git_remotes": ["github.com/acme/payments-sdk"],
        "package_names": ["@acme/payments-sdk"],
        "plane_json_paths": ["../payments-sdk/.plane.json"]
      },
      "confidence": 1.0,
      "source": "manual|heuristic|user_confirmed|plane_json",
      "created_at": "2026-11-01T10:00:00Z",
      "last_used_at": "2026-11-15T12:00:00Z",
      "last_verified_at": null
    }
  }
}
```

## Dependency keys

Keys are stable, lowercase-normalized strings with a **kind prefix**:

| Kind | Key pattern | Examples |
| --- | --- | --- |
| npm | `npm:<name>` | `npm:@acme/foo`, `npm:foo` |
| pypi | `pypi:<name>` | `pypi:acme-foo` |
| git | `git:<host>/<owner>/<repo>` | `git:github.com/acme/foo` |
| mcp | `mcp:<server-name>` | `mcp:acme-transcriber` |
| http | `http:<host>/<api-id>` | `http:api.acme.internal/billing` |
| plane | `plane:<workspace>/<project_identifier>` | `plane:acme/PAY` |
| generic | `name:<slug>` | `name:billing-api` |

The agent chooses the most specific key available from context (lockfile / import path / MCP config / base URL). Multiple keys may point at the same project via `aliases` or duplicate entries with the same `project_id`.

## Lookup algorithm

1. Normalize candidate keys from the current external need (possibly several).
2. Exact match on `entries` keys.
3. Match against any entry's `aliases` (case-insensitive).
4. Match against `signals.package_names` / `signals.git_remotes`.
5. If hit → update `last_used_at` → return project coords.
6. If miss → run [project resolution](05-project-resolution.md).

## Write-back rules

When heuristic (or user) resolution succeeds:

| Confidence / source | Write registry? |
| --- | --- |
| User confirmed a choice | Yes (`source: user_confirmed`, `confidence: 1.0`) |
| Single high-confidence heuristic match and `auto_write_registry_on_confident_match` | Yes (`source: heuristic`) |
| Ambiguous set resolved only after ask | Yes for the chosen project |
| Foreign / no match | **Do not** write a negative entry that blocks future discovery; optionally log only |
| Low confidence without ask | **Do not** write |

Upsert merges aliases/signals; never delete unknown fields from an existing entry.

## Manual edits

Users may edit `registry.json` by hand or via a future `registry_upsert` helper. Manual entries use `source: manual`.

## What must not live in the registry

- API keys
- Full issue descriptions
- Hard requirement that every org package is pre-seeded (empty registry is valid; learning fills it)

## Invalidation

- If API returns 404 for `project_id`, mark entry stale (or remove) and re-run resolution.
- Optional periodic `last_verified_at` refresh is out of scope for v1 beyond 404 handling.
