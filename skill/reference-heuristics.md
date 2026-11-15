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
| Title token Jaccard (alias-normalized) | up to 0.55 |
| Distinctive 2-token phrase in title | +0.25 |
| Description token Jaccard | up to 0.25 |
| Title coverage ≥ 0.7 with ≥ 3 shared title tokens | +0.40 |
| Title coverage ≥ 0.6 with ≥ 2 shared / ≥ 3 shared anywhere | +0.25 / +0.30 |
| Matching external_id | +0.40 |
| Prior audit create/comment for same dependency key (only with token overlap) | +0.35; with theme → comment |
| Tiny generic title | −0.20 |

Aliases map variants like `transcribe`/`transcribator`, `diarization`/`diarize`.

**Judgment:** duplicate = same root cause / deliverable, not shared keywords only.

| Lexical / theme outcome | Action |
| --- | --- |
| Audit hit for dependency key, or strong title coverage | Comment |
| `best ≥ T` and clear winner | Comment |
| Several close mid/high scores | Ask |
| `0.45 ≤ best < T`, or ≥ 2 shared tokens with score ≥ 0.30 | Ask |
| Weak / no overlap | Create |

Never silent second create when theme overlap is plausible — prefer comment or ask.

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
