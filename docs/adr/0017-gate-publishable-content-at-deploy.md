# ADR-0017: Gate publishable-content invariants at the deploy boundary

**Status:** Accepted
**Date:** 2026-07-28
**Decision Maker:** Ouray Viney (owner)
**Supersedes:**
**Superseded by:**

## Context

BUG-065 was a production escape. The block below shipped into the published
flaky-tests article and sat in the live page source until 2026-07-29:

```
<!-- HERO IMAGE — generate an image from the prompt below, then replace this
whole comment with it (see output/posts/<slug>.image_prompt.md): … -->
```

It is invisible in the render, so nothing looked wrong. But it is pipeline
instructions on a public page, and it was stale the day it published — the hero
SVG had existed since B-016a.

The interesting part is *why no gate caught it*, because the project already has
a gate built for exactly this class of problem. `publication_validator` has a
`_check_placeholders` check whose docstring reads "placeholder text that should
never be published". It missed for two compounding reasons:

1. **The validator cannot see the comment, even in principle.**
   `_maybe_inject_hero_prompt` runs *after* `run_stage4` — deliberately, with the
   comment "Injected AFTER Stage 4 so validation is unchanged". Injecting before
   would change word counts and heading detection, so the ordering is correct.
   The consequence is that the artefact the validator blesses is not the artefact
   that ships.
2. **Even if it could see it, the pattern would not match.**
   `_check_placeholders` matches `TODO|FIXME|XXX|REPLACE_ME|YOUR_*`. A
   plain-English "replace this whole comment with it" is not placeholder text by
   that definition.

So the pipeline injects unpublishable content *after* the last gate that could
reject it. That is a structural gap, not a missing regex — and it generalises:
any post-validation transform has the same shape.

This also has to be read against the project's hardest-won lesson (B-015, B-019):
**a green local gate says nothing about what the blog accepts.** Four consecutive
defects passed `make ci-local` and were rejected by the blog. BUG-065 is the
inverse and worse — it passed every gate *and* the blog, and still should not
have shipped.

## Decision

**We will enforce publishable-content invariants at the deploy boundary — the
last point before anything becomes public — rather than in the publication
validator.**

Concretely, `scripts/deploy_to_blog.py` gains `_reject_unrendered_hero_prompt`,
which refuses any article still carrying the `<!-- HERO IMAGE` marker. It guards
**both** entry points, `deploy()` and `deploy_review()` — a review deploy is an
unlisted but live URL, so it carries the same exposure — and it runs before any
clone or push, so a rejected article costs nothing and the error is about the
article rather than about git.

The guard **rejects rather than strips.** The comment is only ever present
because no hero was drawn; silently deleting it would hide that fact, and the
blog requires a resolvable `image:` anyway (B-019), so a stripped article would
fail downstream with a less informative error.

We will **not** add a matching pattern to `_check_placeholders`. That check runs
before the comment exists, so the pattern could never fire in the normal flow —
it would be dead code that reads like protection.

The general principle: **a gate belongs where the boundary is, not where the
similar-looking check already lives.** Content that is legitimate in a local
artefact and illegitimate in public must be gated at the publish step.

## Alternatives Considered

1. **Add the marker to `_check_placeholders`** — the obvious fix, and where a
   reader naturally looks. Rejected: the validator runs before injection, so the
   pattern cannot fire in the real pipeline. It would pass review, add a test
   that passes, and protect nothing.
2. **Move the injection before Stage 4 so the validator sees it** — makes the
   existing gate work as written. Rejected: the post-Stage-4 ordering exists for
   a reason (the comment would distort word count, heading limits, and the
   AI-slop scan). Fixing the gate by breaking the validation it guards is a bad
   trade.
3. **Strip the comment at deploy instead of refusing** — quieter, always
   succeeds. Rejected: the comment's presence *is the signal* that no hero was
   drawn. Stripping it converts an actionable failure into a silent one and
   pushes the error downstream to the blog's `image:` requirement, where it is
   harder to diagnose.
4. **Add a post-Stage-4 validation pass over the final artefact** — validate what
   actually ships, not what Stage 4 produced. Rejected for now as heavier than
   the problem requires, but it is the more complete answer and is the natural
   escalation if a second post-validation transform appears (see Revisit if).

## Consequences

- **Positive:** the invariant is enforced where publication actually happens, so
  it holds regardless of what runs before it or what future post-validation
  transforms are added.
- **Positive:** both publish routes are covered by construction. The earlier
  design would have needed the same fix twice.
- **Positive:** failure is loud, local, and free — no network work happens before
  the check, and the message names the file and the fix.
- **Negative:** the check lives away from the other content checks, so a reader
  looking for "what stops bad content publishing" must know to look at
  `deploy_to_blog.py` as well as `publication_validator.py`. Mitigated by the
  docstring on `_reject_unrendered_hero_prompt`, which explains why it is not in
  the validator.
- **Negative:** it is marker-specific, not a general "no pipeline instructions in
  published output" rule. A different post-validation transform would need its
  own guard.
- **Follow-up:** if a second such transform appears, replace the per-marker
  guards with a post-Stage-4 validation pass over the shipped artefact
  (alternative 4).
- **Revisit if:** the injection ever moves before Stage 4, which would make the
  validator the right home after all; or a second post-validation transform makes
  the per-marker approach unscalable.

## References

- `BACKLOG.md` — BUG-065 (production escape), close-out defects 2026-07-28
- `data/skills_state/defect_tracker.json` — BUG-065 root-cause record
- Tests: `tests/test_deploy_rejects_hero_prompt_comment.py`
- Fix in the live post: `oviney/blog#1168` (merged `b3a29e5`, 2026-07-29)
- [ADR-0016](0016-single-pipeline-path.md) — the decision that made the hero-prompt comment rare but did not eliminate it
- [`docs/blog-integration-constraints.md`](../blog-integration-constraints.md) — the measured blog contract, incl. the required `image:` (B-019)
