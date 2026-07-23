# Tooling & Skill Adoption — Triage

Which Claude Code capabilities (beyond the agent-skills lifecycle plugin) are
worth adopting for this project. Filtered hard against the project's grain:
solo dev, keyless / no-paywall, local-first, allergic to over-engineering.

**The discipline here is saying no.** Only two candidates are real features; the
rest are habits, one-line tweaks, or parked. Nothing below is implemented.

## Adopt as a feature → backlog

| Item | Why | Gate | → |
|------|-----|------|---|
| **deep-research → research briefs** | Fixes the pipeline's real weak spot: T1 showed keyless research is flaky (arXiv/SS 429'd; `claude_web` fell back to the model's own memory). A blog lives on credible stats. | Prototype (running) must beat `claude_web` on a real topic before wiring. | **B-012** |
| **Live unlisted draft review** | Review the *rendered* post from your phone, not a PR diff. Your idea, made feasible. | 10-min leak test (theme must not surface the collection). | **B-013** (spec: `docs/ideas/live-draft-review.md`) |

## Adopt as a practice → no backlog needed

- **`/code-review` before merge.** Now that CI is gone and you merge on
  `make ci-local` (deterministic gates only), a semantic review pass is the
  missing "does this logic make sense" check. It's a habit + one line in
  CONTRIBUTING, not a build. Run it on non-trivial diffs.
- **Cut session friction.** `fewer-permission-prompts` scans transcripts and
  writes a permission allowlist to `.claude/settings.json` (via `update-config`)
  — fewer prompts on the `gh`/`make`/`pytest` calls these sessions repeat. ~2
  minutes, do it when it annoys you enough.

## Parked → revisit on trigger

- **`dataviz` for chart polish** — the matplotlib charts work; adopt only if
  chart consistency/quality starts bugging you.
- **Auto-open-preview hook** (a Stop/post-run hook via `update-config`) —
  genuinely nice, but downstream of B-013 (needs the preview surface to exist
  first). Revisit after B-013.

## Rejected → documented so we don't re-litigate

- **`schedule` / `loop` (cloud routines, recurring runs)** — you *deliberately*
  retired the weekly cron for manual/local (ADR-0014). Re-scheduling walks that
  back. Only if you ever want unattended generation again.
- **Multi-agent workflows for routine use** — powerful (deep-research *is* one),
  but a full fan-out burns large subscription usage. Reserve for a one-off
  "audit the whole codebase" moment; never routine.
- **Most MCP servers** (Drive/Gmail/Calendar/Precisely) — not relevant to a
  static blog pipeline. (Precisely is your *other* project.)

## The through-line

Everything adopted keeps the philosophy intact: **better output** (deep-research),
**better review** (live drafts, `/code-review`), **less friction** (allowlist) —
all local-first, none reintroducing paid infra or unattended cloud automation.
