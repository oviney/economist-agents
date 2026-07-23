# Spec: B-013 · Live unlisted draft review on GitHub Pages

> Status: **DRAFT — awaiting owner LGTM before planning.**
> Builds on the idea one-pager `docs/ideas/live-draft-review.md` and the keyless
> deploy path (`scripts/deploy_to_blog.py`, B-010). Executes the "review the
> rendered post, not a PR diff" direction.

## Assumptions I'm making (correct these before I plan)

1. **This is a cross-repo feature.** The Jekyll config, the `review` layout, and
   `robots.txt` live in the **`oviney/blog`** repo; only `deploy_to_blog.py`
   (`--mode review`) and the `make publish` wrapper live in **economist-agents**.
   The spec covers both sides; the blog-repo changes ship as a separate small PR
   on `oviney/blog`.
2. **Drafts are non-sensitive.** They are AI-generated posts built on public
   statistics. Owner has confirmed nothing confidential — so **unlisted + noindex
   (obscurity), not real auth**, is the accepted trade (one-pager, confirmed).
3. **The blog is minimal-mistakes on GitHub Pages**, default branch builds the
   live site, `BLOG_REPO_TOKEN` (free fine-grained PAT scoped to `oviney/blog`)
   can push to it. Pages rebuilds on push to the live branch — no Action needed.
4. **The obscurity token is generated with Python `secrets`** (`token_hex(4)` →
   8 hex chars). Committed in the filename + permalink; not stored anywhere
   public-facing beyond the URL the pipeline prints to the operator.
5. **`make publish` operates on a fresh clone** of the blog (same mechanism
   `deploy_to_blog` already uses), not on a long-lived working copy.

→ Correct any of these now or I plan against them.

## Objective

Replace the GitHub-PR-diff review surface (built for code, useless for prose)
with the **actual rendered post** at an obscure, `noindex`, **live** URL
`https://viney.ca/review/<slug>-<token>/`. The owner reviews the real post — in
the real theme, from a phone if they want — and promotes it to `_posts/` with one
command when approved. Nothing appears to ordinary visitors.

**Who is the user:** the blog owner (sole reviewer), reviewing generated drafts.
**Success looks like:** a keyless run prints one obscure URL; the owner opens it
and sees the fully-rendered post; that same post is reachable from **none** of
the site's public surfaces; `make publish SLUG=…` moves it into `_posts/` and it
goes live normally.

## Tech Stack

- Jekyll + minimal-mistakes on GitHub Pages (blog repo, static host, no server
  auth) — unchanged.
- Python 3.12 keyless pipeline (this repo); `scripts/deploy_to_blog.py` extended.
- `gh` CLI / git over `BLOG_REPO_TOKEN` for pushes — unchanged, **but `--mode
  review` opens no PR**.

## Commands

```
# Generate a draft to the live review surface (no PR):
python -m scripts.deploy_to_blog --mode review        # writes _review/<slug>-<token>.md, commits to live branch, prints URL

# Promote a reviewed draft to a real post (the publish gate):
make publish SLUG=<slug>                               # _review/<slug>-<token>.md -> _posts/YYYY-MM-DD-<slug>.md, commit+push

# Local instant look (kept, optional, no deploy):
make preview                                           # unchanged if it exists; see Open Questions
```

## Project Structure

**economist-agents (this repo):**
```
scripts/deploy_to_blog.py     → add --mode {post,review} (default: post — no behaviour change)
Makefile                      → add `publish` target (wraps a promote helper)
scripts/promote_review.py     → NEW: clone blog, move _review/* -> _posts/, commit+push (called by make publish)
tests/test_deploy_review_mode.py → NEW: --mode review path (mocked git/subprocess)
tests/test_promote_review.py     → NEW: promote path (mocked)
docs/specs/B-013-live-draft-review.md → this file
```

**oviney/blog (separate PR):**
```
_config.yml                   → `review` collection (output:true, permalink:/review/:name/), excluded from feed + sitemap + listings
_layouts/review.html          → NEW: reuses single/post styling, injects <meta name="robots" content="noindex,nofollow">
robots.txt                    → Disallow: /review/
```

## Code Style

