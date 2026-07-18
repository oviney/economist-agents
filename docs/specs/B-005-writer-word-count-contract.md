# Spec: B-005 · Writer word-count contract (single source of truth + structured prompt)

> Backlog item: **B-005** (`type:bug`/`type:chore`). Follow-up carried forward from
> B-004 (the intentionally-deferred word-count item). Branch:
> `claude/blog-pipeline-root-cause-7ifjsv`.

## Objective

Short drafts are the **one remaining** cause of the "always fails" quarantine that
B-004 did not address: an article body under 700 words is a CRITICAL
`word_count` rejection (`publication_validator.py:447`), and unlike date/categories
it cannot be deterministically fabricated. The logged run was 638 words.

Two problems compound it:

1. **Threshold drift — no single source of truth.** The numbers are scattered and
   inconsistent:
   - `publication_validator._check_word_count` **docstring says "at least 800"** but
     the **code enforces `< 700`** (`:437` vs `:447`) — a lie in the contract.
   - `article_evaluator` soft-penalises `< 600` and `> 1500` (`:412`).
   - `stage3_runner` writer prompt asks for "at least 850 words" (`:176`).
   - The deprecated `writer_agent` self-validation warns at 800.
2. **The writer prompt states a number but gives no structure to hit it.** "At least
   850 words" with no per-section budget under-delivers more often than an explicit
   "4–5 sections of ~200 words each" contract.

**Goal:** one authoritative word-count contract (constants), referenced by both the
validator and the writer prompt, and a writer prompt that gives the model a
*structured* budget — raising the odds a first draft clears the floor with margin.

## Scope

**In scope (deterministic, verifiable in THIS Cloud session — no API keys)**
1. Add word-count constants to `scripts/publication_validator.py` (single source of
   truth, beside `BLOG_AUTHOR`): `WORD_COUNT_MIN = 700`, `WORD_COUNT_TARGET = 850`,
   `WORD_COUNT_MAX = 1200`.
2. Fix the drift: `_check_word_count` docstring + message + threshold all read from
   the constant (no literal `700`/`800` split; docstring stops claiming 800).
