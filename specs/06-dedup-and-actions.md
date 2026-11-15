# 06 — Dedup and Actions

## Goal

In a resolved Plane project, decide whether to **comment** on an existing work item or **create** a new one. Optional wishes always go to **comments**.

## Work-item search

Prefer a **two-pronged** open-item search when the API/MCP supports it:

1. Keyword / full-text search with distinctive title tokens.
2. Structured filter / **PQL** scoped to the project, open states only, e.g.

```pql
title ~ "<key phrase>" AND stateGroup IN openStates()
```

PQL notes (from existing Plane tooling practice): max ~5 conditions; prefer pairwise date comparisons over `BETWEEN` if dates are ever used. Fall back to paginated list + client-side filter:

```http
GET /api/v1/workspaces/{workspace_slug}/projects/{project_id}/work-items/
```

Respect `work_item_page_size` and `max_work_item_pages`. Prefer filtering to non-terminal states when `prefer_open_states_only` is true (exclude state groups `completed` / `cancelled` when expand/state data allows).

Fetch fields useful for scoring: `id`, `name`, `sequence_id`, `description` / `description_html` / stripped text, `state`, `updated_at`.

## Similarity heuristic

**Duplicate judgment:** same underlying work — same root cause / same deliverable — even when wording differs. Shared keywords alone are not enough.

Build a **query text** from the drafted change request: title-ish phrase + key technical tokens (API names, error strings, package symbols). Tokenize on non-alphanumeric; drop stopwords; keep tokens length ≥ 3.

Score each candidate work item:

| Evidence | Contribution |
| --- | --- |
| Title token overlap Jaccard | up to 0.55 |
| Title contains distinctive phrase (≥ 2 contiguous tokens from query) | +0.25 |
| Description token overlap Jaccard | up to 0.25 |
| Same `external_id` / prior audit log link for same dependency key + similar title | +0.40 |
| Agent judges same root cause / same deliverable despite weak lexical score | treat as strong candidate; if still unsure → ask |
| Very short generic title only ("fix", "Update") | penalty −0.20 |

Cap at 1.0. No embeddings in v1.

## Decision table

`T = min_confidence_to_act_without_ask` (default 0.75).

| Condition | Action |
| --- | --- |
| `best ≥ T` and clearly ahead of second | **Comment** on that work item (treat as duplicate / related) |
| Multiple candidates with scores ≥ 0.5 within 0.1 of each other | **Ask user** which to comment on, or whether to create new |
| `0.45 ≤ best < T` | **Ask user** (show top candidates + "create new") |
| Lexical score middling but theme clearly same | Prefer **comment** on closest match; if still doubtful → ask (never silent second create) |
| `best < 0.45` or no candidates | **Create** new work item |
| User says the match is wrong | **Create** new (or stop if user cancels) |

Never create and comment in the same run for the same need unless the user asks to link both.
## Create work item

**Minimum body:**

- `name` — concise actionable one-liner: what / why / where (consumer pointer). No fixed multi-section template.
- Description — free-form HTML or stripped text as the API expects (`description_html` / `description` / `description_stripped`): context from consumer project, why the dependency must change, optional repro, optional wishes.

**Do not set (v1):**

- `assignees` / `assignee_ids`
- Mandatory labels, priority, cycle, module, or invented deadlines (unless the user explicitly requests)

Optional metadata when cheap and reliable:

- `external_source`: `cross-project-plane`
- `external_id`: stable hash of `dependency_key + normalized_title` (helps future dedup)

Return to the user briefly: `{project_identifier}-{sequence_id}` (e.g. `PAY-42`), whether created or attached via comment, and app URL.

## Comment (optional wishes)

When a similar item exists:

- Prefer reading existing comments first when context may be stale (avoid repeating the same wish).
- Post a comment that states this came from consumer project X, summarizes the additional need, and lists optional wishes. Use simple HTML (`comment_html`), e.g. bold lead-in + paths in `<code>`.
- Do not rewrite the original description.
- If there is nothing new beyond "also blocked on this", still leave a short ping comment so watchers see demand signal — unless the audit log (or recent comments) show the same consumer already left the same wish fingerprint (skip duplicate pings).

API shape (v1 path example):

```http
POST /api/v1/workspaces/{slug}/projects/{project_id}/work-items/{work_item_id}/comments/
```

## Ask-on-doubt UX

When asking the user, present:

1. Dependency key and resolved project.
2. Ranked candidates: `IDENTIFIER-n`, title, score, state, updated_at.
3. Explicit options: comment on `#i` / create new / cancel / foreign.

Do not proceed with write operations until the user answers.