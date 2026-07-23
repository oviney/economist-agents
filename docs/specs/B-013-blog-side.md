# B-013 · Blog-side changes (apply in `oviney/blog`)

> **These files live in the blog repo, not here.** Copy each block into
> `oviney/blog`, open one PR there, then run the **leak test** at the bottom
> before generating any real review draft. This is the owner-gated / outward half
> of B-013 (the economist-agents half — `deploy_to_blog --mode review` +
> `make publish` — is already built and merged).
>
> **Unverified until the leak test.** These are written against minimal-mistakes
> conventions but were not built/rendered here (no Jekyll in this repo). The leak
> test *is* their acceptance gate — do not skip it.

## Why a separate collection works (the design)

minimal-mistakes builds the homepage, archives, and category/tag/author pages
from `site.posts` (the `_posts` collection). A **separate `review` collection is
not in `site.posts`**, so it is naturally absent from every post listing.
`jekyll-feed` only emits `_posts` by default (so `feed.xml` is clean), and
`jekyll-sitemap` can be told to skip the collection with `sitemap: false`. The
`review` layout adds `noindex,nofollow`, and `robots.txt` disallows the path.
Belt-and-braces — the leak test confirms all of it.

---

## 1. `_config.yml` — add the `review` collection + defaults

```yaml
collections:
  review:
    output: true
    permalink: /review/:name/

defaults:
  # unlisted review drafts: own layout, keep out of the sitemap, noindex
  - scope:
      path: ""
      type: review
    values:
      layout: review
      sitemap: false      # jekyll-sitemap honours this → drops from sitemap.xml
      author_profile: false
      # minimal-mistakes: do NOT set `read_time`/`share`/`related` here — a
      # review draft is a bare reading surface.
```

> If `collections:` / `defaults:` already exist in `_config.yml`, **merge** these
> keys into the existing blocks rather than adding a second top-level key.

## 2. `_layouts/review.html` — reuse post styling, inject `noindex`

```html
---
layout: single
---
{{ content }}
```

…and add the robots tag via minimal-mistakes' supported head hook,
`_includes/head/custom.html` (create it if absent):

```liquid
{% if page.collection == "review" %}
<meta name="robots" content="noindex,nofollow">
{% endif %}
```

> `_includes/head/custom.html` is injected into `<head>` on every page by the
> theme; gating on `page.collection == "review"` keeps `noindex` off real posts.
> (Alternative if you prefer no shared include: put the `<meta>` directly in a
> non-`single`-based `review.html` `<head>`. The include approach is less code.)

## 3. `robots.txt` — disallow the path (create at repo root if absent)

```
User-agent: *
Disallow: /review/

Sitemap: https://viney.ca/sitemap.xml
```

> If a `robots.txt` already exists, just add the `Disallow: /review/` line.

---

## Leak test — the acceptance gate (run after the blog PR merges)

Deploy exactly **one** draft from economist-agents:

```bash
# from economist-agents, with BLOG_REPO_TOKEN set:
python -m scripts.deploy_to_blog --mode review --article output/posts/<slug>.md \
  --blog-owner oviney --blog-repo <blog-repo-name> --live-branch <main|gh-pages>
# → prints https://viney.ca/review/<slug>-<token>/
```

Wait for the Pages rebuild, then confirm the draft is reachable at its obscure
URL **and appears in NONE of these**:

- [ ] Homepage `https://viney.ca/` — not in the recent-posts list
- [ ] `/blog/` (or your posts index) — absent
- [ ] Category / tag / author archives — absent
- [ ] `https://viney.ca/feed.xml` — the `<slug>-<token>` is not present
- [ ] `https://viney.ca/sitemap.xml` — the `/review/<slug>-<token>/` URL is absent
- [ ] Site search (if enabled) — no hit
- [ ] View-source of the draft page shows `<meta name="robots" content="noindex,nofollow">`

If every box is checked, B-013 is done: mark it Done in `BACKLOG.md` and promote
with `make publish SLUG=<slug>` when you approve the post. **If any box fails**,
the collection is leaking — most likely `jekyll-feed`/minimal-mistakes is
configured to include extra collections; fix `_config.yml` before generating
more drafts.

## Open questions to resolve while doing this

1. **Live branch** — `main` or `gh-pages`? Pass it as `--live-branch` (and set
   `BLOG_LIVE_BRANCH` so `make publish` matches).
2. **Keep `make preview`?** (local instant look) — orthogonal; leave it if you
   use it.
3. **Auto-delete `_review/*` on promote** — `promote_review.py` deletes by
   default (`delete_after=True`); flip if you want to keep drafts for history.
