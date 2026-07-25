# Spec: B-019 — Align generated front matter with the blog's post contract

**Status:** Draft, awaiting owner LGTM
**Backlog:** B-019 (top of Todo)
**Measured contract:** `docs/blog-integration-constraints.md` → "The post front-matter contract"
**Blocks:** every future article. The next `make publish` fails `validate-editorial` without this.

## Objective

Make a generated article pass `oviney/blog`'s `validate-editorial` job **on the
first deploy**, without hand-editing. Publishing the first real article failed that
job four times, each on a rule our own `publication_validator` does not have. Every
fix so far was applied to the live post by hand; only `tags` (BUG-057) was fixed in
the generator.

**Success = a freshly generated article passes the blog's own scripts unedited:**

```bash
bash scripts/validate-posts.sh                # exit 0
bash scripts/validate-post-quality.sh --all   # exit 0 or 2 (2 = warnings only = pass)
```

Non-goal: making our validator a mirror of the blog's. We fix the *generator*; the
blog's scripts stay the acceptance oracle, run for real, never read-and-inferred.

## Assumptions (correct these before I build)

1. **Slug quality is worth one prompt line.** URLs are permanent (no
   `jekyll-redirect-from`, `_config.yml` is protected). A purely mechanical slug is
   safe but reads worse than one the writer chooses. I assume we want the writer to
   propose a slug, with a deterministic derivation as the guarantee — not
   deterministic-only.
2. **A duplicated subtitle is an acceptable fallback.** If the writer omits
   `subtitle`, Stage 4 backfills from `description`. On the page that reads as mild
   duplication. I assume "gate passes with slightly redundant prose" beats "deploy
   fails".
3. **`image_caption` stays a warning.** The blog's ≤40-char rule is a WARNING, and
   truncating a caption at 40 chars mid-clause makes it worse. I assume we fix this
   in the prompt and accept the warning when the model overshoots.
4. **Category values outside the blog's four are dropped, not mapped.** Inventing a
   mapping for an unknown category ("DevOps" → ?) is a guess; dropping it and
   falling back to `["Quality Engineering"]` is predictable.

## The five gaps

Measured against the blog's two scripts. Severity is the blog's, not ours.

| # | Gap | Blog rule | Today |
|---|---|---|---|
| 1 | `subtitle` never emitted | **ERROR** — required, ≤60 words hard | absent |
| 2 | Category items unquoted | **ERROR** — parser splits on `", "`, so `[A, B]` reads as one invalid category | `_normalize_category_casing` preserves whatever the writer emitted |
| 3 | Slug too long | **ERROR** — filename slug >60 chars; policy targets ≤50, complete words | derived from the full title (flaky-tests was **76**) |
| 4 | `image_caption` >40 chars | WARNING | prompt asks for "one punchy editorial sentence" |
| 5 | `image:` placeholder | **ERROR** — must resolve to a real file | prompt asks for a literal `/assets/images/SLUG.png`; `.png` also needs a `.webp` sibling |

## Design

### The single seam: `canonical_slug()`

`src/agent_sdk/_shared.py:461` is called from exactly three places, all deriving
from the article title:

- `_auto_embed_chart` (`_shared.py:486`) → the in-body chart embed
- `_slug_for_chart` (`stage3_runner.py:249`) → the chart PNG + `.image_prompt.md` sidecar
- `_slug_from_article` (`pipeline.py:515`) → the article filename

**Because there is one derivation, shortening inside `canonical_slug` keeps the
B-008 invariant by construction.** All four consumers move together; no consumer
learns about length. This is the whole reason the B-008 refactor was worth doing,
and it is why this is a contained change rather than the risky one the backlog
feared.

New signature stays `canonical_slug(article, fallback) -> str`. New behaviour:

1. **Honour an explicit `slug:` front-matter field** when present and valid
   (`^[a-z0-9]+(-[a-z0-9]+)*$`, ≤60 chars). `publication_validator` *already*
   treats `slug:` as canonical. Jekyll's `:title` permalink token is documented as
   overridable by `slug:`, which slice 1 verifies with a local blog build rather
   than trusting — **but the design is robust either way**: because the filename is
   written *from* the same value, field, filename, and URL agree whichever one
   Jekyll actually uses. The blog's gate measures the filename regardless.
