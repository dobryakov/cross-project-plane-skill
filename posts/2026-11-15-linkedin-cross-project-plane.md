---
platform: linkedin
lang: en
---

I often run into this moment: I’m deep in one repository with an agent, and we suddenly need a change that clearly doesn’t belong here — it’s in a shared library, an internal API, or an MCP server owned by another team.

That insight used to die in the chat. Or I’d open Plane by hand, hunt for the right project, wonder if a similar work item already existed… and lose the thread of the original work.

So I built a personal skill for Cursor and Claude: **cross-project-plane**.

When progress depends on something *outside* the current repo, the agent:

1. frames the upstream need;
2. resolves the owning Plane Cloud project via a user-level registry + heuristics (no hard-coded project UUID tables, no Plane API keys stuffed into every service `.env`);
3. searches open work items for the same root cause;
4. comments optional wishes on a match — or creates a new item if none fits;
5. if nothing in Plane matches, treats it as foreign and stops (no random GitHub noise).

Credentials live once under `~/.config/cross-project-plane/`. The skill installs as a symlink to a `skill/` package. Specs and small stdlib Python helpers are in the open.

For me as an engineer, it means fewer lost follow-ups. For tech managers, it means cleaner boards: demand for upstream work shows up as comments on the real item instead of duplicate tickets.

Repo: https://github.com/dobryakov/cross-project-plane-skill

If your agents keep discovering work in the “wrong” project, this might be useful — feedback welcome.
