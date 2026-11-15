# Cross-Project Plane Skill — Spec Index

English design specs for a personal agent skill that, when work in the **current** project depends on a change **outside** that project, finds the matching Plane Cloud project and either comments on an existing work item or creates a new one.

| Doc | Purpose |
| --- | --- |
| [01-overview.md](01-overview.md) | Problem, goals, non-goals, decisions locked with the product owner |
| [02-architecture.md](02-architecture.md) | Components, REST vs MCP, runtime layout for Cursor and Claude |
| [03-credentials-and-config.md](03-credentials-and-config.md) | User-level secrets and config under `~/.config/cross-project-plane/` |
| [04-registry.md](04-registry.md) | Central dependency → Plane project registry (no hard-coded project lists in skills) |
| [05-project-resolution.md](05-project-resolution.md) | How to resolve a Plane project GUID; heuristic fallback; foreign targets |
| [06-dedup-and-actions.md](06-dedup-and-actions.md) | Similarity heuristics; create vs comment; ask-on-doubt |
| [07-agent-workflow.md](07-agent-workflow.md) | End-to-end agent procedure when an external need appears |
| [08-skill-contract.md](08-skill-contract.md) | Skill packaging for Cursor IDE and Claude; triggers; scripts |
| [09-logging.md](09-logging.md) | Audit log for idempotency across sessions |
| [10-plane-api-binding.md](10-plane-api-binding.md) | Concrete Plane Cloud API usage assumptions |

**Status:** design / pre-implementation.  
**Audience:** implementers of the personal skill and supporting CLI helpers.
