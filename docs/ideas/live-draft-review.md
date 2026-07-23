# Live Draft Review on GitHub Pages

## Problem Statement
How might we let the owner review a generated draft rendered exactly as it will
look published — from anywhere, including a phone — without exposing it to
readers and without adding paid infrastructure?

## Recommended Direction
A Jekyll **`review` collection** that builds unapproved drafts to an obscure,
**live** URL on the existing Pages site (viney.ca) using the real
minimal-mistakes theme — but excluded from nav, pagination, the RSS feed, the
sitemap, and search (`<meta name="robots" content="noindex,nofollow">` + a
`robots.txt` disallow). The owner reviews the *actual rendered post* at
`/review/<slug>-<token>/`; nothing appears to normal visitors.

This is the owner's original idea, corrected on one point: GitHub Pages is a
static host with **no server-side auth**, so drafts are **unlisted + noindex
(obscurity), not secured**. For a personal tech/quality blog whose drafts are
AI-generated posts built on public statistics, that is the right trade — real
access control (Cloudflare Access) would be over-engineering for a negligible
threat, and would add the very infra we are avoiding. It stays designed-in as an
escape hatch if sensitivity ever rises.

The review surface stops being a GitHub PR diff (built for code, useless for
prose). The blog PR either disappears or becomes a pure publish record at
*approve* time.

## Key Assumptions to Validate
- [ ] **The theme does not surface the collection.** Deploy one draft, then
      confirm it appears in NONE of: homepage, `/blog/`, category/tag/author
      archives, `feed.xml`, `sitemap.xml`. (minimal-mistakes can loop over
      collections — this is the #1 risk.)
- [ ] **No public draft index.** The list of pending drafts must not be
      discoverable; the pipeline prints each direct obscure URL instead.
- [ ] **`noindex` + obscure token are enough** for non-sensitive drafts
      (owner confirmed: nothing confidential).
- [ ] **`deploy_to_blog` can commit live to a collection** (not just `_posts` +
      PR) and Pages rebuilds it.

## MVP Scope
**In:**
- A `review` collection in `_config.yml` (`output: true`,
  `permalink: /review/:name/`), excluded from feed/sitemap/listings.
- A minimal `review` layout that reuses the post styling + injects `noindex`.
- `deploy_to_blog.py`: new `--mode review` that writes the article + chart to
  `_review/<slug>-<token>.md`, commits to the live branch, and prints the URL
  (no PR).
- `make publish SLUG=<slug>`: promote a reviewed draft — move `_review/*` →
  `_posts/YYYY-MM-DD-*.md`, commit/push (this is the real publish gate).

**Out (MVP):** a public `/review/` index; auth; scheduled cleanup of stale
drafts; multi-reviewer flow.

## Not Doing (and Why)
- **Cloudflare Access / real auth** — the threat is negligible; it adds infra we
  are deliberately shedding. Escape hatch only.
- **A private-repo Pages site** — private-repo Pages needs a paid GitHub plan.
  Violates no-paywall.
- **Publish-then-retract (inversion)** — sprays half-baked posts + RSS at
  readers; wrong for a curated blog.
- **Keeping the PR as the review surface** — a diff cannot convey prose; this is
  the whole problem we are removing.
- **A public list of pending drafts** — turns obscurity into a single-URL leak
  of everything.

## Open Questions
- Promote action: a `make publish` command, or a tiny action on the blog itself?
  (MVP: command.)
- Keep local `make preview` too as the instant no-deploy look, or is the live
  review the single surface? (Lean: live is primary; `make preview` optional.)
- Auto-delete `_review/*` after promotion, or leave for history?
