# B-024 · Research failure must not silently produce an ungrounded article

**Status:** DRAFT — awaiting owner LGTM
**Defect:** BUG-067
**Discovered:** 2026-07-29, during the article-two regeneration run
**Id note:** numbered B-024 rather than B-023 because the owner uses "B-023" for
the `backup/integration-test-20260728` ref, which is not a backlog item.

## Objective

Decide and implement what the pipeline does when the `claude_web` research leg
fails. Today it degrades to a findings-free brief and writes the article anyway.
Success is that a failed research leg can never yield a *published* article, and
that its failure is legible at the point it happens rather than inferred from a
confusing downstream symptom.

## The current behaviour, and why it is deliberate

This is not an oversight — it is a documented design choice, which is why it
needs a decision rather than a patch. `build_claude_web_brief`
(`src/agent_sdk/research/claude_web.py`):

```python
except Exception as exc:  # noqa: BLE001 — soft-degrade, never crash Stage 3
    logger.warning("claude_web research failed (%s) — returning empty brief", exc)
```

and its docstring: *"On any SDK failure the brief still returns with its
guardrail header (an empty findings block) so the pipeline degrades softly
rather than crashing."*

`_format_brief` then returns the 401-char guardrail header with no findings, and
`run_stage3` (`stage3_runner.py:666-678`) logs the char count and goes straight
to the writer prompt. **No emptiness check exists on this path.**

The asymmetry is the real defect: the *deterministic* provider path raises
`EmptyResearchBriefError` (`tests/test_empty_research_guard.py` asserts
`run_stage3` propagates it), and `run_stage3` calls it at line 668 — one line
below the `claude_web` call at 666 that has no equivalent guard. Two research
paths, two opposite failure policies, one of them silent.

## Observed, not assumed

From the aborted run (`2026-07-29`):

```
WARNING claude_web: claude_web research failed (...) — returning empty brief
INFO   stage3_runner: Research brief: 665 chars
```

Stage 3 proceeded. The writer leg then failed for the unrelated BUG-066 reason,
which is the only thing that stopped this run producing an article.

Measured downstream behaviour against an empty brief (`audit_article_stats`):

| Input sentence | Outcome |
|---|---|
| "At Google, 84% of build failures…" | **stripped** |
| "Teams report a 21% drop…" | **stripped** |
| "The median pull request waits 4.3 hours…" | **survived** |

74 words → 47 (−36%). So the stat audit is a **leaky** guard, not an absent one:
most quantified claims go, but unsourced ones without a `%`-style marker survive.
The probable real-world outcome is a word-count quarantine after ~$1 is spent;
the tail risk is a published article carrying unsourced numbers.

## The decision required (this is the LGTM)

**Option A — Abort the run.** Raise `EmptyResearchBriefError` from the
`claude_web` path, matching the deterministic path exactly.
*For:* one failure policy across all research modes; impossible to publish
ungrounded work; the error already exists and is already tested.
*Against:* forfeits a partially-spent run (research is charged before the abort).

**Option B — Fall back to the keyless deterministic providers.** On
`claude_web` failure, call `build_research_brief` (arXiv + Semantic Scholar) and
continue with that brief.
*For:* keeps a ~$1 run alive; the providers are built, free, keyless, and already
the default for `--research-mode deterministic`; constraints #1–#3 hold.
*Against:* silently changes the sourcing character of the article (academic
rather than live web), which the owner may not want without being told; and if
the fallback *also* returns nothing, we still need Option A underneath it.

**Recommendation: B with A underneath.** Try the deterministic providers, and if
they also yield no sources, raise `EmptyResearchBriefError`. This preserves the
run in the common case (a transient SDK/CLI failure, which is exactly what
BUG-066 was) while making "no research at all" unconditionally fatal. The
fallback must be **logged loudly and recorded in the run metadata**, so a
downgraded article is never mistaken for a web-researched one.

## Success criteria

1. A `claude_web` failure with a working deterministic path produces an article
   whose brief contains real sources, and the run metadata records that a
   fallback occurred.
2. A `claude_web` failure with *no* usable sources from any provider raises
   `EmptyResearchBriefError` and produces **no** article file.
3. `run_stage3` never dispatches the writer with a findings-free brief, on any
   `--research-mode`.
4. The existing deterministic-path behaviour is unchanged
   (`tests/test_empty_research_guard.py` still green).
5. `make ci-local` green.

## Testing strategy

Prove-It, per `test-driven-development`. Each test fails against today's code:

- `test_claude_web_failure_falls_back_to_deterministic_providers` — patch the
  SDK to raise; assert the brief contains the arXiv/Semantic Scholar sources.
- `test_claude_web_failure_with_no_sources_anywhere_raises` — patch both to
  yield nothing; assert `EmptyResearchBriefError` and that no article is written.
- `test_writer_is_never_dispatched_with_a_findings_free_brief` — the invariant
  behind criterion 3, asserted directly at the `run_stage3` seam.
- Mocked SDK throughout; no test may reach a third party (BUG-058).

## Boundaries

- **Always:** keyless providers only (constraints #1–#3); log a downgrade at
  WARNING with the reason; keep the deterministic path's behaviour identical.
- **Ask first:** changing `EmptyResearchBriefError`'s type or its public
  contract — `tests/test_empty_research_guard.py` and `flow.py` both depend on it.
- **Never:** publish an article built on a findings-free brief; add an API key or
  a paid provider to keep a run alive.

## Open questions

1. **Should the fallback be automatic or opt-in?** Automatic keeps runs alive;
   opt-in (`--research-fallback`) keeps the sourcing character predictable.
   Recommendation: automatic, because the failure it covers is transient.
2. **Should a fallback article be publishable without review?** It is materially
   different from what was commissioned. Recommendation: publishable, but the
   downgrade must appear in the run report the reviewer reads.
