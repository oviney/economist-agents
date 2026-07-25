# B-020 → B-023 · Source-integrity gates

**Status:** spec
**Date:** 2026-07-25
**Defects:** BUG-058, BUG-059, BUG-060, BUG-061, BUG-062
**Evidence:** `data/review_corpus/2026-07-24-green-light-red-ledger/`

---

## Assumptions I'm making

1. The keyless path (`python -m src.agent_sdk.pipeline`) is the only path that
   matters. The legacy `EconomistContentFlow` path needs `ANTHROPIC_API_KEY`
   (BUG-046) and is not being fixed here.
2. Network access at pipeline runtime is **best-effort, not guaranteed**. arXiv
   and several publishers already 403 datacentre fetches. A gate that cannot
   reach a source must report `UNRESOLVED`, never `verified`.
3. These gates run at **Stage 4**, on the finished article, against the research
   brief. They do not change Stage 3's prompting.
4. "Fail" means the article is quarantined for human review, not silently
   patched. We have enough evidence that silent auto-fixing hides defects.
5. Constraints #1–#3 hold: no keys, no paid services. Deterministic checks use
   `requests`; the one judgement-based gate (B-022) uses `query()` on the
   subscription.
→ Correct me if any of these is wrong.

## Objective

The first pipeline-generated article passed **every** deterministic gate while
carrying six factual errors and two fabricated citations. The gates measure
conformance; none measures correctness. These four gates close that gap.

Success: re-running the gates against
`data/review_corpus/2026-07-24-green-light-red-ledger/` flags the defects that
shipped. That corpus is the acceptance test.

## What we already have, and why it did not help

`scripts/citation_verifier.py` exists, has tests, and does roughly the right
thing — but it did not run and would not have caught this:

1. **It is wired only into the legacy path.** `verify_citations` is imported by
   `agents/research_agent.py` alone. The keyless pipeline
   (`pipeline.run_pipeline` → `run_stage3` → `run_stage4`) never calls it. The
   published article went through a path with *zero* citation verification.
2. **It verifies the wrong thing.** It checks whether a *statistic* appears in
   the source text. It never checks whether the *reference itself* is real —
   whether the title and authors we printed match the document at that URL.
   Both fabrications (BUG-058) were reference-metadata errors, invisible to it.
3. **It fails open.** On a fetch failure it does
   `logger.info(...); continue`, leaving `verified` untouched. Given that arXiv
   403s us, a wired-in version would have passed the fabricated references by
   default. **Fail-open verification is worse than no verification**, because it
   produces a green signal from an unperformed check.

So B-020 is not "build a verifier". It is: build the check that was missing,
wire it into the path that is actually used, and make unresolved distinguishable
from verified.

## Design

New module `scripts/source_integrity.py`. Pure-function core, injectable
`fetch_fn` (mirrors the existing `citation_verifier` convention so it mocks the
same way). Every check returns a `Finding` with an explicit verdict:

```python
Verdict = Literal["PASS", "FAIL", "UNRESOLVED"]
```

`UNRESOLVED` is a first-class outcome and is reported separately from `PASS` in
every summary. A run where every reference is `UNRESOLVED` must never read as a
clean run.

### B-020 · Reference integrity (BUG-058)

Parse the `## References` section of the finished article into structured
entries (index, authors, title, URL). For each entry:

- fetch the URL, extract the document's real title and author list
- compare against what the article printed
- `FAIL` on title mismatch or author mismatch; `UNRESOLVED` on fetch failure

Additionally, **cross-reference contamination** is checked without network: if
an author surname printed on reference *i* appears in the author list of
reference *j* and not in reference *i*'s own resolved metadata, flag it. That
is exactly the BUG-058 signature (`Parry` migrating from reference 5 to
reference 1) and it is detectable offline.

### B-021 · Claim provenance and units (BUG-059)

Two deterministic checks over the article body against the research brief:

- **Unit preservation.** For every currency/percentage figure in the article,
  find its counterpart in the brief and assert the unit matches. `0.02 cents`
  in the brief rendered as `$0.02` in the article is a `FAIL`. This is the
  100× error, and it is mechanically detectable.
- **Number scope.** A figure in the article must appear in the brief attached
  to the *same* subject. `45%` attached to "projects" in the brief and to
  "root causes" in the article is a `FAIL`.

The existing stat audit is not a substitute and must not be treated as one. It
asserts `stat ∈ research_brief`. It has never asserted that the brief entry is
correctly scoped or correctly united, so it passed the fabricated statistic
while working exactly as specified. **Spec defect, not implementation bug.**

### B-022 · Source stance (BUG-060)

For each citation, classify whether the source's own conclusion **supports**,
**contradicts**, or **does not bear on** the sentence citing it. Contradiction
is a `FAIL`.

Keyless via `query()` on the subscription (constraint #3). Injectable
`query_fn` so tests never hit the network. Depends on B-020: a resolved
citation is a precondition for reading its stance.

This is the one gate that cannot be deterministic — detecting that a paper
argues *against* the paragraph citing it requires reading the paper's
conclusion. It is also the finding the external review called most damaging.

### B-023 · Chart data provenance (BUG-061) and scaffolding leaks (BUG-062)

- Every chart series value must appear in the research brief. A series computed
  from another series must be explicitly declared derived. The published chart
  plotted "genuine defects" shares of 16% and 79%, both produced by subtracting
  the flaky share from 100; neither appears in any source.
- Strip the `<!-- HERO IMAGE` placeholder whenever `image:` resolves to a real
  asset (BUG-062), with a regression test asserting none survives finalisation.

## Commands

```
Test:   python -m pytest tests/test_source_integrity.py -q
Suite:  python -m pytest tests/ -q --ignore=tests/test_arxiv_search.py
Lint:   python -m ruff check .
Gate:   make ci-local
```

> Container note: `tests/test_arxiv_search.py` cannot be collected in a fresh
> container — `feedparser` needs `sgmllib3k`, whose wheel will not build on this
> Python. Unrelated to this work. Four pre-existing failures in
> `test_arxiv_query_optimize.py` and `test_topic_scout.py` also predate it,
> confirmed by stashing.

## Testing strategy

TDD, RED → GREEN → REFACTOR, one slice per commit. Mock all network via
`fetch_fn` / `query_fn` per repo standard. The review corpus provides the
regression fixtures: every check must flag the real defect that shipped.

## Boundaries

- **Always:** fail closed; report `UNRESOLVED` separately from `PASS`; mock
  network in tests.
- **Ask first:** making any gate CRITICAL enough to block the pipeline outright.
  Start as flag-and-quarantine.
- **Never:** add an API key or a paid service; silently auto-fix a factual
  defect; treat a fetch failure as a pass.
