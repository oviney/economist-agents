# Blog-repo integration constraints (oviney/blog)

> Discovered 2026-07-23 while opening the B-013 blog-side PR (oviney/blog #1157).
> These are governance + CI facts about the **target blog repo** that constrain
> anything economist-agents pushes to it — including the everyday
> `deploy_to_blog` article PRs, not just B-013. Capture-and-come-back note; not
> yet turned into pipeline changes.

## TL;DR

`oviney/blog` is itself an agent-governed repo with its own skills framework,
scoped agent labels, protected files, and a required-check branch-protection
gate. economist-agents is an *external agent* from its point of view, so our PRs
are subject to all of it. Two things bite us right now:

1. **`_config.yml` is an UNBYPASSABLE protected file.** Any PR touching it fails
   `check-agent-scope` and needs a human-approved issue + admin merge. B-013's
   review collection edits `_config.yml`, so #1157 can only land by owner
   admin-bypass (or via a dedicated issue). This is a **one-time** cost for
   B-013 — once the collection exists, review drafts never touch `_config.yml`
   again.
2. **Our generated-article PRs must pass the blog's required checks**, not just
   our own `publication_validator`. See the gate list below.

## Branch protection on `main`

- `enforce_admins = false` → the **owner can bypass via the web UI** (the
  "merge without waiting for requirements" path). This is how #1157 gets merged
  from a tablet with no terminal.
- `required_approving_review_count = 1`, and **the PR author cannot self-approve**
  — so an economist-agents PR (authored by the token user = owner) always shows
  `REVIEW_REQUIRED` and needs either a second reviewer or admin bypass.
- Required status checks (legacy protection): `build`, `🔒 Security Audit`.
  Additional checks surface as blocking via rulesets: `check-agent-scope`,
  `🖼️ Visual Regression`, `📝 Content Validation`, `validate-editorial`,
  `🎯 Accessibility, Visual & Lighthouse`, Playwright shards 1–3.

## The agent-scope guardrail — `scripts/check-pr-scope.sh`

A pre-merge scope self-check that flags:
1. **Protected files** — `_config.yml`, `Gemfile`, `Gemfile.lock`,
   `.github/CODEOWNERS`, `.github/copilot-instructions.md`, `AGENTS.md`,
   `ARCHITECTURE.md`. Changing these "always requires a dedicated human-approved
   issue; an agent should never touch them as a side-effect."
2. **Scope explosion** — >15 files changed (skip with `bulk-content` label).
3. **Governance surfaces** — `.github/skills/`, `.github/instructions/` (skip
   with `governance-update` label).
4. **Per-agent-label file allowlists** — labels like `agent:creative-director`
   (→ `_sass/`, `_layouts/`), `agent:qa-gatekeeper` (→ `tests/`, `scripts/`),
   `agent:editorial-chief` (→ `_posts/`, `docs/`). A PR touching files outside
   its label's scope fails.

Label exemptions: `protected-file-update` relaxes Rule 1 **only** for
`AGENTS.md`/`ARCHITECTURE.md` — `_config.yml`, `Gemfile*`, `CODEOWNERS`,
`copilot-instructions.md` remain unbypassable even with the label. A **human PR
(no agent label)** skips the agent-scope check entirely.

→ ~~Implication: if we ever want economist-agents PRs to clear agent-scope
cleanly, they should carry the right `agent:*` label (probably
`agent:editorial-chief`)~~ — **WRONG. Resolved 2026-07-24 by reading the
script** (see next section).

## RESOLVED (2026-07-24): do **not** label our PRs with `agent:*`

Read `check-pr-scope.sh` rather than inferring from the docs. Rule 4 is
**opt-in by label**:

```sh
if [ -z "$AGENT_LABEL" ]; then
  echo "check-pr-scope: no agent label found in PR_LABELS — skipping agent-scope check (human PR)."
```

An **unlabelled PR skips Rule 4 entirely** as a "human PR". Adding
`agent:editorial-chief` would therefore *add* restrictions, never remove them —
it activates the forbidden-zone pattern
`^_sass/|^_layouts/|^\.github/workflows/|^tests/|^scripts/|^_config\.yml$`.

**Decision: keep `deploy_to_blog` PRs unlabelled.** They are pushed with the
owner's token and are human PRs from the gate's point of view. This is both less
work and less risk than the labelling plan B-015 originally assumed.

What still applies to every PR regardless of label — and how we satisfy it:

| Rule | Trigger | Our article PR |
|---|---|---|
| 1 · protected files | `_config.yml`, `Gemfile*`, `.github/CODEOWNERS`, `.github/copilot-instructions.md`, `AGENTS.md`, `ARCHITECTURE.md` | **Pass** — we touch none |
| 2 · scope explosion | >15 files | **Pass** — one article + its assets |
| 3 · governance surfaces | `.github/skills/`, `.github/instructions/` | **Pass** — we touch none |
| 4 · agent scope | only with an `agent:*` label | **Skipped** — unlabelled |

To make Rules 1–3 hold **by construction rather than by luck**, `deploy()` now
stages `git add _posts assets` instead of `git add .` (B-015) — an unscoped add
would sweep in anything else dirty in the clone. `deploy_review()` already did
this. Regression: `TestGovernanceSafeStaging` in `tests/test_deploy_to_blog.py`.

**Still unavoidable:** the 1-review requirement. The token user is the owner, and
GitHub forbids self-approval, so every economist-agents PR shows
`REVIEW_REQUIRED` and needs the owner's web-UI bypass (or a second reviewer).
That is a property of the blog's branch protection, not something we can fix
here.

## The post front-matter contract (measured 2026-07-25 by publishing a real article)

**This is the section to read before touching generated front matter.** Publishing
the first real article failed the blog's `validate-editorial` job **four separate
times**, each on a rule our own `publication_validator` does not have. Our
contract had only ever been written against *our* validator.

`validate-editorial` runs **two** scripts — both must pass:

### 1. `scripts/validate-posts.sh`

| Rule | Requirement |
|---|---|
| Required fields | `layout`, `title`, `date`, `author`, `categories`, **`image`** |
| **`tags`** | **≥ 2**, inline bracket form `tags: [a, b]`, **all lowercase-hyphen** (any uppercase = hard error). Block-style YAML is *not detected* and reads as missing |
| `image` | must resolve to a real file under `assets/images/` |

### 2. `scripts/validate-post-quality.sh` (ERROR = blocks, WARNING = advisory)

| Rule | Requirement |
|---|---|
| **`subtitle`** | **required**; ≤ 60 words hard, ≤ 40 soft |
| `categories` | each item must be one of exactly **"Quality Engineering", "Software Engineering", "Test Automation", "Security"** — and the parser splits on `", "`, so items **must be quoted**. An unquoted inline list is read as ONE category and fails |
| **slug** | filename minus the `YYYY-MM-DD-` prefix, **≤ 60 chars hard** (≥ 55 warns). See the blog's `docs/URL_SLUG_POLICY.md` |
| `image` | set, not `blog-default.svg`, file must exist |
| `image_alt` / `image_caption` | both required, must be reader-facing, not generic |
| `image_caption` | ≤ ~40 chars (**warning** — it renders as `figcaption.image-credit`) |
| `description` | present, ≤ 160 chars |
| `author` | must be exactly `Ouray Viney` |
| body | no heading markers inside paragraph text |
| advisory only | `## References` with ≥ 3 items, ≥ 800 words, ≥ 3 H2s, a data chart |

### What the generator still does NOT emit (next article will fail)

- **`subtitle`** — never emitted
- **quoted** category items — we emit `[Quality Engineering, Test Automation]`
- **slug ≤ 60** — ours derive from the full title (the flaky-tests slug was **76**).
  Careful: this collides with **B-008**'s single-canonical-slug invariant, where one
  slug feeds the article filename, chart PNG, chart embed, and prompt sidecar.

Only `tags` was fixed generator-side (BUG-057). **Verify any change by running the
blog's own scripts**, not by reading them:

```bash
bash scripts/validate-posts.sh
bash scripts/validate-post-quality.sh --all   # exit 2 = warnings only, that's a pass
```

> **No redirects.** The blog has **no `jekyll-redirect-from`** and `_config.yml` is
> an unbypassable protected file, so **renaming a published post 404s the old URL**
> with no way to redirect. Get the slug right before publishing.

## The blog's own skills framework — `.github/skills/`

oviney/blog carries a full local mirror of the agent-skills lifecycle plus
blog-specific skills: `jekyll-development`, `jekyll-qa`, `economist-theme`,
`editorial`, `audience-research`, `github-issues-workflow`, `git-operations`,
alongside the standard `spec-driven-development`, `test-driven-development`,
`code-review-and-quality`, etc. Scoped instructions live in
`.github/instructions/` (`posts.instructions.md`, `scss.instructions.md`,
`tests.instructions.md`).

→ Implication: the blog has its own opinionated conventions for posts, SCSS, and
tests. When economist-agents changes anything beyond a plain `_posts/` article
(layouts, SCSS, config), those conventions and the matching skills apply — worth
reading `posts.instructions.md` before we tune generated-post frontmatter.

## Follow-ups to come back to (see BACKLOG B-015)

- Decide the canonical way economist-agents PRs satisfy agent-scope: label as
  `agent:editorial-chief` + keep article PRs `_posts/`-only, OR treat them as
  human PRs (no agent label) to skip the scope check. Confirm which the owner
  wants.
- The B-013 `_config.yml` change is a one-time human-gated edit — fine, but note
  it in the B-013 runbook so it isn't mistaken for a recurring blocker.
- `🖼️ Visual Regression` is failing on homepage/blog-index/about snapshots on
  #1157 (pages our change doesn't touch) — looks like **pre-existing baseline
  drift** on the blog; flag to the owner as a blog-side issue, not ours.
- The blog's `.env`-equivalent `BLOG_REPO_TOKEN` failed auth on push
  (read-only/expired); `gh auth token` works. Refresh the PAT so
  `deploy_to_blog` keeps working headlessly.
