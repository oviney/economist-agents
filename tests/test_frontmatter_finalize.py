#!/usr/bin/env python3
"""Deterministic frontmatter-finalize guarantees.

Root cause of recurring pipeline quarantines: mechanically-fixable
frontmatter defects (missing block, missing/stale ``date``, absent
``categories``) were routed through unreliable LLM regeneration and,
failing that, rejected as CRITICAL. ``apply_editorial_fixes`` is the
deterministic finalize step both pipelines share; when a finalize
``current_date`` is supplied it must guarantee a valid, complete
frontmatter block so the publication validator never blocks an
otherwise-publishable article on a mechanical issue.
"""

import yaml

from scripts.frontmatter_schema import REQUIRED_FIELDS, FrontmatterSchema
from scripts.publication_validator import PublicationValidator
from src.agent_sdk._shared import apply_editorial_fixes as _apply_editorial_fixes

_TODAY = "2026-07-13"
# A body long enough (>=700 words) to isolate mechanical checks from the
# legitimate word-count gate.
_LONG_BODY = " ".join(["Testing quality engineering matters."] * 200)


def _frontmatter_of(article: str) -> dict:
    assert article.startswith("---"), "article must carry a frontmatter block"
    return yaml.safe_load(article.split("---", 2)[1])


class TestReconstructsMissingFrontmatter:
    """A draft that lost its frontmatter entirely is rebuilt, not rejected."""

    def test_block_is_created(self) -> None:
        result = _apply_editorial_fixes(f"# Real Title\n\n{_LONG_BODY}", _TODAY)
        assert result.startswith("---\n")

    def test_all_required_fields_present(self) -> None:
        result = _apply_editorial_fixes(f"# Real Title\n\n{_LONG_BODY}", _TODAY)
        fm = _frontmatter_of(result)
        for field in REQUIRED_FIELDS:
            assert field in fm, f"reconstructed frontmatter missing '{field}'"

    def test_title_derived_from_h1(self) -> None:
        result = _apply_editorial_fixes(f"# Real Title\n\n{_LONG_BODY}", _TODAY)
        assert _frontmatter_of(result)["title"] == "Real Title"

    def test_date_is_finalize_date(self) -> None:
        result = _apply_editorial_fixes(f"# Real Title\n\n{_LONG_BODY}", _TODAY)
        assert str(_frontmatter_of(result)["date"]) == _TODAY

    def test_body_preserved(self) -> None:
        result = _apply_editorial_fixes(f"# Real Title\n\n{_LONG_BODY}", _TODAY)
        assert "Testing quality engineering matters." in result

    def test_image_is_empty_not_default_svg(self) -> None:
        # A blog-default.svg (or missing-file) hero is itself a CRITICAL; the
        # reconstruction must stamp an EMPTY image (chart-only), which passes.
        result = _apply_editorial_fixes(f"# Real Title\n\n{_LONG_BODY}", _TODAY)
        assert "blog-default.svg" not in result
        assert _frontmatter_of(result).get("image", "") in ("", None)


class TestLeadingWhitespace:
    """A draft with blank lines before ``---`` must not get a second block."""

    def test_no_double_frontmatter_block(self) -> None:
        draft = f'\n\n---\nlayout: post\ntitle: "T"\ndate: 2026-01-01\n---\n\n{_LONG_BODY}'
        result = _apply_editorial_fixes(draft, _TODAY)
        assert result.count("---") == 2  # exactly one frontmatter block

    def test_date_still_rewritten_despite_leading_blank_lines(self) -> None:
        draft = f'\n\n---\nlayout: post\ntitle: "T"\ndate: 2026-01-01\n---\n\n{_LONG_BODY}'
        result = _apply_editorial_fixes(draft, _TODAY)
        assert str(_frontmatter_of(result)["date"]) == _TODAY


class TestBackwardsCompatible:
    """Without a finalize date, behaviour is unchanged (no injection)."""

    def test_plain_text_not_wrapped(self) -> None:
        result = _apply_editorial_fixes("The organization grew steadily.")
        assert not result.startswith("---")

    def test_no_date_added_without_current_date(self) -> None:
        result = _apply_editorial_fixes("---\nlayout: post\n---\n\nBody", None)
        assert "date:" not in result.split("---", 2)[1]


class TestFillsPartialFrontmatter:
    """Present-but-incomplete frontmatter is completed deterministically."""

    def test_missing_date_added(self) -> None:
        article = '---\nlayout: post\ntitle: "T"\n---\n\nBody'
        result = _apply_editorial_fixes(article, _TODAY)
        assert f"date: {_TODAY}" in result

    def test_stale_date_overwritten(self) -> None:
        article = '---\nlayout: post\ntitle: "T"\ndate: 2026-01-01\n---\n\nBody'
        result = _apply_editorial_fixes(article, _TODAY)
        assert str(_frontmatter_of(result)["date"]) == _TODAY

    def test_missing_categories_added(self) -> None:
        article = '---\nlayout: post\ntitle: "T"\ndate: 2026-01-01\n---\n\nBody'
        result = _apply_editorial_fixes(article, _TODAY)
        assert "categories" in _frontmatter_of(result)

    def test_idempotent(self) -> None:
        article = f"# Real Title\n\n{_LONG_BODY}"
        once = _apply_editorial_fixes(article, _TODAY)
        twice = _apply_editorial_fixes(once, _TODAY)
        assert once == twice


class TestEndToEndNoMechanicalRejection:
    """The regression: the exact defects that quarantined the logged run
    must survive finalize as a publishable article."""

    def _mechanical_criticals(self, article: str) -> list[str]:
        validator = PublicationValidator(expected_date=_TODAY)
        _, issues = validator.validate(article)
        # Includes the image checks: finalize stamps image: when missing, and a
        # blog-default.svg / missing-file value is itself a CRITICAL — so a
        # naive default would re-quarantine the very articles this fix rescues.
        mechanical = {
            "date_mismatch",
            "yaml_format",
            "categories",
            "layout",
            "default_image_fallback",
            "missing_image_file",
        }
        return [
            i["check"]
            for i in issues
            if i.get("severity") == "CRITICAL" and i.get("check") in mechanical
        ]

    def test_missing_frontmatter_no_mechanical_criticals(self) -> None:
        finalized = _apply_editorial_fixes(f"# QA in 2026\n\n{_LONG_BODY}", _TODAY)
        assert self._mechanical_criticals(finalized) == []

    def test_stale_date_no_date_mismatch(self) -> None:
        article = (
            f'---\nlayout: post\ntitle: "QA in 2026"\ndate: 2026-01-01\n'
            f'author: "x"\ncategories: ["Quality Engineering"]\n'
            f'image: "/x.svg"\ndescription: "d"\n---\n\n{_LONG_BODY}'
        )
        finalized = _apply_editorial_fixes(article, _TODAY)
        assert "date_mismatch" not in self._mechanical_criticals(finalized)

    def test_reconstructed_passes_frontmatter_schema(self) -> None:
        finalized = _apply_editorial_fixes(f"# QA in 2026\n\n{_LONG_BODY}", _TODAY)
        fm = _frontmatter_of(finalized)  # asserts the block exists first
        assert FrontmatterSchema().validate(fm).is_valid
