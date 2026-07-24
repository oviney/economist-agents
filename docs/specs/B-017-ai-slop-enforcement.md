# Spec: B-017 · Catch AI-slop tells that pass every deterministic gate (BUG-054)

> **Status:** DRAFT — awaiting owner LGTM before any code.
> **Skill lifecycle:** `spec-driven-development` → (on LGTM) `planning-and-task-breakdown` → `test-driven-development` + `incremental-implementation`.

## Objective

The generated flaky-tests article passed **every** current economist-writing gate
(named companies, ≤4 headings, colon-twist title, no lists in prose) yet still
read like AI slop. Close the gap: **detect** the structural tells that survive
today and **surface them to the human reviewer** — without silently rewriting
prose. Success = a regression fixture built from the real BUG-054 article trips
the new checks, and a clean human-written control article does not.

Who it serves: the owner, reviewing a rendered draft (B-013) or a PR, who today
gets a green Stage-4 report on prose that is not publishable.

## The core design decision (read before the tasks)

The five cited tells split cleanly by **how they can be caught**, and that split
drives the whole design:

| # | Tell (BUG-054) | Deterministically countable? | Mechanism |
|---|---|---|---|
| 1 | Em-dash rhythm (1–2 `—` per paragraph as default connective) | **Yes** — density metric | flag |
| 2 | `not X but Y` antithesis scaffold, repeated | **Yes** — regex count | flag |
| 3 | Meta-commentary on its own argument ("The argument here is…", "…make this case almost without assistance") | **Yes** — phrase set | flag |
| 4 | Unfalsifiable superlatives ("No other category…") | **Yes** — pattern set | flag |
| 5 | Purple / mixed metaphor (dripping-tap→flooding-basement→plumber) | **No** — semantic | out of deterministic scope |

Two non-negotiable principles fall out of this:

