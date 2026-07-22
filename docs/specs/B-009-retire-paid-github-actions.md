# Spec: B-009 · Retire paid-AI GitHub Actions; keyless local run is the only generation path

> Backlog item: **B-009** (`type:chore`). Executes
> [ADR-0014](../adr/0014-retire-paid-github-actions-generation.md). Depends on
> #438/#440 (removed pay-per-use research) and #439 (hardened the free
> replacements), all merged to `main`.

## Objective

Make a keyless local/subscription run the **only** way articles are generated
and published, and remove every GitHub Actions workflow that requires a paid-AI
key. This closes a standing contradiction: CLAUDE.md #5 and ADR-0013 mandate
keyless/subscription-only operation, yet four workflows still inject
`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `SERPER_API_KEY`, and the weekly
`content-pipeline.yml` cron has failed 8 consecutive runs (no live article since
2026-04-27).

**Success = zero paid-AI keys anywhere in `.github/workflows/`, and one
documented keyless command that both generates an article and opens a PR on
`oviney/blog`, proven by a real end-to-end run.**

## Assumptions (correct me before I plan)

1. **The canonical keyless generate+publish command already exists** and needs
   no new wiring: `python -m src.economist_agents.flow`. Its `main()` builds
   `EconomistContentFlow()` with the default `image_mode="chart_only"` (keyless,
   no DALL-E), and `kickoff()` runs `run_pipeline(research_mode="deterministic")`
   — which post-#438 is keyless (arXiv + Semantic Scholar) — then calls
   `_deploy_to_blog`, which opens the blog PR on the free `BLOG_REPO_TOKEN`.
   → B-009 is therefore **delete + strip + doc-fix + verify**, not new code.
2. **`docs/keyless-pipeline-runbook.md` documents the wrong command** for the
   full flow: `python -m src.agent_sdk.pipeline …` generates and validates but
   does **not** publish. The runbook should present `python -m
   src.economist_agents.flow` as the canonical generate+publish command, and
   keep the `pipeline` command only as the generate-only/validate path.
3. **`blog-quality-audit.yml` needs no paid AI, but its cron is a spam vector.**
   `ArticleEvaluator.evaluate` is purely heuristic (`_score_opening`/
   `_score_evidence`/…, no LLM); `blog_quality_audit.py` reads only `GH_TOKEN`/
   `DRY_RUN`, so `OPENAI_API_KEY` is vestigial. But the weekly `cron` re-scans
   the *entire* back-catalogue with no date filter and files a GitHub issue per
   post below threshold, and `existing_issue_title()` dedupes on `state=open`
   only — so a closed quality issue is **re-created every Monday**. With
   `content-pipeline.yml` deleted there is also no upstream producer, so the
   cron just re-spams a static blog. → **strip the key AND remove the cron,
   keeping `workflow_dispatch`** (it has a `dry_run` input) for on-demand use.
   This matches ADR-0014's "generation/automation is owner-initiated now"
   posture. (Decision from the doubt-driven review of the two spec open
   questions.)
4. **`ci.yml`'s `OPENAI_API_KEY` is vestigial.** Tests mock external APIs
   (CLAUDE.md standard); the last PR CI runs were green with it present. Removing
   it should be inert — but this is **verified by a green CI run, not assumed**.
5. **Deleting the DALL-E *script* is out of scope.** `featured_image_agent.py`
   is referenced by `adapters.py`, `economist_agent.py`,
   `test_featured_image_agent.py`, and `pre_commit_arch_check.py`'s
   architecture-compliance check. B-009 deletes the *workflow*
   (`regenerate-image.yml`); removing the script is a separate, entangled
   cleanup → flag as a follow-up item, do not attempt here.

## Scope

**In:**
- Delete `.github/workflows/content-pipeline.yml` (scheduled paid generation;
  also an `image_mode='hero'` + `OPENAI_API_KEY` path, a CLAUDE.md #4 violation).
- Delete `.github/workflows/regenerate-image.yml` (DALL-E 3 automation; violates
  CLAUDE.md #1/#4).
- Strip `OPENAI_API_KEY` from `.github/workflows/ci.yml`.
- Strip `OPENAI_API_KEY` from `.github/workflows/blog-quality-audit.yml` **and
  remove its `schedule:` cron**, leaving `workflow_dispatch` (with `dry_run`) as
  the only trigger.
- **Triage `.github/workflows/remediation-sync.yml`:** its Monday cron runs
  `gh workflow run content-pipeline.yml` (line ~149), which B-009 deletes — so
  it would fail at runtime post-merge. Retire the workflow or remove the
  content-pipeline trigger step so no scheduled job references a deleted
  workflow. (Discovered by the doubt-driven review — was a hidden coupling.)
- Fix `docs/keyless-pipeline-runbook.md` to name `python -m
  src.economist_agents.flow` as the canonical keyless generate+publish command;
  document the required env (`BLOG_REPO_TOKEN`; `IS_SANDBOX=1` only when running
  as root) and that it opens a blog PR you then merge.
- Correct CLAUDE.md's remaining paid contradiction: the
  `OPENAI_API_KEY | For images | DALL-E 3` Environment-Variables row.
- **Fully correct README.md's run docs** (not just add a link — the doc is
  comprehensively stale): the "via Serper" research line (~L29); the env table
  advertising `ANTHROPIC_API_KEY | Yes` / `SERPER_API_KEY | Recommended` /
  `OPENAI_API_KEY | DALL·E 3` (~L82-84); the Usage block naming the
  non-publishing `python -m src.agent_sdk.pipeline` + hero handshake as THE
  command (~L92-104); and the DALL-E note (~L175-176). Point at the runbook as
  canonical. ~20-30 lines. Leaving README split into a follow-up would park a
  live self-contradiction in `main` while every sibling doc says keyless.

**Out:**
- Deleting `featured_image_agent.py` or any DALL-E code (follow-up item).
- Any unattended/scheduled replacement for the retired cron (see ADR-0014
  "Revisit if").
- Changes to `deploy_to_blog.py` behaviour (it already opens the PR correctly;
  we only exercise it).

## Commands

```bash
# Canonical keyless generate + publish (local / in-session, subscription only):
IS_SANDBOX=1 BLOG_REPO_TOKEN=<free gh token> \
  python -m src.economist_agents.flow          # chart_only, deterministic research, opens blog PR

