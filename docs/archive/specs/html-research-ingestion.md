# Spec — HTML research ingestion (B-038)

**Status:** DRAFT — awaiting owner LGTM · **Opened:** 2026-07-31

## Objective

The owner researches by holding a back-and-forth conversation with Claude and finalising it
as an **HTML artifact**. That artifact is whatever the conversation converged on — a report,
an analysis, a comparison, an argument — not a fixed research-brief shape.

The pipeline cannot consume it. `python -m src.agent_sdk.pipeline` takes a topic string plus
an optional `--brief PATH`, and `load_brief_file` (`pipeline.py:90`) expects **markdown** at
`docs/research/<slug>.md`. The only route today is manual transcription, which is why this
recurs.

Build `scripts/html_to_brief.py`: **Claude HTML artifact → a markdown brief the existing
writer path already consumes.** No change to the pipeline.

```bash
python scripts/html_to_brief.py ~/Downloads/conversation.html --slug ai-code-review
# writes docs/research/ai-code-review.md
IS_SANDBOX=1 python -m src.agent_sdk.pipeline "<topic>" --brief docs/research/ai-code-review.md
```

## What the contract actually requires — this decides the whole design

Measured, not assumed. `--brief` is loaded by `load_brief_file`, which does exactly two
things: read the file, and strip `## Refuted…` sections. The result is handed to
`run_stage3(brief_override=…)`, and `stage3_runner.py:249` **returns it verbatim** as the
research text the writer works from.

So there are only two hard requirements:

1. **It is markdown text.**
2. **`## Refuted` is honoured** — that section is removed before the writer sees it.

There is no schema. No "Verified claims" parser, no required headings. The
`ai-productivity-brief.md` layout is a *convention the deep-research harness happens to
emit*, not an interface.

**That changes the build from claim-extraction to faithful conversion**, which is the right
answer for arbitrary chat artifacts. A claim-extractor would need to guess the shape of every
conversation you ever finalise, and would silently drop whatever it failed to recognise. A
faithful converter cannot have that failure mode.

## Design: faithful HTML → markdown, no LLM in the middle

**Recommendation: deterministic conversion with BeautifulSoup (4.13.5, already installed —
no new dependency, no key, so Operating Constraints #1–#3 are untouched). Do not put a
summarisation or restructuring model between your research and the writer.**

The reason is not cost. It is that **ADR-0018 just measured what this failure mode is worth.**

That ADR's finding was that the expensive defect class is *fidelity*: a statistic quoted with
its offsetting clause deleted, a baseline described as measuring something it does not, a
conclusion imported into a paper that does not report it. Those survived four gates and cost
a BLOCK at 51/100 on an article the deterministic evaluator passed at 88%.

An LLM paraphrase step sits exactly where that damage originates — between what your research
concluded and what the writer believes it concluded. **The brief's job is transport, not
judgment.** You already did the judging, in the conversation. Deciding emphasis is the
writer's job; checking fidelity is `blog-post-review`'s. A paraphrase in the middle would
manufacture the precise defect class we just built a gate to catch.

So: convert structure to structure, preserve prose, quotes, tables and URLs verbatim, and let
you edit the brief before use.

### Mapping

| HTML | Markdown | Note |
|---|---|---|
| `h1`–`h6` | `#`–`######`, demoted so the brief's own `#` title stays top-level | headings drive the writer's sense of structure |
| `p` | paragraph | |
| `ul` / `ol` | `-` / `1.` | nesting preserved |
| `blockquote` | `> …` | **verbatim** — these are usually the load-bearing quotes |
| `table` | GFM table | the sample artifact has 2; dropping them would lose comparisons |
| `a href` | `[text](url)` | **URL verbatim** — ADR-0018 G5 and `citation_verifier` depend on real URLs |
| `code` / `pre` | inline / fenced | |
| `script`, `style`, `nav`, `footer` | dropped | Claude artifacts carry styling and chrome that is not content |

### The `## Refuted` convention is the highest-value feature

`load_brief_file` strips it. So content routed there is **excluded by construction** rather
than by the writer's discretion.

v1 does **not** try to infer what is hedged — inference is judgment, and this tool does
transport. Instead it always appends an empty, clearly-labelled `## Refuted / unverified`
section, so moving a paragraph into it is a one-line edit with a guaranteed effect. That is
a better tool than a classifier that is right 80% of the time and silently wrong the rest.

## Boundaries

- **Always:** preserve quotes, tables and URLs verbatim; emit valid markdown; emit the
  `## Refuted` section even when empty, so the mechanism is visible and one edit away.
- **Ask first:** any new dependency (none expected); any network access — resolving a
  citation URL would need a constraint check.
- **Never:** call an LLM to paraphrase; invent content not in the input; **silently drop
  anything** — unrecognised elements are converted as plain text rather than discarded.

## Testing strategy

TDD per `agent-skills:test-driven-development`. `tests/test_html_to_brief.py`, deterministic,
no network:

- Three fixture shapes (headings+prose, blockquote-heavy, table-bearing) proving template
  independence — the artifacts vary because the conversations vary
- Quotes, tables and URLs survive byte-identical
- `script`/`style` chrome is dropped; content is not
- **End-to-end:** output passes through the real `load_brief_file` and the Refuted section is
  stripped — asserted against the loader itself, never a mirrored regex
- Nothing is silently dropped: total text content of input ⊆ output
- Malformed/empty HTML exits non-zero with a clear message rather than emitting a hollow brief

## Success criteria

- [ ] `python scripts/html_to_brief.py <file> --slug <slug>` writes `docs/research/<slug>.md`
- [ ] Output round-trips through `load_brief_file` with Refuted stripped
- [ ] Run on a real artifact from one of your conversations, the brief is usable **without
      re-typing any content** (reordering and deletion are fine; transcription is not)
- [ ] `make ci-local` green; ≥80% coverage on the new module
- [ ] No new dependency, no key, no network

## Not in scope for v1

- Multi-file merge
- Fetching or verifying cited URLs — that is `citation_verifier` / ADR-0018 G5
- Inferring which claims are hedged (see above — deliberate)
- Deriving the topic string; the pipeline still takes it as an argument

## Fixtures — and the one thing only the owner can supply

**Drop point: `docs/research/samples/*.html`** (created, with a README explaining what and
why). Any HTML artifact from a finalised research conversation.

The build is **not blocked** on it. v1 ships three synthetic fixtures —
headings-and-prose, blockquote-heavy, table-bearing — chosen to prove template independence,
and they are enough to develop against.

But a synthetic fixture only proves the converter handles *HTML I imagined*. The evidence
that this matters is already in the repo: the one real Claude artifact here,
`docs/reviews/review-queue-throughput-tax-42d2fbb4.html`, contains **zero `<a href>`**. A
design that assumed "sources arrive as links" would have been wrong on the only real evidence
available, and would have looked fine against invented fixtures. That is the third instance of
the pattern recorded in `skills/defect-prevention/SKILL.md` — asserting from a plausible
reading instead of measuring.

**Resolution rule, so this never stalls the work:** if `docs/research/samples/` contains an
`*.html` file, make it the primary fixture and treat the synthetic three as supplements. If
it is empty, build and ship on the synthetic three, and record in `docs/HANDOFF.md` that the
tool has **not yet been proven against a real artifact** — as an open item, not a silent gap.
Do not pause to ask.
