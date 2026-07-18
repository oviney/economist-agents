# TODO: Keyless subscription pipeline (B-006)

**Plan**: [`tasks/plan.md`](./plan.md) · **Spec**: [`docs/specs/B-006-keyless-subscription-pipeline.md`](../docs/specs/B-006-keyless-subscription-pipeline.md)
**Status**: IMPLEMENTED — all tasks + both checkpoints complete (PR #447).

## Todo (dependency-ordered)

- [x] **T0** — Env: `claude-agent-sdk` imports; keyless smoke `query()` proven (install workaround: `--ignore-installed PyJWT`; `IS_SANDBOX=1` under root). Full requirements install fix → T6.
- [x] **T1** — `src/agent_sdk/research/claude_web.py` → `build_claude_web_brief()` (WebSearch/WebFetch) + 3 tests green
- [x] **T2** — Wired `research_mode="claude_web"` through `run_stage3` dispatch + `run_pipeline` type; routing + env-override tests green. (CLI `--research-mode`/`--image-mode` end-to-end flags deferred to the Checkpoint B live-run wiring.)
- [x] **— CHECKPOINT A —** `run_pipeline(chart_only, claude_web)` with all keys unset → `publication_validator_passed=True`, 0 issues. Surfaced + fixed two pre-existing chart-embed bugs (BUG-038 `!`→`.` mangling of `![`; BUG-039 chart_only strip-before-embed ordering) with regression tests. Full suite: 2234 passed, no regressions.
- [x] **T3** — Rerouted `refine_image_metadata` to `query()`+Read vision, dropped key gate; 7 vision tests rewritten; arch-check clean
- [x] **T4** — `economist_agent._abort_if_keyless()` fail-loud message + 2 tests
- [x] **T5** — ADR-0013 (keyless claude_web research); registered in mkdocs; adr-lint passes
- [x] **T6** — `--research-mode`/`--image-mode` CLI + end-to-end chart_only path; runbook `docs/keyless-pipeline-runbook.md`; `BACKLOG.md` B-006
- [x] **— CHECKPOINT B — PASSED (run 6)** ✅ Live keyless subscription run with ANTHROPIC/OPENAI/SERPER **all unset** produced a validator-passing 1092-word article (`output/posts/crying-wolf-flaky-tests-...md`), `publication_validator PASSED`, exit 0. Six real sourced stats + URLs, embedded chart. Took 6 runs, each peeling off one pre-existing gap against the real CLI (mocked tests never exercised it): BUG-038 (`!`→`.` on `![`), 039 (chart_only strip-order), 040 (fence body-delete), 041 (graphics turn-cap crash), 042 (missing chart title), 043 (bounded writer retry for non-determinism), + budget-cap headroom for multi-turn CLI calls. All fixed with regression tests.

## Done

_(none yet)_