3. Rewrite the `stage3_runner._build_writer_prompt` length paragraph into a
   structured contract that references `WORD_COUNT_TARGET`/`MIN` (e.g. "Target
   ~{TARGET} words across 4–5 body sections of ~180–220 words each; the validator
   rejects anything under {MIN}, so never come in short").
4. A small pure helper `word_count_shortfall(article) -> str | None` (in the
   validator module) returning specific expansion feedback when a body is short —
   shared by the validator message and available to callers as revision feedback.

**Out of scope (non-negotiable — scope discipline)**
- **Any LLM retry/regeneration loop.** That is exactly what destroyed the frontmatter
  before B-004. First-draft quality + the B-004 finalize net is the strategy; we do
  not add fragile self-correction loops.
- Changing the *values* of the gate (700 stays the floor) — this is consolidation,
  not re-tuning. Re-tuning needs live data (see Open Questions).
- The deprecated `writer_agent.py` / `content-writer.yaml` prompts (production is
  `stage3_runner.py`; touching the dead path is scope creep).
- The `article_evaluator` 600/1500 soft-penalty (a deliberately looser scoring band;
  consolidating it risks changing scores — left alone, noted).

## Decision: constants in the validator, imported by the prompt builder

**Chosen:** The floor is *defined by* the validator, so the constants live in
`scripts/publication_validator.py` and `stage3_runner.py` imports them for the
prompt. This guarantees the prompt can never drift below what the gate enforces.

**Rejected:** A new `constants.py` module (over-abstraction for three ints);
duplicating the numbers in the prompt (the drift we're removing).

## The API constraint (honest scoping)

This session has **no `ANTHROPIC_API_KEY`**, so the *behavioural* claim — "real
articles now clear {TARGET} words" — **cannot be verified here** and is **not**
claimed done. It is a live-run acceptance criterion the human executes (§Success
Criteria 6). Everything in scope above is verifiable in-session at the
constant/contract/unit level.

## Commands

```
Setup (session):   pip install pytest pyyaml orjson ruff==0.14.10 ; export PYTHONPATH=$(pwd)
Test (validator):  python3 -m pytest tests/test_publication_validator.py -q
Test (new):        python3 -m pytest tests/test_word_count_contract.py -q
Lint:              python3 -m ruff check scripts/publication_validator.py src/agent_sdk/stage3_runner.py
Live (human, later): ANTHROPIC_API_KEY=… SERPER_API_KEY=… python -m src.agent_sdk.pipeline  # confirm body ≥ TARGET
```

## Code Style

Constants mirror `BLOG_AUTHOR` (module-level, typed by literal, commented):

```python
# scripts/publication_validator.py
WORD_COUNT_MIN = 700       # hard floor: body under this is a CRITICAL rejection
WORD_COUNT_TARGET = 850    # writer aim — above the floor for safety margin
WORD_COUNT_MAX = 1200      # editorial upper guidance (advisory, not enforced here)
```

`_check_word_count` reads the constant; the helper is pure and importable:

```python
def word_count_shortfall(article: str) -> str | None:
    """Return specific expansion feedback if the body is under WORD_COUNT_MIN,
    else None. Pure — used by the validator message and as revision feedback."""
```

Prompt builder imports and interpolates — no bare literals:

```python
from scripts.publication_validator import WORD_COUNT_MIN, WORD_COUNT_TARGET
...
f"Target ~{WORD_COUNT_TARGET} words across 4–5 body sections of ~180–220 words "
f"each. The publication validator rejects anything under {WORD_COUNT_MIN}, so "
f"never come in short.\n\n"
```

## Testing Strategy (all no-API)

`tests/test_word_count_contract.py`:
- **Single source of truth:** the prompt built by `_build_writer_prompt` contains
  `str(WORD_COUNT_TARGET)` and `str(WORD_COUNT_MIN)` — proves no drift possible.
- **Docstring/message consistency:** `_check_word_count` message quotes
  `WORD_COUNT_MIN`; a body of exactly `MIN` words passes, `MIN-1` fails CRITICAL.
- **Helper:** `word_count_shortfall` returns None at/above `MIN`, and specific
  feedback (mentioning the actual count) below it.
- **Regression:** existing `tests/test_publication_validator.py` still green
  (threshold value unchanged at 700).

If importing `stage3_runner` pulls the Anthropic SDK (not installed here), the
prompt-contract test imports `_build_writer_prompt` guarded by
`pytest.importorskip("claude_agent_sdk")`, and a fallback test asserts the
constants are consistent — so the suite is green in this session regardless.

## Boundaries

- **Always:** keep 700 as the enforced floor; run validator + new tests + ruff
  before push; keep the diff to `publication_validator.py`, `stage3_runner.py`,
  and the new test file.
- **Ask first:** re-tuning any threshold value; touching the evaluator band or the
  deprecated writer path.
- **Never:** add an LLM retry loop; claim the behavioural target verified without a
  live run; duplicate the word-count numbers as literals in the prompt.

## Success Criteria

1. `WORD_COUNT_MIN/TARGET/MAX` defined once in `publication_validator.py`; grep shows
   no bare `700`/`800` word-count literals in `_check_word_count` or the prompt.
2. `_check_word_count` docstring, message, and threshold are mutually consistent
   (no more "says 800, enforces 700").
3. `_build_writer_prompt` output embeds `WORD_COUNT_TARGET` and `WORD_COUNT_MIN`
   and a per-section budget.
4. `word_count_shortfall` unit-tested (None ≥ MIN; specific feedback < MIN).
5. New + validator test suites green; ruff clean; `current` behaviour of the 700
   gate unchanged (regression).
6. **[Human, live run]** A real pipeline run produces a body ≥ `WORD_COUNT_TARGET`
   and clears the validator without a `word_count` CRITICAL. *(Cannot be run in this
   API-key-less session.)*

## Open Questions

- **Is 700 the right floor, or should it rise to 850?** Deferred — re-tuning needs
  live data on what the writer actually produces post-prompt-change. This spec
  consolidates the existing floor; it does not move it.
