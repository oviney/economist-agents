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

→ Implication: if we ever want economist-agents PRs to clear agent-scope
cleanly, they should carry the right `agent:*` label (probably
`agent:editorial-chief`, since generated articles land in `_posts/`) and stay
within that label's file scope — i.e. a generated-article PR must touch **only**
`_posts/` + its assets, nothing else.

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
