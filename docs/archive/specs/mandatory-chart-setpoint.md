# Spec — Art is the owner's; the pipeline hands off a review packet (B-042)

**Status:** DRAFT — awaiting LGTM · **Opened:** 2026-08-01 · **Rewritten:** 2026-08-01 after the
owner's decision that he owns *all* images, charts included
**Resolves:** B-042 · **Moots:** B-041 · **Amends:** Operating Constraint #4
**Related:** ADR-0016 (one pipeline path) · ADR-0017 (gate publishable content at deploy) ·
ADR-0018 · B-043 `docs/specs/sensor-proof-of-teeth.md` open question 3

## Objective

`publication_validator.py:1031` requires a chart in every article at **CRITICAL** severity. When
the research carries no chartable data the pipeline is therefore *required* to produce one anyway,
and on 2026-08-01 it did: a brief containing one number yielded a chart carrying four invented
percentages (62 / 46 / 28 / 12%), with an axis and a measured-sounding subtitle. The evaluator
scored the article 76 and the validator **passed** it. That was compliance, not a rogue writer.

**The owner's decision (2026-08-01) resolves this by removing the machine's authority over it
rather than by tuning a threshold.** He is responsible for every image the blog publishes — hero
and chart alike — because fully automated visual generation has not produced outcomes he will
stand behind. The pipeline's job ends at a **review packet**: the article, every gate result, and
everything he needs to make the art.

**B-042 is then resolved by construction. A pipeline that never generates chart data cannot
fabricate chart data.**

## What changed from this spec's first draft

The first draft designed an `audit_chart_data` function to catch invented chart numbers after the
fact. That machinery is **deleted from this spec**, not implemented. Auditing output for
fabrication is strictly worse than never asking a model to produce the numbers. The first draft's
frontmatter declaration (`chart: none`) also goes: with the owner authoring the art, **presence on
disk is the decision**, and no declaration needs writing, trusting, or binding.

What survives from the first draft is the measurement — five reinforcing sites, all verified —
and two findings that stand regardless of design.

## Two findings that stand on their own

### 1. `orphaned_chart` is dead code, and a test holds it dead

The backlog and `docs/HANDOFF.md` both say `orphaned_chart` fires unless prose "near the embed"
mentions the chart. It does not. `publication_validator.py:1045-1049` scans `content_lower` — the
**whole article** — for any of `chart`, `figure`, `graph`, `shows`, `illustrates`.

It is worse than loose. `missing_chart` **returns early** (`:1042`) unless a `/assets/charts/….png`
reference exists, so by the time `orphaned_chart` runs, the content provably contains the substring
**`chart`** — in the embed URL itself. **The check can never fire, for any input.**

`tests/test_publication_validator.py:411` is named `test_orphaned_chart_flagged`, asserts
`len(orphan_issues) == 0`, and documents the inertness as intended: *"charts in /assets/charts/
inherently contain the word 'chart' in the URL, so the orphan detection check … won't fire. This
test verifies that behaviour."*

A dead sensor with a passing test locking it dead — B-031's class exactly, found one day after
B-043 shipped a standing rule about it.

### 2. `orphaned_chart` did not push the writer. The writer prompt did.

`stage3_runner.py:314-317` instructs the writer: *"At least one paragraph in the body must
reference the chart explicitly — write something like 'as the chart shows' … **This is required by
the publication validator.**"* That is the direct cause of case `g2` ("As the chart below
illustrates, undetected defects do not flow linearly into rework"). The prompt names the sensor and
demands the sentence; the sensor would have passed without it.

## The five sites, all verified 2026-08-01

| # | Site | What it does | Fate |
|---|---|---|---|
| 1 | `stage3_runner.py:314-317` | Writer prompt **demands** a chart-referencing sentence | Deleted (S1) |
| 2 | `stage3_runner.py:868` | Graphics prompt gets the article, **never the brief** | Deleted (S1) |
| 3 | `stage3_runner.py:876` | Chart render unconditional, failure **fatal** | Deleted (S1) |
| 4 | `_shared.py:664`, called `:887` | `_auto_embed_chart` inserts an embed regardless | Moves to `make chart` (S3) |
| 5 | `publication_validator.py:1031` | `missing_chart`, **CRITICAL** | Deleted (S2) |

Note that fixing site 5 alone — the obvious reading of B-042 — would have left sites 1–4 still
generating a chart nothing required.

## Design

### S1 — Stage 3 stops producing art

Remove the hero draw (`hero_author`, B-016b) and the entire graphics stage: the LLM chart prompt
(`:859-868`), `_graphics_with_retry`, the graphics budget, and the writer instruction at
`:314-317`.

