# SPEC: Keyless subscription pipeline (B-006)

**Status**: IMPLEMENTED — merged-ready via PR #447 (B-006 marked done in BACKLOG.md)
**Backlog**: B-006 (local `BACKLOG.md` item; no GitHub issue)
**Date**: 2026-07-14
**Author path**: spec-driven-development lifecycle
**Branch**: `claude/pipeline-status-check-mwptdh`

---

## 1. Objective

Make the economist-agents content pipeline generate a **validator-passing
article end-to-end with no paid API keys** — no `ANTHROPIC_API_KEY`, no
`OPENAI_API_KEY`, no `SERPER_API_KEY` — running only against the user's Claude
subscription via the Agent SDK (`claude` CLI auth), and without depending on
any github.com run.

**Target user:** the repo owner, running the pipeline locally / in this managed
environment on a Claude subscription, unwilling to provision or pay for
per-token API keys.

### Feasibility (already proven in-session)

`claude_agent_sdk.query()` returned a real completion with `ANTHROPIC_API_KEY`
unset (subscription auth via the container's authenticated `claude` CLI):

```
TEXT: PIPELINE_AUTH_OK
COST_USD: 0.043899   # subscription usage readout, not a metered API charge
```

Two environment preconditions surfaced:
1. `claude-agent-sdk` must be importable (the full `pip install -r
   requirements.txt` currently aborts on an unrelated `sgmllib3k` wheel build).
2. Under root, the SDK's `permission_mode="bypassPermissions"` →
   `--dangerously-skip-permissions` is refused unless `IS_SANDBOX=1` is set.

---

## 2. Scope decisions (LGTM checkpoints)

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Which path becomes keyless | **Production `src.agent_sdk.pipeline` / `flow.py` only** | Deprecated `scripts/economist_agent.py` left to fail loudly; PR #443 already calls it deprecated. |
| D2 | Hero image without `OPENAI_API_KEY` | **`chart_only` mode** | First-class mode already exists (`pipeline.py:105`, `flow.py` defaults to it). No DALL-E, no hero; article validates on its chart. |
| D3 | `image_alt` / `image_caption` (validator CRITICAL) | **Route vision through Agent SDK** | *Only load-bearing in `hero` mode.* In `chart_only` the hero frontmatter is stripped pre-Stage-4, so alt/caption are not required. Rewire is done for correctness/future hero runs but is **off the critical path** for the chosen keyless run. |
| **D4** | **Research without `SERPER_API_KEY`** | **Claude-driven web research via the Agent SDK** (`claude_web` mode) | Default `deterministic` research calls Serper (`pipeline.py:412`). Instead, let the Agent SDK's own `WebSearch`/`WebFetch` tools do live research on subscription. **Proven in-session with all three keys unset:** `query(allowed_tools=["WebSearch","WebFetch"])` performed a real search and returned a sourced stat + URL (`USED_A_TOOL: True`). Keyless AND live-web-verified. |

**D4 — resolved (owner's call).** Claude does its own live web research; no
Serper key. Two honest consequences, carried explicitly (not hidden):
- **Non-deterministic** research (vs. the reproducible Serper path). Acceptable
  for a zero-key run; note it in the runbook.
- **Departs from the repo's "no LLM in the research path" principle** (CLAUDE.md /
  research architecture). This is a deliberate owner decision → record it as a
  short **ADR** rather than a silent violation.
- Fabricated/weak sources are still caught downstream: the existing
  `citation_verifier` / `publication_validator` citation gates stay enforced.

---

## 3. Commands

```bash
# One-time env setup (keyless)
pip install --ignore-installed PyJWT "claude-agent-sdk>=0.1.68,<1.0.0"
export IS_SANDBOX=1            # required only when running as root

# Keyless end-to-end run (no ANTHROPIC/OPENAI/SERPER keys)
IS_SANDBOX=1 python -m src.agent_sdk.pipeline --topic "..." \
    --image-mode chart_only --research-mode claude_web

# Deterministic tests (unchanged, keyless)
PYTHONPATH=. pytest tests/ -q
```

---

## 4. Project structure (files touched)

| File | Change |
|------|--------|
| `src/agent_sdk/_shared.py` | `refine_image_metadata`: route through `claude_agent_sdk.query()` (vision) instead of `anthropic.AsyncAnthropic`; drop the `ANTHROPIC_API_KEY` gate. Keep graceful fallback to writer drafts. (D3) |
| `src/agent_sdk/pipeline.py` | Add `research_mode="claude_web"` branch; ensure `chart_only` requires no keys end-to-end. (D4/D2) |
| `src/agent_sdk/stage3_runner.py` | Accept/thread `claude_web`; no auth change (already `query()`-based). |
| `src/agent_sdk/research/` | New `claude_web` researcher: `query()` with `allowed_tools=["WebSearch","WebFetch"]` → returns a research brief with sourced claims + URLs. No Serper. (D4) |
| `docs/adr/` | Short ADR recording the deliberate "LLM in research path, keyless mode only" decision. (D4) |
| `requirements.txt` | Note the `IS_SANDBOX`/root caveat; leave `sgmllib3k`/feedparser install fix as a doc note or pin. |
| `scripts/economist_agent.py` | If a keyless run is attempted, fail with a clear "use `python -m src.agent_sdk.pipeline`" message rather than a raw KeyError. (D1) |
| `docs/` + `BACKLOG.md` | Runbook for the keyless run; mark B-006. |

No change to `flow.py`'s default `image_mode="chart_only"` — it is already correct.

---

## 5. Code style

Per `CLAUDE.md` / `skills/python-quality`: type hints mandatory, docstrings
required, `orjson` not `json`, `logger` not `print`, mock APIs in tests, >80%
coverage. Changes surgical; no architecture refactor (the two divergent
pipelines are **not** converged here — same scope discipline as PR #443).

---

## 6. Testing strategy

**Deterministic (CI-safe, keyless):**
- Unit test `research_mode="claude_web"` drives Stage 3 with a **mocked
  `query()`** (returns a canned tool-using research transcript) and asserts no
  Serper client is constructed and no `SERPER_API_KEY` is read.
- Unit test `refine_image_metadata` uses a mocked `query()` (no `anthropic`
  client, no `ANTHROPIC_API_KEY`) and still returns refined alt/caption; and
  falls back to drafts on error.
- Regression: `chart_only` + `brief_supplied` `run_pipeline` with **all three
  keys unset** produces a `publication_validator_passed=True` result (Stage 3
  `query()` mocked so the test stays offline/free).

**Behavioural (human, one live subscription run — the acceptance gate):**
- `IS_SANDBOX=1 python -m src.agent_sdk.pipeline --image-mode chart_only
  --research-mode claude_web` with no keys → article written to disk,
  `publication_validator.py` exits 0. This is the proof the whole thing works;
  it uses the subscription (incl. live `WebSearch`), not CI.

---

## 7. Acceptance criteria

1. With `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `SERPER_API_KEY` **all unset**,
   a single command produces an article that `scripts/publication_validator.py`
   accepts (exit 0, zero CRITICALs).
2. No code path on that run constructs an `anthropic.Anthropic` /
   `AsyncAnthropic` client or calls Serper.
3. The run uses `claude_agent_sdk.query()` (subscription auth) for all LLM work,
   including research (`WebSearch`/`WebFetch`).
4. Deterministic test suite stays green and keyless in CI.
5. Honest limitations documented (D4): `claude_web` research is
   non-deterministic and departs from the "no-LLM-in-research" principle;
   recorded via ADR. Existing citation gates stay enforced.

---

## 8. Boundaries

- **Always:** keep the change surgical; keyless run must never silently fall
  back to a paid key; state the research-freshness caveat plainly.
- **Ask first:** anything that would converge/delete the two pipelines, or drop
  the Serper research path for all modes (not just add a keyless one).
- **Never:** commit a key; hardcode the model marketing name into artifacts;
  claim the behavioural run passed without actually running it.