`--mode` is an explicit enum; **`post` stays the default so existing behaviour is
untouched**. The review branch of `deploy()` shares clone/render, diverges only at
write-target + commit + no-PR:

```python
def deploy(*, mode: Literal["post", "review"] = "post", ...) -> DeployResult:
    ...  # clone, render article + chart — shared
    if mode == "review":
        token = secrets.token_hex(4)                       # 8 hex chars
        dest = blog_dir / "_review" / f"{slug}-{token}.md"
        _write_with_layout(dest, article, layout="review") # front-matter layout: review
        run_command("git add _review", cwd=blog_dir)
        run_command(f'git commit -m "review draft: {slug}-{token}"', cwd=blog_dir)
        run_command(f"git push origin {live_branch}", cwd=blog_dir)  # NO PR
        url = f"https://{BLOG_HOST}/review/{slug}-{token}/"
        logger.info("Review URL (unlisted, noindex): %s", url)
        return DeployResult(mode="review", url=url, branch=live_branch, pr_url=None)
    # mode == "post": existing branch+_posts+PR path, unchanged
```

## Testing Strategy

- **Unit (this repo, mocked git/subprocess):** `--mode review` writes to
  `_review/`, sets `layout: review`, generates an 8-hex token, commits to the
  live branch, opens **no** PR, and returns the obscure URL. `make publish`
  promotes `_review/<slug>-<token>.md` → `_posts/YYYY-MM-DD-<slug>.md` with a
  valid Jekyll date prefix and pushes. Default `--mode post` is byte-for-byte
  unchanged (regression).
- **The acceptance gate is a live leak test (owner-run, outward — see below).**
  It cannot be unit-tested; it is a manual checklist against the deployed site.
- `make ci-local` stays green (coverage ≥70 / `src/quality` ≥90).

## Boundaries

- **Always:** keep `--mode post` the default; keyless (`BLOG_REPO_TOKEN` only, no
  AI key); print the URL to the operator, never to a public index.
- **Ask first (owner-gated, outward):** the **live leak-test deploy** to
  viney.ca; the blog-repo `_config.yml`/layout PR; anything that pushes to the
  blog's live branch for the first time under this feature.
- **Never:** a public `/review/` index page; real auth / Cloudflare / private-repo
  Pages (paywall — violates the no-paywall constraint); publish-then-retract;
  keeping the PR diff as the review surface.

## Success Criteria

1. `python -m scripts.deploy_to_blog --mode review` writes
   `_review/<slug>-<token>.md` (`layout: review`, 8-hex token), commits to the
   live branch, opens **no PR**, and prints `https://viney.ca/review/<slug>-<token>/`.
2. **Leak test PASSES (owner-run):** after deploying exactly one draft, it appears
   in **NONE** of: homepage `/`, `/blog/`, category/tag/author archives,
   `feed.xml`, `sitemap.xml`, site search. The rendered post itself is reachable
   only at its obscure URL and carries `noindex,nofollow`.
3. `make publish SLUG=<slug>` moves the draft to `_posts/YYYY-MM-DD-<slug>.md`,
   pushes, and the post then appears normally in listings + feed.
4. Default `--mode post` behaviour is unchanged (regression test + green ci-local).
5. No new API key, subscription, or paid service introduced (constraint check).

## Open Questions

1. **Live branch name** on `oviney/blog` — `main` or `gh-pages`? (Determines the
   push target; needs the owner or a `git remote show`.)
2. **Promote = command vs. blog-side action?** MVP: `make publish` command.
3. **Keep `make preview`** as the instant no-deploy look, or make live review the
   single surface? Lean: live is primary, `make preview` stays optional.
4. **Auto-delete `_review/*` after promotion**, or keep for history? Lean: delete
   on promote (avoids stale-draft accumulation on the live host).
5. **Does `deploy_to_blog` currently hard-code the PR path** such that adding
   `--mode` needs a refactor of `deploy()` into shared + per-mode tails? (Impl
   detail for the plan; not a blocker.)

## Not in this spec (deferred)

Multi-reviewer flow; scheduled cleanup of stale drafts; a private draft index;
comment/annotation on drafts. All are post-MVP per the one-pager.