**Kept:** `compose_prompt` → `output/posts/<slug>.image_prompt.md`. It is already the hero brief
and ADR-0016 already treats it as such. Nothing new is invented for the hero.

### S2 — Two-phase validation, per ADR-0017

**Phase A — the pipeline.** `publication_validator` runs with art absent by design. `missing_chart`
is **deleted**; the hero/image checks report **PENDING** rather than CRITICAL. Every other gate
(frontmatter, word count, references, placeholders, endings, British spelling, citation verifier,
evaluator) is unchanged and must pass. The run exits 0 having produced everything a machine can
produce.

**Phase B — deploy.** `deploy_to_blog` enforces art presence before any clone. It already refuses a
missing chart asset (`test_missing_chart_asset_raises`) and the stray `<!-- HERO IMAGE` comment
(BUG-065), so the enforcement point exists and this extends it rather than inventing a gate.

This is ADR-0017's accepted principle: publishable-content requirements belong at the deploy
boundary, because that is where "publishable" becomes true.

**`missing_chart` is deleted rather than made conditional.** Whether an article warrants a chart is
an editorial judgment made against the research, and the machine has neither the research at
validation time nor the standing to make it. That is B-042's real answer: the setpoint was not
mistuned, it was *held by the wrong party*.

### S3 — Chart: proposed deterministically, authored by the owner, rendered by the repo

`propose_chart_spec(research_brief) -> dict | None` in `_shared.py`. **No LLM.** It reuses
`_extract_stats` (`_shared.py:132`), which already returns every number in the brief with ±60
characters of surrounding context, and emits one candidate row per number, carrying its provenance:

```json
{ "title": "", "subtitle": "",
  "data": [ { "metric": "", "value": 40, "unit": "%",
              "source": "brief: 'up to 40% of engineering capacity'" } ] }
```

Written to `output/charts/<slug>.spec.json`. Returns `None` — and the packet says so plainly —
when the brief contains no numbers.

**Every value in a proposed spec appears in the brief by construction**, because extraction is the
only way values get in. There is nothing to audit. Titles and metric labels are left **empty**: they
are framing, framing is judgment, and a plausible machine-written label is exactly the artefact that
made case `g4` unreadable as fiction.

