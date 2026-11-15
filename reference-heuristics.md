# Heuristics reference

## Project resolution order

1. Registry lookup (keys, aliases, package/git signals)
2. Dependency `.plane.json` (`workspace_slug`, `project_id`) — verify via API
3. List projects in `config.workspace_slugs` and score
4. Decide: resolved / ask / foreign

### Project scoring (cap 1.0)

| Evidence | Score |
| --- | --- |
| Validated dependency `.plane.json` | 1.0 (direct resolve) |
| Exact identifier match | +0.55 |
| Exact name match | +0.50 |
| Package/repo slug ↔ name (len ≥ 4) | +0.35 |
| Git path / MCP name overlap | +0.25 |
| Token Jaccard ≥ 0.5 on name | +0.15 |
| Description mentions package | +0.10 |

Auto-resolve when `best ≥ T` (default 0.75) and lead over second ≥ 0.15.
If `0.4 ≤ best < T` or close rivals → **ask**. If `best < 0.4` → **foreign**.

## Work-item dedup

Open items only when `prefer_open_states_only` is true.

| Evidence | Score |
| --- | --- |
| Title token Jaccard | up to 0.55 |
| Distinctive 2-token phrase in title | +0.25 |
| Description token Jaccard | up to 0.25 |
| Matching external_id / prior fingerprint | +0.40 |
| Tiny generic title | −0.20 |

**Judgment:** duplicate = same root cause / deliverable, not shared keywords only.

| Lexical outcome | Action |
| --- | --- |
| `best ≥ T` and clear winner | Comment |
| Several close mid/high scores | Ask |
| `0.45 ≤ best < T` | Ask |
| `best < 0.45` | Create |

When theme matches but score is middling, prefer comment on closest match or ask —
never silent second create.

## Signals JSON example

```json
{
  "names": ["ai-multi-search", "AMS"],
  "identifiers": ["AMS"],
  "package_names": ["ai-multi-search"],
  "git_remotes": ["github.com/acme/ai-multi-search"],
  "mcp_names": [],
  "plane_json_paths": ["/home/ubuntu/ai-multi-search/.plane.json"]
}
```
