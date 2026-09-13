# Spec: B-004 · Deterministic frontmatter finalize so mechanical defects never quarantine

> Backlog item: **B-004** (`type:bug`). Defect **BUG-038**. Fixes the recurring
> pipeline quarantine documented in `generation.log`.
>
> **Retroactive note (honest):** the implementation for this spec already exists
> on branch `claude/blog-pipeline-root-cause-7ifjsv` (commit `ad86e7f`). It was
> written before the `spec-driven-development` lifecycle was invoked. This spec
> documents the intended behaviour and the acceptance gates the change must meet;
> the `test`/`review` phases below validate the existing code against it rather
> than re-deriving it. Where the code and this spec disagree, this spec wins and
> the code is corrected.

## Objective

The content pipeline must never quarantine an otherwise-publishable article for a
**mechanically-fixable** frontmatter defect. Evidence — the last real run
(`generation.log`) did all the expensive work (research, a paid DALL-E image,
writing, editing, hostile critique) and was then rejected for a **single**
CRITICAL:

```
❌ REJECTED - 1 CRITICAL ISSUE
1. DATE_MISMATCH: article shows 2026-01-01, expected 2026-01-10
```

The date is a value a computer can set correctly in 100% of cases. The pipeline
instead marked it CRITICAL, tried to fix it via LLM regeneration (which deleted
the frontmatter entirely — `No YAML front matter found`), and quarantined.

**Goal:** one deterministic finalize step guarantees a complete, valid frontmatter
block (`date` stamped to today; `categories`/`image`/`description`/`layout`/
`author` present; block reconstructed if the LLM emitted none) immediately before
publication validation, so the validator only ever fails on genuinely un-fixable
**content** problems (e.g. word count).

## Scope

**In scope**
1. Harden `src/agent_sdk/_shared.py:apply_editorial_fixes` so that **when a
   finalize `current_date` is supplied** it guarantees valid frontmatter:
   reconstruct a missing block (title derived from the article H1); add a missing
   `date`; fill missing `image`/`description`.
2. Wire `apply_editorial_fixes(current_date=today)` into the deprecated
   `scripts/economist_agent.py` immediately before `PublicationValidator`, which
   today calls no finalizer at all (the production `flow.py` path already
   finalizes via Stage 4 `stage4_runner.py`).
3. Regression tests (`tests/test_frontmatter_finalize.py`) proving the mechanical
   defects survive finalize as a publishable article, asserted against the **real**
   `PublicationValidator` and `FrontmatterSchema`.

