# PLAN: Keyless subscription pipeline (B-006)

**Spec**: `docs/specs/B-006-keyless-subscription-pipeline.md` (approved — go to plan)
**Branch**: `claude/pipeline-status-check-mwptdh`
**Status**: DRAFT — awaiting human LGTM before implementation

## Goal restated

One command, **all three keys unset**, produces a `publication_validator`-passing
article using only the Claude subscription (Agent SDK). Auth + keyless WebSearch
already proven in-session.

## Dependency graph

```
T0 env (install SDK + IS_SANDBOX)         ← unblocks all runtime verification
      │
      ▼
T1 claude_web researcher  ──►  T2 wire research_mode through stage3+pipeline+CLI
                                     │
                                     ▼
                              [CHECKPOINT A]  keyless article via mocked test
                                     │
      ┌──────────────────────────────┼───────────────────────────┐
      ▼                              ▼                            ▼
T3 vision→query() (D3)      T4 economist_agent fail-loud (D1)   T5 ADR (D4)
      └──────────────────────────────┼───────────────────────────┘
                                     ▼
                              T6 runbook + BACKLOG + install fix
                                     │
                                     ▼
                              [CHECKPOINT B]  live keyless run → validator exit 0
```

T1→T2 is the only hard chain. T3/T4/T5 are independent and parallelizable after
Checkpoint A. Each task is a vertical slice (produces an observable result), each
tested and committed per `incremental-implementation`.

## Tasks

### T0 — Env: reliable keyless SDK install *(unblocker)*
- Make `claude-agent-sdk` installable without the `sgmllib3k`/feedparser wheel
  failure aborting the transaction (pin/isolate, or document a two-step install).
- Document `IS_SANDBOX=1` requirement when running as root.
- **AC**: `python -c "import claude_agent_sdk"` succeeds; keyless smoke `query()`
  returns text. **Verify**: run `scratchpad/smoke.py` with keys unset.

### T1 — `claude_web` researcher
- New `src/agent_sdk/research/claude_web.py`:
  `async build_claude_web_brief(topic, max_budget_usd=None) -> tuple[str, float]`.
- Uses `query()` with `allowed_tools=["WebSearch","WebFetch"]`, research-analyst
  system prompt; returns a brief **string** matching `_format_brief` shape
  (claims + source names + URLs) and the SDK cost.
- **AC**: given a mocked `query()` transcript, returns a non-empty brief string
  with sources; reads no `SERPER_API_KEY`; constructs no `anthropic` client.
- **Verify**: `pytest tests/test_claude_web_research.py -q`.

### T2 — Wire `research_mode="claude_web"` through the stack
- `stage3_runner.run_stage3`: add `"claude_web"` to the allowed set
  (lines 424–435) → dispatch to `build_claude_web_brief`.
- `pipeline.run_pipeline`: accept/thread `research_mode="claude_web"`.
- `pipeline.main`: add `--research-mode` choice `claude_web` (+ `--image-mode`).
- **AC**: `run_pipeline(topic, image_mode="chart_only", research_mode="claude_web")`
  with mocked `query()` and **all keys unset** returns
  `publication_validator_passed=True`; asserts no Serper/anthropic client built.
- **Verify**: `pytest tests/test_pipeline_keyless.py -q`.

> **CHECKPOINT A** — keyless article generated in a deterministic (mocked) test;
> prove zero paid-client construction. Stop, show green, get go for T3–T6.

### T3 — Vision refinement off the API key (D3)
- `_shared.refine_image_metadata`: replace `anthropic.AsyncAnthropic` path with
  `query()` vision (image passed to the SDK); drop the `ANTHROPIC_API_KEY` gate;
  keep graceful fallback to writer drafts on any error.
- **AC**: mocked `query()` → refined alt/caption; error → drafts. No
  `ANTHROPIC_API_KEY` read. (Off critical path for `chart_only`; matters for hero.)
- **Verify**: `pytest tests/test_vision_refine_keyless.py -q`.

### T4 — `economist_agent.py` fail-loud (D1)
- Deprecated path: on a keyless invocation, raise/exit with a clear
  "use `python -m src.agent_sdk.pipeline --research-mode claude_web`" message
  instead of a raw `KeyError`/`ValueError`.
- **AC**: keyless run of the deprecated entry prints the guidance, exits non-zero.
- **Verify**: `pytest tests/test_economist_agent_deprecation.py -q`.

### T5 — ADR: LLM in the research path (keyless mode) (D4)
- `docs/adr/00NN-llm-research-keyless-mode.md`: record the deliberate departure
  from "no LLM in research"; scope it to `claude_web` mode only; note
  non-determinism and that citation gates remain enforced.
- **AC**: ADR passes the repo's adr-lint gate. **Verify**: adr-lint script green.

### T6 — Runbook + backlog + install fix
- Doc: keyless run recipe (env + command + the honest research caveat).
- `BACKLOG.md`: add B-006, mark Done on merge.
- **AC**: doc committed; `BACKLOG.md` updated.

> **CHECKPOINT B** — behavioural: `IS_SANDBOX=1 python -m src.agent_sdk.pipeline
> --image-mode chart_only --research-mode claude_web` with **no keys** →
> article on disk, `publication_validator.py` exit 0. This is the real proof;
> subscription-billed, not CI. (I can run this here.)

## Non-goals (scope discipline, per spec §8)

Not converging/deleting the two pipelines; not touching hero/DALL-E generation;
not removing the Serper `deterministic` mode (only adding a keyless sibling).

## Test strategy summary

All new tests keyless + offline via **mocked `query()`** so CI needs no
subscription. The one subscription-dependent step is Checkpoint B (human/live),
explicitly out of CI. Existing suite must stay green.
