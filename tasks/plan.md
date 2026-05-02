# Plan: Publication Gate Hardening (issue #320)

**Spec**: SPEC.md  
**Branch**: main  
**Date**: 2026-05-02

## Goal

Add four deterministic checks to `PublicationValidator` (checks 17–20) plus
one writer-prompt instruction, so the defect classes from the human QA sweep
(blog#892–894) are caught before publication.

## Dependency graph

```
T1 (slug consistency)    ──┐
T2 (claim attribution)   ──┤
T3 (fm stat drift)       ──┼──► T5 (integration run + close #320)
T4 (internal links)      ──┤
T6 (writer prompt)       ──┘
```

T1–T4 and T6 are independent and can be done in any order.  
T5 is the final gate — run after all others are done.

## Tasks

### T1 — Check 17: slug consistency
**File**: `scripts/publication_validator.py`  
**Test class**: `TestSlugConsistency` in `tests/test_publication_validator.py`

Implement `_check_slug_consistency(self, content: str, article_path: str | None) -> None`.

Logic:
1. Return immediately if `article_path` is None.
2. Parse filename: `Path(article_path).name` → match `(\d{4}-\d{2}-\d{2})-(.+)\.md`.
3. Parse `date:` from front matter with `yaml.safe_load`.
4. CRITICAL if `str(fm_date)[:10] != filename_date`.
5. Derive canonical slug from front matter `slug:` field if present, else from
   `title:` (lowercase, `re.sub(r'[^a-z0-9]+', '-', title).strip('-')`).
6. HIGH if `filename_slug != canonical` and not `canonical.startswith(filename_slug)`.

Wire into `validate()` as check 17:
```python
self._check_slug_consistency(article_content, article_path)
```

Tests (6 cases — see SPEC.md §5).

DoD: `pytest tests/test_publication_validator.py::TestSlugConsistency -v` passes.

---

### T2 — Check 18: claim attribution
**File**: `scripts/publication_validator.py`  
**Test class**: `TestClaimAttribution`

Implement `_check_claim_attribution(self, content: str) -> None`.

Logic:
1. Split body (after front matter, before `## References`) into sentences
   (`re.split(r'(?<=[.!?])\s+')`).
2. Identify quantified sentences: contain `\d+(?:\.\d+)?%`, `\d+[×x]`,
   `\d+-fold`, or `\d+ times`.
3. For each, check sentence ± adjacent sentences for attribution phrases:
   `according to`, `per `, `reported by`, `finds? that`, `shows? that`,
   `data from`, `study by`, `research by`, `published by`, `\([A-Z][^)]+,\s*\d{4}\)`.
4. Collect unattributed sentences.
5. If any found: one HIGH issue with count and up to 3 example sentences.

Wire into `validate()` as check 18.

Tests (4 cases — see SPEC.md §5).

DoD: `pytest tests/test_publication_validator.py::TestClaimAttribution -v` passes.

---

### T3 — Check 19: front-matter stat drift
**File**: `scripts/publication_validator.py`  
**Test class**: `TestFrontmatterStatDrift`

Implement `_check_frontmatter_stat_drift(self, content: str) -> None`.

Logic:
1. Parse `description:` from front matter.
2. Find all `\d+(?:\.\d+)?%` in description.
3. For each, check verbatim presence in article body.
4. HIGH if any description stat is absent from body.

Wire into `validate()` as check 19.

Tests (3 cases — see SPEC.md §5).

DoD: `pytest tests/test_publication_validator.py::TestFrontmatterStatDrift -v` passes.

---

### T4 — Check 20: internal-link integrity
**File**: `scripts/publication_validator.py`  
**Test class**: `TestInternalLinks`

Implement `_check_internal_links(self, content: str) -> None`.

Logic:
1. Find all markdown links: `\[([^\]]+)\]\(([^)]+)\)`.
2. Skip: starts with `http`, `https`, `mailto`, `#`, `/assets/`.
3. For absolute internal paths (starts with `/`):
   - HIGH if path does not match `r'^/\d{4}/\d{2}/\d{2}/[a-z0-9-]+/?$'`.
4. If `BLOG_POSTS_DIR = os.environ.get("BLOG_POSTS_DIR")`:
   - Derive expected filename: `YYYY-MM-DD-<slug>.md` from path segments.
   - CRITICAL if file not found in that directory.

Wire into `validate()` as check 20.

Tests (5 cases — see SPEC.md §5).

DoD: `pytest tests/test_publication_validator.py::TestInternalLinks -v` passes.

---

### T6 — Writer prompt: attribution instruction
**File**: `src/agent_sdk/_shared.py`

Find the writer system prompt string (grep for `"Use ONLY statistics"`).  
Add one instruction adjacent to the existing stat rules:

> "Every sentence containing a percentage, multiplier, or quantified claim must
> name the source inline (e.g. 'According to Gartner, 2024, …' or '…, per the
> ASQ report (2023)')."

DoD: instruction present in the prompt string; `grep` confirms it.

---

### T5 — Integration run + close issue
1. `pytest tests/test_publication_validator.py -v` — all tests pass.
2. `pytest --cov=scripts.publication_validator --cov-report=term-missing` —
   new methods ≥80% coverage.
3. Run validator against `generated-article/2026-01-18-quality-metrics-executives-actually-use.md`
   to confirm no false positives on known-good content.
4. Close #320 with a comment summarising the four checks added.

DoD: CI green, #320 closed.
