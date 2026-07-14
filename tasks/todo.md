# TODO: Keyless subscription pipeline (B-006)

**Plan**: [`tasks/plan.md`](./plan.md) · **Spec**: [`docs/specs/B-006-keyless-subscription-pipeline.md`](../docs/specs/B-006-keyless-subscription-pipeline.md)
**Status**: awaiting LGTM on the plan before starting.

## Todo (dependency-ordered)

- [x] **T0** — Env: `claude-agent-sdk` imports; keyless smoke `query()` proven (install workaround: `--ignore-installed PyJWT`; `IS_SANDBOX=1` under root). Full requirements install fix → T6.
- [x] **T1** — `src/agent_sdk/research/claude_web.py` → `build_claude_web_brief()` (WebSearch/WebFetch) + 3 tests green
- [x] **T2** — Wired `research_mode="claude_web"` through `run_stage3` dispatch + `run_pipeline` type; routing + env-override tests green. (CLI `--research-mode`/`--image-mode` end-to-end flags deferred to the Checkpoint B live-run wiring.)
- [x] **— CHECKPOINT A —** `run_pipeline(chart_only, claude_web)` with all keys unset → `publication_validator_passed=True`, 0 issues. Surfaced + fixed two pre-existing chart-embed bugs (BUG-038 `!`→`.` mangling of `![`; BUG-039 chart_only strip-before-embed ordering) with regression tests. Full suite: 2234 passed, no regressions.
- [x] **T3** — Rerouted `refine_image_metadata` to `query()`+Read vision, dropped key gate; 7 vision tests rewritten; arch-check clean
- [x] **T4** — `economist_agent._abort_if_keyless()` fail-loud message + 2 tests
- [x] **T5** — ADR-0012 (keyless claude_web research); registered in mkdocs; adr-lint passes
- [x] **T6** — `--research-mode`/`--image-mode` CLI + end-to-end chart_only path; runbook `docs/keyless-pipeline-runbook.md`; `BACKLOG.md` B-006
- [~] **— CHECKPOINT B —** live keyless subscription run (4 runs). **Keyless foundation PROVEN**: research (claude_web WebSearch), writer, and graphics all execute with ANTHROPIC/OPENAI/SERPER unset. Surfaced + fixed 5 pre-existing bugs against the real CLI (BUG-038 writer fence, 039 chart_only strip-order, 040 fence-body-delete, 041 turn-cap crash, 042 chart title). **Not yet a clean validator-pass**: the writer via the CLI is non-deterministic (run1 fence, run4 empty body) and `_run_end_to_end` uses single-shot `run_pipeline` (no retry), whereas `flow.py` EconomistContentFlow has the revision/retry loop built for this. Decision pending: route end-to-end through flow.py's retry loop vs. add a bounded Stage-3 retry.

## Done

_(none yet)_
