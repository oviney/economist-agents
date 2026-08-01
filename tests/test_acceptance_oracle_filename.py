"""The acceptance oracle must stage the deploy path's filename (B-029).

`scripts/acceptance_blog_frontmatter.sh` is documented as *the* oracle — "a green
local suite says nothing about what the blog accepts, and only the blog's own
scripts are the oracle". It passed on article two with 0 errors while the deploy
path was producing an **unpublishable filename** (BUG-069).

The cause was line 120: `STAGED="$BLOG/_posts/2026-01-01-${SLUG}.md"`. The oracle
composed its own dated filename instead of using the one `deploy_to_blog`
produces, which was `_posts/<slug>.md` — undated. **An oracle that renames its
input is not testing the deploy path; it is testing a hypothetical one.**

Two things are needed, and B-029 is explicit that the first alone is not enough:

1. Derive the staged name from the deploy path's own `_dated_post_name`.
2. Assert the result is publishable. The blog's `validate-posts.sh` globs
   `_posts/*.md` itself rather than asking Jekyll, so an undated file validates
   happily — the oracle cannot delegate this check.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import scripts.deploy_to_blog as dtb

REPO_ROOT = Path(__file__).resolve().parents[1]
ORACLE = REPO_ROOT / "scripts" / "acceptance_blog_frontmatter.sh"


class TestIsPublishablePostName:
    """Jekyll derives a post's date and URL from its filename.

    `_config.yml` sets `permalink: /:year/:month/:day/:title/`, so an undated
    file in `_posts/` is not a publishable post — it is silently not a post.
    """

    @pytest.mark.parametrize(
        "name",
        [
            "2026-07-31-review-queue-throughput-tax.md",
            "2026-01-01-x.md",
        ],
    )
    def test_dated_names_are_publishable(self, name: str) -> None:
        assert dtb.is_publishable_post_name(name)

    @pytest.mark.parametrize(
        "name",
        [
            "review-queue-throughput-tax.md",  # the BUG-069 shape
            "2026-7-31-short-month.md",
            "20260731-nodashes.md",
            "2026-07-31-.md",
            "2026-07-31-noextension",
            "",
        ],
    )
    def test_undated_or_malformed_names_are_not_publishable(self, name: str) -> None:
        assert not dtb.is_publishable_post_name(name)

    def test_the_deploy_path_produces_a_publishable_name(self) -> None:
        """BUG-069 regression, stated as a property rather than an example."""
        produced = dtb._dated_post_name("review-queue-throughput-tax.md", "2026-07-31")

        assert dtb.is_publishable_post_name(produced)

    def test_an_already_dated_source_stays_publishable(self) -> None:
        produced = dtb._dated_post_name("2026-01-01-old.md", "2026-07-31")

        assert dtb.is_publishable_post_name(produced)
        assert produced == "2026-07-31-old.md"


class TestOracleUsesTheDeployPathsFilename:
    """Static contract on the shell script — it is the thing that regressed."""

    @pytest.fixture(scope="class")
    def oracle_text(self) -> str:
        return ORACLE.read_text(encoding="utf-8")

    def test_oracle_does_not_compose_its_own_dated_filename(
        self, oracle_text: str
    ) -> None:
        """The exact defect: a hardcoded date glued onto the slug.

        Comments are excluded — the fix deliberately quotes the old line to
        explain itself, and a comment cannot stage a file.
        """
        code = [
            line
            for line in oracle_text.split("\n")
            if not line.lstrip().startswith("#")
        ]
        offenders = re.findall(
            r"_posts/\d{4}-\d{2}-\d{2}-\$\{?SLUG",
            "\n".join(code),
        )

        assert not offenders, (
            "the oracle is composing its own filename again: "
            f"{offenders}. It must use deploy_to_blog._dated_post_name."
        )

    def test_oracle_calls_the_deploy_paths_derivation(self, oracle_text: str) -> None:
        assert "_dated_post_name" in oracle_text

    def test_oracle_guards_the_staged_name(self, oracle_text: str) -> None:
        """It cannot delegate this to validate-posts.sh, which globs _posts/*.md."""
        assert "is_publishable_post_name" in oracle_text


class TestGuardFailsOnARegressedDeployPath:
    """B-029's central criterion, run rather than asserted statically.

    "Given a deploy path that emits an undated filename, the oracle **fails**
    (the BUG-069 reproduction — it currently passes)."

    The oracle's guard is a small Python block. These run that block against a
    deploy path stubbed back to its BUG-069 behaviour and require a non-zero
    exit — the thing that did not happen when it mattered.
    """

    GUARD = (
        "import sys\n"
        "from pathlib import Path\n"
        "from scripts.deploy_to_blog import _dated_post_name, "
        "is_publishable_post_name\n"
        "name = _dated_post_name(Path(sys.argv[1]).name, '2026-01-01')\n"
        "if not is_publishable_post_name(name):\n"
        "    sys.exit(f'unpublishable: {name!r}')\n"
        "print(name)\n"
    )

    def _run(self, article: str, stub: str = "") -> tuple[int, str]:
        import subprocess
        import sys

        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", stub + self.GUARD, article],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )
        return result.returncode, result.stdout + result.stderr

    def test_healthy_deploy_path_passes_and_emits_a_dated_name(self) -> None:
        code, out = self._run("output/posts/review-queue-throughput-tax.md")

        assert code == 0, out
        assert "2026-01-01-review-queue-throughput-tax.md" in out

    def test_bug_069_regression_makes_the_guard_fail(self) -> None:
        """Stub `_dated_post_name` back to the no-op that caused BUG-069."""
        stub = (
            "import scripts.deploy_to_blog as d\n"
            "d._dated_post_name = lambda source_name, deploy_date: source_name\n"
        )

        code, out = self._run("output/posts/review-queue-throughput-tax.md", stub)

        assert code != 0, "the oracle must fail on an undated filename"
        assert "unpublishable" in out