1. **Flag, never silently rewrite.** Today `apply_editorial_fixes` catches slop by
   *deleting* fixed dead phrases inline (`game-changer` → ""). That is safe for
   dead words. It is **unsafe** for tells 1–4: deleting one arm of a `not X but Y`,
   or excising a meta-commentary clause mid-paragraph, produces broken prose —
   *worse* slop. So these checks **report** (like `_check_weak_endings`), they do
   not mutate. Rewriting stays human-in-the-loop, consistent with the hero-image
   rule (constraint #4).
2. **The deterministic slice covers 4 of 5 tells. Tell #5 is honestly out of
   reach for regex** and is *not* faked. It is either accepted as the human
   reviewer's job (recommended) or handled by a **parked, opt-in** keyless Claude
   judge (see Not Doing) — never bolted into the default path.

### Where the checks live — and why not the obvious alternatives

**Chosen: new detector methods on `scripts/publication_validator.py`.** It already
runs inside Stage 4, already has a severity model, and its issues already surface
in `Stage4Result.publication_validator_issues` — the reviewer sees them with zero
new plumbing. New checks mirror the existing `_check_weak_endings` exactly.

Rejected alternatives:
- **`apply_editorial_fixes` (_shared.py)** — it *mutates*. Wrong tool per principle 1.
- **`editorial_judge.py`** — keyless and deterministic, but a *post-deploy*
  GitHub-fetch gate. We want to catch slop **before** it ships, not after.
- **An LLM judge pass in the default flow** — the CrewAI Stage-4 LLM reviewer was
  deliberately removed (50% JSON-parse failure, no value; see `stage4_runner.py`
  docstring). Do not reintroduce that risk into the default path.

### Severity: flag, don't quarantine (MVP)

New checks emit **HIGH** (tell present, egregious count) or **MEDIUM** (present,
low count) — **never CRITICAL**. Rationale: `validate()` only fails on CRITICAL,
and a borderline em-dash count should *inform* the reviewer, not hard-block an
otherwise-publishable draft. The owner can promote any single check to CRITICAL
later once thresholds are trusted on real articles. **Surface, then tighten.**

## Detection rules (thresholds are the review surface — tune on real data)

All checks run on the **article body** (frontmatter and the `## References`
section excluded, reusing `_check_weak_endings`'s body-extraction), and **skip
fenced code blocks** (` ``` `) so code em-dashes/operators never trip them.

1. **Em-dash density** — count `—` (U+2014) in the body. Flag HIGH if
   `count / paragraphs > 0.8` (≈ roughly one per paragraph or more); MEDIUM if
   `> 0.5`. Report the ratio and top offending paragraphs.
2. **`not X but Y` antithesis** — count matches of
   `\bnot\s+(?:merely|simply|just|only\s+)?[\w-]+(?:[^.]{0,40}?)\bbut\b`
   (case-insensitive). Flag HIGH if ≥ 4, MEDIUM if ≥ 2. False positives are
   acceptable *because it only flags* — the human adjudicates.
3. **Meta-commentary** — a curated phrase set the writer uses to narrate its own
   argument: e.g. `the argument here`, `makes? (?:this|the) case`, `the numbers,?
   once examined`, `as this (?:article|piece) (?:argues|shows)`, `what follows`,
   `it is worth restating`, `almost without assistance`. Any hit → HIGH (this tell
   is never desirable). Report each phrase + context.
4. **Unfalsifiable superlatives** — pattern set anchored on absolute claims: e.g.
   `\bno other\b`, `\b(?:the )?most \w+ (?:category|form|kind|type)\b`,
   `\bnever before\b`, `\bunlike any\b`, `\bnothing (?:else )?(?:comes close|
   compares)\b`. Flag MEDIUM per hit, HIGH if ≥ 2. Report phrase + context.

Each violation reports `{check, severity, message, details, fix}` exactly like the
existing checks; `fix` names the tell and says "rewrite by hand" (never an
auto-substitution).

## Tests (TDD — RED first)

Framework: pytest, `tests/test_publication_validator_ai_slop.py` (new).

- **Prove-It regression:** a fixture assembled from the real BUG-054 tells (the
  cited em-dash-dense, `not X but Y`, meta-commentary, superlative sentences)
  MUST raise HIGH-severity issues on each of checks 1–4 → RED on current code.
- **Clean control:** a short human-written Economist-style passage (moderate
  em-dash use, no antithesis pile-up, no meta-commentary) MUST produce **zero**
  new issues → guards against false-positive over-flagging.
- **Boundary:** one passage each sitting just under / just over each threshold.
- **Non-mutation invariant:** `validate()` returns the article text unchanged
  (validator never rewrites) — assert body bytes are untouched.
- **Code-block immunity:** em-dashes / `not…but` inside a ` ``` ` block do not trip.
- **Non-blocking invariant:** an article whose *only* issues are the new
  HIGH/MEDIUM slop flags still returns `is_valid == True` (no CRITICAL) — the
  flags inform, they don't quarantine.

Verify: `make ci-local` green (ruff, mypy, tests, coverage ≥ 70 / `src/quality`
≥ 90, bandit, destructive guard).

## Project structure touched

```
scripts/publication_validator.py                    # + 4 _check_* methods, wired into validate()
tests/test_publication_validator_ai_slop.py         # NEW — regression + control + boundary
docs/specs/B-017-ai-slop-enforcement.md             # this spec
BACKLOG.md                                           # B-017 → In Progress → Done
data/skills_state/defect_tracker.json               # BUG-054 → resolved on land
```

No changes to `_shared.py`'s mutation path, `stage4_runner.py`, or the default
generation flow beyond the validator gaining checks it already knew how to run.

## Boundaries

- **Always:** flag-only (no prose mutation); body-only, code-block-safe; every
  threshold justified by the BUG-054 fixture; keyless; `make ci-local` before land.
- **Ask first:** promoting any check to CRITICAL (changes publish gating);
  building the opt-in metaphor judge (separate spec).
- **Never:** silently auto-rewrite prose; add an LLM pass to the default flow;
  add any key/paid service (constraints #1–#3); touch the hero-image rule (#4).

## Success Criteria

- [ ] The BUG-054 regression fixture trips checks 1–4 at HIGH; the clean control trips none.
- [ ] Checks report (never mutate) and never emit CRITICAL in the MVP.
- [ ] `Stage4Result.publication_validator_issues` shows the new flags on a slop draft.
- [ ] `make ci-local` green; coverage bar held.
- [ ] BACKLOG B-017 + BUG-054 closed; tell #5 explicitly parked, not silently dropped.

## Not Doing (and why)

- **Purple/mixed-metaphor detection (tell #5)** — semantic, not regex-detectable;
  faking it with a keyword list would false-positive on every real metaphor.
  Handled by human review in the MVP.
- **Opt-in keyless Claude economist-writing judge** — a Claude/Agent-SDK pass that
  *flags* (not rewrites) semantic tells including metaphors, kept **out of the
  default path** and off by default, mirroring B-012's opt-in-heavy design. Parked
  as a follow-on idea; specced separately only if flagging proves insufficient.
- **Auto-rewriting any tell** — out of scope by principle 1; rewriting is the
  human's job at review.

## Open Questions

1. Thresholds (em-dash 0.8/0.5; antithesis 4/2) are first guesses to tune against
   the BUG-054 article + one clean control. OK to land with these and adjust, or
   hold for a second real sample?
2. Keep every new check non-blocking (HIGH max) for the MVP — agreed? Or should
   meta-commentary (never desirable) block as CRITICAL from day one?
