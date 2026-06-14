# Spec: Migrate from GitHub MCP to a Local Backlog (Hybrid)

## Objective

Stop the token drain caused by the **GitHub MCP server** (`https://api.githubcopilot.com/mcp/`),
which injects a large bundle of tool schemas + verbose JSON responses into every
session's context, while preserving the GitHub workflows the user values.

**Decision (user, 2026-06-13): Hybrid model.**
- A **local backlog file is the system of record for planning/backlog items.**
- **GitHub stays** the system of record for **PRs + code review**, driven by the
  `gh` CLI (already authenticated, near-zero context cost).
- The **`github` MCP server is removed** from `.mcp.json`. That removal is what
  actually stops the token bleed.

**Success looks like:** a new session opens without loading any GitHub MCP tool
schema; backlog items are read/written from a versioned repo file; `gh` still
works for PRs; and CLAUDE.md + memory route future work to the local backlog
rather than re-opening GitHub issues.

### Why this matters / what it reverses

This **reverses recorded user preferences** (`feedback_github_workflow`,
`feedback_sprint_discipline` — "log all work via GitHub issues/PRs"). Those
memories must be updated as part of this change, or the next session will
silently route work back to GitHub issues and the migration won't stick.

## Scope

**In scope**
1. Remove the `github` entry from `.mcp.json` (7 other MCP servers untouched).
2. Create `BACKLOG.md` at repo root as the human-readable backlog source of record.
3. Seed `BACKLOG.md` from the **3 currently-open GitHub issues** (#420, #425, #428).
4. Close those 3 GitHub issues with a comment pointing to `BACKLOG.md` (reversible).
5. Update `CLAUDE.md` (GitHub-workflow guidance + Skill Routing) to reflect hybrid.
6. Update the three affected memory files.

**Out of scope**
- `data/skills_state/backlog.json` — left as-is. It is a machine-state file for
  autonomous sprint scripts, keyed by `STORY-NNN`, parallel to GitHub issues. Not
  the "local backlog file" the user means. Touching it risks breaking sprint tooling.
- Deleting any GitHub issues or history. We close, not delete (reversible).
- Migrating closed issues / PR history. GitHub remains the archive.
- The other 7 MCP servers, the pipeline, or any runtime code (verified: no code
  imports `mcp__github` — it is purely interactive).

## Tech Stack / Tools

- `gh` CLI (authenticated: `repo`, `project`, `workflow` scopes) — PRs, and the
  one-time issue export/close.
- Plain Markdown for `BACKLOG.md`.
- No new dependencies, no new runtime code.

## Commands

```bash
# Export the 3 open issues to seed the backlog (one-time, read-only)
gh issue list --state open --json number,title,labels,body,url

# After migration — managing the backlog is just editing a file
$EDITOR BACKLOG.md

# GitHub still drives PRs (unchanged)
gh pr create / gh pr view / gh pr list

# Verify the MCP server is gone (no github tools should appear next session)
grep -c '"github"' .mcp.json   # expect 0
```

## Project Structure

```
BACKLOG.md                      → NEW. Backlog source of record (root, versioned)
.mcp.json                       → EDIT. Remove the `github` server entry
CLAUDE.md                       → EDIT. Hybrid workflow + routing guidance
docs/specs/local-backlog-migration.md → this spec
~/.claude/.../memory/*.md       → EDIT. 3 memory files + MEMORY.md index
data/skills_state/backlog.json  → UNTOUCHED (out of scope)
```

## Code Style — `BACKLOG.md` format

Lightweight, greppable, human-editable. One section per status. Items carry a
stable `B-NNN` id (independent of GitHub issue numbers), priority, and an
optional `(was #NNN)` provenance tag for the migrated three.

```markdown
# Backlog

> Source of record for planning items. PRs + code review live on GitHub (`gh` CLI).
> Item ids are `B-NNN` and never reused.

## In Progress
_(none)_

## Todo
- **B-003** · P3 · Broken adr-lint pre-commit hook + ADR governance drift (was #428)
  - Blocks new ADRs. type:refactor.
- **B-002** · P3 · Remove asyncio.run stub in test_flow_agent_sdk.py (was #425)
  - Residual coroutine warnings. type:refactor.
- **B-001** · P3 · Wire Stage 4 author safety net to BLOG_AUTHOR constant (was #420)
  - type:refactor.

## Done
_(append items here on completion with a date)_
```

## Testing Strategy

This is a config + docs migration; no unit tests. Verification is procedural:

1. **MCP removal:** `.mcp.json` parses as valid JSON and contains no `github` key.
2. **Backlog fidelity:** all 3 open issues appear in `BACKLOG.md` with title +
   provenance; nothing dropped.
3. **Reversibility:** the 3 issues are *closed* (not deleted); each has a comment
   linking to `BACKLOG.md`.
4. **gh still works:** `gh pr list` succeeds (proves GitHub-for-PRs intact).
5. **Stickiness:** CLAUDE.md no longer instructs "open a GitHub issue" for backlog
   items; memories updated; `MEMORY.md` index consistent.

## Boundaries

- **Always:** keep `.mcp.json` valid JSON; preserve the other 7 MCP servers;
  close-not-delete on GitHub; keep changes reversible.
- **Ask first:** anything touching `data/skills_state/backlog.json` or sprint
  tooling; deleting any GitHub issue; removing MCP servers other than `github`.
- **Never:** delete GitHub issues/PRs/history; commit secrets; touch runtime
  pipeline code as part of this migration.

## Success Criteria

- [ ] `.mcp.json` has no `github` server and remains valid JSON.
- [ ] `BACKLOG.md` exists at root and contains all 3 open issues (#420/#425/#428)
      as `B-NNN` items with provenance.
- [ ] The 3 issues are closed on GitHub with a comment pointing to `BACKLOG.md`.
- [ ] `gh pr list` still works (GitHub-for-PRs path intact).
- [ ] `CLAUDE.md` describes the hybrid model and stops mandating GitHub issues for
      backlog items.
- [ ] `feedback_github_workflow`, `feedback_sprint_discipline`, and
      `project_next_session` memories updated; `MEMORY.md` index consistent.
- [ ] A note that the `github` MCP token cost is gone (no github tool schemas load
      next session).

## Open Questions

1. **Issue ids vs. backlog ids.** Spec proposes fresh `B-NNN` ids with `(was #N)`
   provenance, rather than reusing GitHub numbers. OK? (Keeps the local backlog
   independent of GitHub numbering.)
2. **Close the 3 open issues now, or leave them open** as a read-only mirror until
   you confirm the backlog feels right? Default in this spec: **close them** (clean
   single source of record), but it's a one-flag change either way.
3. **Should `gh` issue *creation* be discouraged in CLAUDE.md** going forward
   (backlog items go to BACKLOG.md), while `gh` PR commands stay encouraged?
   Default: yes.
```