# Generate + validate only (no publish), e.g. for iterating on an article:
IS_SANDBOX=1 python -m src.agent_sdk.pipeline "your topic" --research-mode claude_web

# Verify no paid keys remain in workflows:
grep -rEn "ANTHROPIC_API_KEY|OPENAI_API_KEY|SERPER_API_KEY" .github/workflows/   # expect: no matches

# Verify no scheduled workflow references a deleted workflow:
grep -rEn "content-pipeline\.yml|regenerate-image\.yml" .github/workflows/       # expect: no matches

# Test suite (must stay green with no paid secrets present):
pytest tests/ -v --cov=src --cov=scripts --cov-fail-under=70
```

## Project Structure (files touched)

```
.github/workflows/content-pipeline.yml    → DELETE
.github/workflows/regenerate-image.yml    → DELETE
.github/workflows/remediation-sync.yml     → retire, or drop the content-pipeline trigger
.github/workflows/ci.yml                   → strip OPENAI_API_KEY
.github/workflows/blog-quality-audit.yml   → strip OPENAI_API_KEY + remove cron (keep workflow_dispatch)
docs/keyless-pipeline-runbook.md           → canonical command + env
CLAUDE.md                                  → fix DALL-E env row; link runbook
README.md                                  → full run-doc correction (Serper line, env table, Usage block, DALL-E note)
```

No `src/` or `scripts/` code changes are expected. If verification reveals the
flow does not actually run keyless end-to-end, that is a **new finding** — stop
and re-spec rather than silently widening scope.

## Testing Strategy

- **Regression (automated):** full `pytest` suite passes with **no** paid-AI
  secrets in the environment. Architecture-compliance and adr-lint gates stay
  green.
- **The proof (manual, required):** one real keyless run of `python -m
  src.economist_agents.flow` on the Claude subscription that (a) produces a
  publish-valid article + chart and (b) opens a PR on `oviney/blog`. Capture the
  blog PR URL in the B-009 PR description. This is the acceptance gate — the
  8-week production outage means "the code looks right" is explicitly
  insufficient.
- **Guard:** `grep` assertion above wired into the PR description (and
  optionally a tiny key-free-workflows check) so a future workflow edit
  reintroducing a paid key is visible.

## Boundaries

- **Always:** run the full test suite before commit; keep adr-lint and
  arch-compliance green; use the free `BLOG_REPO_TOKEN` for publishing, never a
  paid key.
- **Ask first:** any change to `src/`/`scripts/` code (the assumption is
  doc+workflow only); retiring `blog-quality-audit.yml` entirely rather than
  stripping it; anything that would leave `main` without a working keyless
  command.
- **Never:** add or reintroduce `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/
  `SERPER_API_KEY` to any workflow; add image-generation code; commit a token.

## Success Criteria

1. `grep -rE "ANTHROPIC_API_KEY|OPENAI_API_KEY|SERPER_API_KEY" .github/workflows/`
   returns nothing.
2. `content-pipeline.yml` and `regenerate-image.yml` no longer exist, and no
   remaining workflow references either (the second `grep` above returns
   nothing) — `remediation-sync.yml` in particular no longer triggers the
   deleted content pipeline.
3. `blog-quality-audit.yml` has no `schedule:` cron (only `workflow_dispatch`)
   and no paid-AI key.
4. `docs/keyless-pipeline-runbook.md` names `python -m
   src.economist_agents.flow` as the canonical keyless generate+publish command;
   README and CLAUDE.md no longer advertise `SERPER_API_KEY`, a required
   `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY`/DALL-E as a supported path, and both
   point at the runbook.
5. Full `pytest` + arch-compliance + adr-lint pass with no paid secrets present.
6. **A real keyless run opened a blog PR** — URL recorded in the B-009 PR.

## Open Questions — RESOLVED (doubt-driven review, `doubt-driven-development`)

1. **`blog-quality-audit.yml` — strip or retire?** → **Strip the key AND remove
   the cron**, keep `workflow_dispatch`. Keeping the schedule would re-spam the
   blog: no date filter + `state=open`-only dedup means closed issues resurrect
   every Monday, and there is no upstream producer left after
   `content-pipeline.yml` is deleted. Deleting it outright needlessly discards a
   working, tested, free tool.
2. **Its schedule.** → Removed (folded into #1).
3. **README scope.** → **In scope, full correction.** README is comprehensively
   stale and every sibling run-doc is being fixed in this slice; splitting it out
   would leave `main` self-contradictory between merges. A bare runbook link is
   insufficient.

## Follow-ups (out of scope, tracked for later)

- **Delete the DALL-E script** `featured_image_agent.py` and untangle its
  references (`adapters.py`, `economist_agent.py`, tests, arch-compliance).
- **Fix the audit's latent bugs** if it is ever re-scheduled: `existing_issue_title()`
  querying `state=open` only, and `fetch_posts()` having no recency filter. Not
  urgent now that the cron is removed (manual `dry_run` runs are safe).
