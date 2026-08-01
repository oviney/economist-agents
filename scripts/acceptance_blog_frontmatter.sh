#!/usr/bin/env bash
# B-019 acceptance: does OUR generated front matter pass THE BLOG'S gate?
#
# Publishing the first real article failed oviney/blog's `validate-editorial`
# job four times. Each failure was on a rule our own publication_validator does
# not have, and `make ci-local` was green through all four. The lesson is in
# docs/blog-integration-constraints.md: a green local suite says nothing about
# what the blog accepts, and only the blog's own scripts are the oracle.
#
# This runs a pipeline-finalized article through the blog's two real validators
# in a real blog clone. It does NOT read the scripts and infer — it runs them.
#
# Usage:
#   scripts/acceptance_blog_frontmatter.sh <path-to-blog-clone> [article.md]
#
# With no article, a writer-shaped draft exhibiting every B-019 defect is
# finalized through apply_editorial_fixes and used as the subject.
#
# Exit: 0 = both gates pass (validate-post-quality exit 2 = warnings = pass).

set -euo pipefail

BLOG="${1:?usage: $0 <path-to-blog-clone> [article.md]}"
ARTICLE="${2:-}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PY:-$REPO_ROOT/.venv/bin/python}"

[[ -x "$BLOG/scripts/validate-posts.sh" ]] || {
  echo "not a blog clone (no scripts/validate-posts.sh): $BLOG" >&2; exit 2; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"; rm -f "${STAGED:-}" "${HERO_STAGED:-}"' EXIT

if [[ -z "$ARTICLE" ]]; then
  ARTICLE="$WORK/generated.md"
  # A draft in exactly the shape the Stage-3 writer emits, carrying every
  # defect B-019 fixes: over-long title, unquoted categories, no subtitle,
  # no tags, and the literal SLUG.png the old prompt asked for.
  "$PY" - "$ARTICLE" <<'PY'
import sys
from src.agent_sdk._shared import apply_editorial_fixes

DRAFT = '''---
layout: post
title: "Green Light, Red Ledger: Flaky Tests Are Engineering's Costliest Invisible Tax"
date: 2026-01-01
author: "Ouray Viney"
categories: [Quality Engineering, Test Automation]
image: /assets/images/SLUG.png
image_alt: "A developer watching a green dashboard while money drains away"
image_caption: "The build is green; the budget drains"
description: "Flaky tests do not merely annoy developers. They levy a recurring, unbudgeted tax on engineering payroll."
---

## The Green Build That Lies

A test suite that fails at random is worse than one that fails honestly. As the
chart shows, the cost lands on payroll rather than on any infrastructure line
item, which is precisely why it escapes budget scrutiny for so long.

## What The Numbers Say

Engineering time spent re-running suites is time not spent shipping. The
arithmetic is unglamorous and entirely mechanical.

## References

1. Example source one
2. Example source two
3. Example source three
'''

sys.stdout.write("finalizing a writer-shaped draft through apply_editorial_fixes\n")
open(sys.argv[1], "w").write(apply_editorial_fixes(DRAFT, "2026-01-01"))
PY
fi

# The blog derives the slug from the FILENAME, so the filename must come from
# our canonical slug — that is the thing under test.
SLUG="$("$PY" -c '
import sys
from src.agent_sdk._shared import canonical_slug
print(canonical_slug(open(sys.argv[1]).read(), "acceptance"))
' "$ARTICLE")"

# The blog REQUIRES a resolvable image:, so mirror what deploy_to_blog does —
# copy the hero asset in and link it. Without this the article is rejected with
# "hero image not set", which is how we learned there is no publishable
# chart-only article (B-015).
HERO_SRC="$REPO_ROOT/output/posts/images/${SLUG}-hero.svg"
HERO_STAGED="$BLOG/assets/images/${SLUG}-hero.svg"
if [[ ! -f "$HERO_SRC" ]]; then
  # No real hero drawn for this slug (B-016b will generate them). Stand in a
  # minimal well-formed SVG so the *front-matter* contract is what gets tested.
  HERO_SRC="$WORK/${SLUG}-hero.svg"
  printf '%s\n' \
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" role="img">' \
    '<title>Acceptance stand-in</title><rect width="1600" height="900" fill="#f3efe4"/>' \
    '</svg>' > "$HERO_SRC"
  echo "note: no hero at output/posts/images/${SLUG}-hero.svg — using a stand-in"
fi
mkdir -p "$BLOG/assets/images"
cp "$HERO_SRC" "$HERO_STAGED"

# Exercise the real linking code rather than hand-writing the image: line —
# _link_hero_asset is the thing that has to be right in production.
LINKED="$WORK/linked.md"
"$PY" - "$ARTICLE" "$SLUG" "$LINKED" "$(dirname "$HERO_STAGED")" <<'PY'
import sys
from pathlib import Path

from src.agent_sdk.pipeline import _link_hero_asset

article, slug, out, images_dir = sys.argv[1:5]
Path(out).write_text(
    _link_hero_asset(Path(article).read_text(), slug, images_dir=Path(images_dir))
)
PY

# B-029: this was STAGED="$BLOG/_posts/2026-01-01-${SLUG}.md" — the oracle
# composed its own dated filename instead of using the one deploy_to_blog
# produces. It therefore passed with 0 errors on article two while the deploy
# path was emitting an undated, unpublishable name (BUG-069). An oracle that
# renames its input is not testing the deploy path; it is testing a hypothetical
# one. Ask the deploy path for the name it would really use.
#
# The injected front-matter date stays fixed at 2026-01-01 so the run remains
# deterministic — only the *filename* derivation changes.
POST_NAME="$("$PY" - "$ARTICLE" <<'PY'
import sys
from pathlib import Path

from scripts.deploy_to_blog import _dated_post_name, is_publishable_post_name

name = _dated_post_name(Path(sys.argv[1]).name, "2026-01-01")

# validate-posts.sh globs _posts/*.md itself rather than asking Jekyll, so an
# undated file validates happily there. The oracle cannot delegate this check.
if not is_publishable_post_name(name):
    sys.exit(f"unpublishable: {name!r}")

print(name)
PY
)" || {
  echo "ACCEPTANCE FAILED — the deploy path produced an unpublishable _posts/ filename."
  echo "Jekyll needs YYYY-MM-DD-<slug>.md; see BUG-069 and B-029."
  exit 1
}

STAGED="$BLOG/_posts/${POST_NAME}"
cp "$LINKED" "$STAGED"
echo "staged: $(basename "$STAGED")  (slug ${#SLUG} chars, name from deploy path)"
echo

FAILED=0
echo "── the blog's scripts/validate-posts.sh ──"
( cd "$BLOG" && bash scripts/validate-posts.sh ) || FAILED=1

echo
echo "── the blog's scripts/validate-post-quality.sh ──"
set +e
( cd "$BLOG" && bash scripts/validate-post-quality.sh --all )
QUALITY=$?
set -e
# 0 = clean, 2 = warnings only (non-blocking on the blog), 1 = errors.
[[ $QUALITY -eq 0 || $QUALITY -eq 2 ]] || FAILED=1

echo
if [[ $FAILED -eq 0 ]]; then
  echo "ACCEPTANCE PASSED — generated front matter clears the blog's gate."
else
  echo "ACCEPTANCE FAILED — the blog would reject this article." >&2
fi
exit $FAILED
