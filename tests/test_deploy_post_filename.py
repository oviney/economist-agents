"""``_posts`` filenames must carry the deploy date — regression guard for BUG-069.

``deploy_to_blog`` intends to stamp the deploy date onto the post filename; its own
comment says "Rename article file to today's deploy date". The mechanism was::

    article_name = re.sub(r"^\\d{4}-\\d{2}-\\d{2}-", f"{deploy_date}-", article_path.name)

which **replaces** an existing date prefix but never **adds** one. That worked while
the pipeline wrote dated files (``output/2026-01-18-<slug>.md``). B-006/B-008 moved
generation to a canonical slug at ``output/posts/<slug>.md`` — undated — and the
substitution silently became a no-op, so the article would land at
``_posts/<slug>.md``.

Jekyll derives a post's date and URL from the filename (``_config.yml`` sets
``permalink: /:year/:month/:day/:title/``), and every one of the blog's 26 posts is
dated. An undated file is not a publishable post.

Why no gate caught it: ``scripts/validate-posts.sh`` globs ``_posts/*.md`` itself
rather than asking Jekyll, so it happily validates an undated file, and
``acceptance_blog_frontmatter.sh`` stages its own copy as
``_posts/2026-01-01-<slug>.md`` — a *different filename from the one the deploy path
produces*. The oracle passed on a name that would never exist.
"""

from __future__ import annotations

from scripts.deploy_to_blog import _dated_post_name


class TestDatedPostName:
    """The deploy date must end up on the filename, dated source or not."""

    def test_undated_source_gains_the_deploy_date(self) -> None:
        """The BUG-069 reproduction — current pipeline output is undated."""
        assert (
            _dated_post_name("review-queue-throughput-tax.md", "2026-07-29")
            == "2026-07-29-review-queue-throughput-tax.md"
        )

    def test_existing_date_is_replaced_not_stacked(self) -> None:
        """Legacy dated output must be re-stamped, not double-prefixed."""
        assert (
            _dated_post_name("2026-01-18-the-productivity-paradox.md", "2026-07-29")
            == "2026-07-29-the-productivity-paradox.md"
        )

    def test_slug_containing_digits_is_not_mistaken_for_a_date(self) -> None:
        """Only a full leading YYYY-MM-DD- counts as an existing prefix."""
        assert (
            _dated_post_name("2026-in-review-what-changed.md", "2026-07-29")
            == "2026-07-29-2026-in-review-what-changed.md"
        )