**Out of scope** (non-negotiable — scope discipline, Core Behavior #5)
- **Word-count failures.** `< 700` words is a legitimate content shortfall the
  validator *should* block; a finalizer must not fabricate prose to game the gate.
  The upstream fix (writer prompt targeting ~900 words) needs a live API run to
  verify and is a separate item.
- Behaviour change when `current_date is None` (unit-test / non-finalize callers) —
  must remain byte-for-byte identical.
- Deleting or migrating the deprecated `economist_agent.py` path, or repointing
  `run.sh` / `run_full_workflow.sh` at `flow.py` (larger change; separate item).
- Touching the dead `_EDITOR_AGENT_PROMPT_LEGACY` hardcoded dates (unused; leaving
  it is scope discipline, not an endorsement).

## Decision: harden the shared finalizer, gated on `current_date`

**Chosen:** Both pipelines already share `apply_editorial_fixes`. Extend it so the
presence of `current_date` (which only the real pipelines pass) is the signal that
"this is a real finalize pass — guarantee valid frontmatter." Unit tests that call
it without `current_date` are unaffected.

- Deterministic. No LLM in the fix path — the exact anti-pattern that failed
  (LLM regeneration destroying frontmatter) is removed for metadata.
- One code path serves both the production `flow.py`/Stage 4 pipeline and the
  deprecated local pipeline once the latter is wired to call it.

**Rejected:** Downgrading the validator's `DATE_MISMATCH`/`categories` severity
(hides the signal instead of fixing the cause; other callers rely on those gates).
Fixing only the old pipeline (leaves the shared finalizer fragile for production).

## Commands

This Cloud session has **no API keys** (`ANTHROPIC/OPENAI/SERPER` unset) and no
`.venv`, so only deterministic logic + mocked/unit tests are runnable here.

```
Setup (session):   pip install pytest pyyaml orjson ruff==0.14.10 ; export PYTHONPATH=$(pwd)
Test (new):        python3 -m pytest tests/test_frontmatter_finalize.py -q
Test (regression): python3 -m pytest tests/test_stage4_editorial_fixes.py -q
Test (validators): python3 -m pytest tests/test_publication_validator.py tests/test_frontmatter_schema.py -q
Lint:              python3 -m ruff check src/agent_sdk/_shared.py scripts/economist_agent.py tests/test_frontmatter_finalize.py
```

## Code Style

New helpers are small, typed, docstringed, and live beside the other frontmatter
helpers in `_shared.py`; the guarantee logic is gated on `current_date`:

```python
if current_date and not text.startswith("---"):
    title = _derive_title(text)          # H1 → first prose line → fallback
    text = f'---\nlayout: post\ntitle: "{title}"\ndate: {current_date}\n---\n\n' + text

# inside the existing `if text.startswith("---")` completion block:
if current_date and "date:" not in fm:
    fm = fm.rstrip() + f"\ndate: {current_date}\n"
if current_date and "image:" not in fm:
    fm = fm.rstrip() + f'\nimage: "{_DEFAULT_IMAGE}"\n'
if current_date and "description:" not in fm:
    fm = fm.rstrip() + f'\ndescription: "{_derive_description(parts[2])}"\n'
```

All derived scalars pass through `_yaml_safe` (strips `"`/newlines, caps length)
so reconstructed frontmatter always parses.

## Testing Strategy

TDD-in-spirit (retroactive): `tests/test_frontmatter_finalize.py` feeds in the
exact defects and asserts the outcome against the real validators — no API, no
mocks of the validator itself.

- **Reconstruction:** missing frontmatter + `current_date` → all `REQUIRED_FIELDS`
  present, `title` from H1, `date == current_date`, body preserved.
- **Completion:** partial frontmatter → missing `date`/`categories`/`image`/
  `description` added; stale `date` overwritten; idempotent on a second pass.
- **Backwards compat:** no `current_date` → plain text is **not** wrapped; no
  `date` injected. (Guards the 41 existing `test_stage4_editorial_fixes` cases.)
- **End-to-end (the regression):** after finalize, `PublicationValidator(expected_date=today)`
  reports **zero** CRITICALs among `{date_mismatch, yaml_format, categories, layout}`
  for a body ≥ 700 words; and the reconstructed frontmatter passes `FrontmatterSchema`.

## Boundaries

- **Always:** run the three test suites + ruff before push; keep the diff to
  `_shared.py`, `economist_agent.py`, and the new test file; preserve `current_date is None`
  behaviour exactly.
- **Ask first:** any change to validator severities, the word-count gate, or
  repointing the local entrypoints at `flow.py`.
- **Never:** fabricate body content to pass word count; add an image/description
  default in the `current_date is None` path; touch unrelated `_shared.py` helpers.

## Success Criteria

1. A draft with **missing frontmatter** yields, after finalize, zero mechanical
   CRITICALs from the real `PublicationValidator` and passes `FrontmatterSchema`.
2. A draft with a **stale `date`** yields no `date_mismatch` CRITICAL after finalize.
3. `apply_editorial_fixes(x)` (no `current_date`) is byte-for-byte unchanged vs.
   pre-change behaviour — all 41 `test_stage4_editorial_fixes` cases still pass.
4. `scripts/economist_agent.py` finalizes the edited article before validation.
5. `tests/test_frontmatter_finalize.py` (14 cases) + validator/schema suites (89)
   green; ruff clean.

## Open Questions

_(none — root cause verified against `generation.log` and the real validators;
word-count remains an intentionally-separate content item.)_
