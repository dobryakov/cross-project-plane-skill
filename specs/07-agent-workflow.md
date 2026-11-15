# 07 — Agent Workflow

## When to trigger

The agent should start this workflow **proactively** when, during ordinary work, it determines that progress requires a change **outside** the current project, for example:

- A bug/limitation in an internal library dependency
- A missing endpoint or behavior in an internal HTTP API
- A gap or bug in an MCP server the project relies on
- Shared infra owned by another Plane-tracked product team

Do **not** trigger for:

- Changes that belong entirely in the current repo
- Pure third-party OSS with no Plane project (will resolve foreign)
- Vague "someone should…" without a concrete dependency target
- Work the agent is **already fixing in this same turn** in the dependency itself (file only what remains deferred)

User can also invoke the skill explicitly ("file this upstream in Plane"); same pipeline.
## Procedure

Copy and track:

```text
External change request
- [ ] 1. Formulate need
- [ ] 2. Ensure credentials
- [ ] 3. Resolve dependency key
- [ ] 4. Resolve Plane project
- [ ] 5. Dedup search
- [ ] 6. Ask if ambiguous
- [ ] 7. Create or comment
- [ ] 8. Audit log + report to user
```

### 1. Formulate need

Write a short internal brief (not a rigid template) — ideally one crisp line plus detail:

- What is broken / missing (actionable)
- Which dependency (signals)
- Where it hurts in the consumer (path / feature)
- Optional wishes
### 2. Ensure credentials

If `~/.config/cross-project-plane/credentials` missing → explain bootstrap; stop.  
Optionally run `plane_auth_check.py`.

### 3. Resolve dependency key

Pick the best key kind (`npm:…`, `mcp:…`, etc.). Gather signals.

### 4. Resolve Plane project

Registry → heuristic → ask / foreign ([05-project-resolution.md](05-project-resolution.md)).  
On foreign → report and **stop** (no ticket anywhere).

### 5. Dedup search

Search open work items; score ([06-dedup-and-actions.md](06-dedup-and-actions.md)).  
Also scan `audit.jsonl` for recent actions on the same dependency key.

### 6. Ask if ambiguous

Project or work-item ambiguity → ask; wait.

### 7. Create or comment

Execute via scripts (preferred) so headers, pagination, and HTML encoding stay consistent.

### 8. Audit + report

Append audit event. Reply briefly with:

- Action taken (`created` | `commented` | `skipped_foreign` | `cancelled`)
- Work item key `{project_identifier}-{n}` + URL
- Whether registry was updated
## Concurrency and safety

- One write action per external need per turn unless user requests more.
- On HTTP failure after create uncertainty (timeout), check audit + re-search before creating again.
- Never paste API keys into the conversation.

## Interaction with normal coding

After filing:

- Continue consumer work with a workaround if possible, or
- Block and wait if the external change is a hard dependency — say so explicitly and link the Plane item.