The owner edits the spec and runs `make chart SLUG=<slug>`, which renders it through
`chart_renderer.py` (matplotlib, keyless, Constraint #4's sanctioned path) **and inserts the embed
into the article**. A hand-made PNG dropped at `output/charts/<slug>.png` takes precedence and skips
rendering, so the fully-manual route stays open at no extra cost.

### S4 — The review packet

`output/posts/<slug>.review.md`, written at the end of every run. One file, everything needed:

1. **Verdict** — every gate, sensor and eval with its result; the evaluator score; anything PENDING.
2. **The permanent slug**, flagged as unchangeable after publish (no redirects on the blog).
3. **Hero** — the drawing brief inlined from `.image_prompt.md`, plus the target path
   `output/posts/images/<slug>-hero.svg`. **A `.png` hero needs a `.webp` sibling**; `.svg` does not
   — the blog's `responsive-image.html` rewrites `.png` → `.webp`.
4. **Chart** — either the proposed spec with each number's brief provenance, or *"no numbers found
   in the research brief — no chart proposed"*, stating what was searched.
5. **The exact next commands**, in order.

### S5 — Notification

Terminal summary at end of run, plus a macOS banner via `osascript`. Degrades **silently** when
`osascript` is absent (headless, non-macOS) and is **never fatal** — a notification failure must not
fail a run that succeeded. Keyless, local, no outward send.

### S6 — Delete `orphaned_chart`

Not repair it. A *working* `orphaned_chart` detects an embed the prose never engages with, and its
only available remedy is *add a sentence about the chart* — the precise pressure that wrote case
`g2`. Repair would make this defect worse. It has never fired, so nothing regresses.

What it reached for — *is the description of the chart true?* — is case `g2`, which is inferential.
ADR-0018 decided judgment is advisory here, so it belongs to B-040's arm, not a deterministic gate.
`tests/test_publication_validator.py:411` goes with it: a test asserting a sensor stays inert is not
coverage.

### S7 — Amend Operating Constraint #4

Constraint #4 was amended 2026-07-25 (B-016) to have Claude draw the hero as SVG. **This reverses
that**: Claude draws neither hero nor chart; the owner authors both, and the repo renders only a
chart spec he has signed off. CLAUDE.md requires new constraints be encoded immediately, so this
edit is part of the work. The reason is recorded with it — automated visual generation has not
produced outcomes the owner will stand behind, and B-042 is the measured instance.

## What gets deleted

Listed explicitly so the change is a removal, not an accumulation:

`hero_author` · the graphics stage (`_graphics_with_retry`, prompt, budget, `_GRAPHICS_MAX_ATTEMPTS`)
· the writer's chart-sentence instruction · `missing_chart` · `orphaned_chart` and its test ·
`_auto_embed_chart`'s unconditional path.

**B-041 is mooted**: the hero-draw timeout item exists only because Stage 3 draws heroes. The two
600s timeouts blocking the current article stop happening. Close it with a pointer here.

## Acceptance criteria

- [ ] **AC1** — A brief with no numbers yields **no chart proposal**, an article with **no chart**,
      and a **passing** Phase A validation. The backlog's stated regression case.
- [ ] **AC2** — `docs/evals/review-gate/cases/g4-fabricated-chart-figures.yaml`: no code path can
      produce those four values, because no code path generates chart values. Asserted as *the
      graphics stage does not exist* — a structural test, not a filter test.
- [ ] **AC3** — Every value in a proposed spec appears in the brief. Property-style over the
      fixtures in `tests/fixtures/html_briefs/`.
- [ ] **AC4** — A brief **with** real numbers produces a proposal with provenance on every row and
      **empty** title/labels.
- [ ] **AC5** — Deploy **refuses** an article whose hero is missing, and refuses a chart embed whose
      PNG is absent. Both directions, both `deploy()` and `deploy_review()`.
- [ ] **AC6** — `make chart SLUG=…` renders the spec and inserts the embed; a pre-existing hand-made
      PNG is used as-is and not overwritten.
- [ ] **AC7** — The packet is written on every run, including one with PENDING art, and names every
      gate.
- [ ] **AC8** — A notification failure does not fail the run (`osascript` absent → run still exits 0).
- [ ] **AC9** — `make ci-local` green, including `check_sensor_proofs.py`.

## Proof of teeth (B-043 obligation)

B-043's standing check applies. Two register entries in `docs/sensors/register.yaml` change:

- **`publication_validator` (`:216-231`)** — its `regulates` text and the B-042 note, which
  currently records this defect as open.
- **`unreviewed_publish_guard` (`:233`)** — gains the art-presence gate; needs a proof that
  deleting the hero makes deploy refuse (AC5 is that proof).

AC2 and AC5 are mutation proofs by construction. AC5 is the one that matters: Phase A no longer
blocks on art, so if Phase B does not refuse, nothing does.

## Non-goals

- **No LLM chart-truth checker.** ADR-0018 decided advisory-first; `g2` stays B-040's arm.
- **No resurrection of `--resume`, `--image-mode`, or exit codes 10/11.** ADR-0016 deleted a
  *mid-pipeline pause*; this adds a hand-off *after* a complete run. One path, still exits 0.
- **No republishing of already-shipped articles.** One carries a manufactured chart; it is
  unpublished and blocked on the owner for other reasons.
- **No new keys or services.** Extraction is regex, rendering is matplotlib, notification is
  `osascript`.

## The ADR — beside this spec, in the same PR

B-043's open question 3 leaves a taxonomy gap: *a sensor with a wrong setpoint is neither inert nor
inaccurate — it works, and the system is worse for it.* Boeckeler's framework does not name it.

**Recommendation: ADR-0019, in this PR.** B-042 now sharpens the claim rather than merely
illustrating it: `missing_chart`'s setpoint was not mistuned but **held by the wrong party**, and
the fix was to remove the sensor's authority, not to adjust its threshold. That is a reusable
finding — *before tuning a setpoint, ask whether the decision is the machine's to make* — and it is
the generalisable output of this work. Written after the fix, it would be a changelog.

## Files

| File | Change |
|---|---|
| `src/agent_sdk/stage3_runner.py` | Delete `:314-317`, the graphics stage, the hero draw |
| `src/agent_sdk/_shared.py` | `propose_chart_spec` (new); `_auto_embed_chart:664` moves to `make chart` |
| `src/agent_sdk/pipeline.py` | Write the packet; notify; PENDING art |
| `scripts/publication_validator.py` | Delete `missing_chart:1031` and `orphaned_chart:1044-1062` |
| `scripts/deploy_to_blog.py` | Art-presence gate (Phase B) |
| `tests/test_publication_validator.py` | Delete `test_orphaned_chart_flagged:411` |
| `Makefile` | `make chart SLUG=…` |
| `CLAUDE.md` | Amend Constraint #4 (S7) |
| `docs/sensors/register.yaml` | Two entries (above) |
| `docs/adr/0019-*.md` | New |
| `BACKLOG.md` | B-042 closed; **B-041 closed as mooted** |

**Scope:** M–L. Larger than the first draft in files touched, smaller in machinery retained — it
deletes a stage rather than adding an audit.