2. **Otherwise derive from the title**, deterministically:
   - strip possessives (`Engineering's` → `Engineering`) — today `'` becomes `-`,
     which produced the `-s-` in the 76-char slug
   - lowercase, non-alphanumeric → `-`, collapse `--`, strip edges
   - drop a small closed stop-word list (`the a an and or of to in on for is are
     was were be that this with as at by from it its but not`)
   - if still >50, drop **trailing whole words** until ≤50 — never cut mid-word
   - empty → `"article"`

Worked example, the article we just published:

```
title:  Green Light, Red Ledger: Flaky Tests Are Engineering's Costliest Invisible Tax
today:  green-light-red-ledger-flaky-tests-are-engineering-s-costliest-invisible-tax   (76 → ERROR)
after:  green-light-red-ledger-flaky-tests-engineering                                 (46 → clean, no warning)
```

Invariants the tests must pin:

- output is always ≤50 chars (so the blog's ≥55 soft warning never fires either)
- output is always a prefix-compatible, complete-word phrase — never ends mid-word
- output never contains `--`
- the same article yields the same slug from all three call sites

### Stage 4 front-matter emitter (`apply_editorial_fixes`)

Extends the existing "deterministic front-matter guarantee" block
(`_shared.py:651-677`), same belt-and-braces shape already used for `tags`:

- **`subtitle`** — if absent, backfill from `description` (or the derived
  description), truncated at a word boundary to ≤40 words.
- **`categories`** — rewrite the line to canonical form:
  `categories: ["Quality Engineering", "Test Automation"]`. Parse items, map through
  `_CATEGORY_NORMALIZATION`, **drop anything not one of the blog's four**, default to
  `["Quality Engineering"]` when nothing survives. Replaces the substring-substitution
  approach, which cannot add quotes.
- **`image:`** — strip the line when its value does not resolve to a real file
  (covers the literal `SLUG.png` placeholder). Consistent with BUG-055: absent is
  safe, broken is not. *Setting* it correctly is B-016b's job, when the hero exists.
- Ordering: `subtitle` after `categories`, so the categories fallback is already
  in place; `image:` strip stays where it is.

### Writer prompt (`_build_writer_prompt`, `stage3_runner.py:163`)

Four edits, all in the front-matter sentence:

- add `subtitle` — one line, ≤40 words, distinct from `description` (not a restatement)
- add `slug` — 4–6 words, lowercase-hyphen, ≤50 chars, the keywords a reader would search
- `image_caption` — "≤40 characters" replaces "one punchy editorial sentence"
- drop `image (/assets/images/SLUG.png)` from the required list — the writer cannot
  know the slug, and a literal placeholder is worse than an absent key

## Slices

Each slice is RED → GREEN → commit, per `test-driven-development`.

| # | Slice | Verify |
|---|---|---|
| 1 | `canonical_slug` shortening | Prove-It: the real 76-char title asserts ≤50 + complete-word (RED today). Plus all three call sites agree. |
| 2 | Quoted + validated `categories` | unquoted writer input → quoted canonical; off-list dropped; empty → default |
| 3 | `subtitle` backfill + prompt line | absent → derived ≤40 words; present → untouched |
| 4 | `image:` placeholder strip | unresolvable value → key absent; resolvable → untouched |
| 5 | Acceptance | generate an article, run **the blog's own two scripts** in a clone; `make ci-local` green |

Slice 5 is the only one that proves the objective. Slices 1–4 are necessary, not
sufficient — that is the lesson of the four consecutive gate failures.

## Boundaries

- **Always:** derive every slug through `canonical_slug`; verify against the blog's
  scripts by running them.
- **Ask first:** anything that would rename an already-published post (permanent
  404), or touch a blog-side protected file.
- **Never:** a second slug derivation; mid-word truncation; stamping an empty or
  unresolvable `image:`; adding a key or paid service (constraints #1–#3).

## Open question

**One** — everything else is decided above. Slice 1 makes the writer's `slug:` the
preferred source. If you would rather the pipeline stay fully deterministic here (no
LLM input to a permanent URL), say so and I drop the prompt line and the honour-field
branch; the derivation alone still satisfies the gate, at some cost in readability
(`…-flaky-tests-engineering` rather than `…-flaky-tests-invisible-tax`).
