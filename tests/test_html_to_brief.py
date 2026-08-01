"""Tests for scripts/html_to_brief.py — Claude HTML artifact → markdown research brief.

B-038. The converter's contract is *transport*, not judgment: quotes, tables and URLs
survive verbatim, chrome is dropped, and nothing else is dropped at all. The round-trip
is asserted against the **real** ``load_brief_file`` (never a mirrored regex), because
that loader is the only consumer whose behaviour matters.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from scripts import html_to_brief
from scripts.html_to_brief import (
    REFUTED_HEADING,
    BriefConversionError,
    build_brief,
    html_to_markdown,
    main,
)
from src.agent_sdk.pipeline import load_brief_file

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "html_briefs"
REPO_ROOT = Path(__file__).parent.parent
SAMPLE_DIR = REPO_ROOT / "docs" / "research" / "samples"

#: The chrome the spec says to drop. Hardcoded rather than imported from the module so a
#: change that starts dropping *content* tags fails these tests instead of moving with them.
SPEC_CHROME_TAGS = ("script", "style", "nav", "footer", "head")


def read_fixture(name: str) -> str:
    """Read a fixture HTML file by bare name."""
    return (FIXTURE_DIR / f"{name}.html").read_text()


def words(text: str) -> Counter[str]:
    """Multiset of alphanumeric word tokens, ignoring all punctuation and markup."""
    return Counter(re.findall(r"[0-9A-Za-z]+", text))


def content_words(html: str) -> Counter[str]:
    """Word multiset of the HTML's *content* tree — chrome removed, computed independently."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(SPEC_CHROME_TAGS):
        tag.decompose()
    return words(soup.get_text(" "))


# ═══════════════════════════════════════════════════════════════════════════
# The invariant that matters most: nothing is silently dropped
# ═══════════════════════════════════════════════════════════════════════════


class TestNothingSilentlyDropped:
    """Every word of content in, every word of content out."""

    @pytest.mark.parametrize(
        "fixture", ["headings_and_prose", "blockquote_heavy", "table_bearing"]
    )
    def test_every_content_word_survives_conversion(self, fixture: str) -> None:
        html = read_fixture(fixture)
        out = words(build_brief(html, source_name=f"{fixture}.html"))

        missing = content_words(html) - out
        assert not missing, f"conversion dropped: {sorted(missing)}"

    def test_unrecognised_elements_are_converted_not_discarded(self) -> None:
        html = (
            "<html><body><h1>T</h1>"
            "<figure><figcaption>A caption nobody mapped</figcaption></figure>"
            "<claude-note>An element that does not exist in HTML</claude-note>"
            "</body></html>"
        )
        out = build_brief(html, source_name="x.html")

        assert "A caption nobody mapped" in out
        assert "An element that does not exist in HTML" in out


class TestInlineSvgDiagrams:
    """Claude draws diagrams as inline SVG. Flattened into prose, a diagram key reads
    as a claim — the fidelity hazard ADR-0018 is about."""

    SVG_HTML = (
        "<html><body><h1>T</h1><p>Before.</p>"
        '<svg viewBox="0 0 10 10">'
        "<text>Schedule Pressure</text><text>+</text>"
        "<text>Feature Velocity</text><path d='M0 0'/>"
        "</svg><p>After.</p></body></html>"
    )

    def test_every_svg_label_survives(self) -> None:
        out = build_brief(self.SVG_HTML, source_name="x.html")

        assert "Schedule Pressure" in out
        assert "Feature Velocity" in out

    def test_labels_are_marked_as_a_diagram_not_left_reading_as_prose(self) -> None:
        out = build_brief(self.SVG_HTML, source_name="x.html")

        assert "*Diagram (inline SVG in the source) — labels only:*" in out
        assert "Schedule Pressure · + · Feature Velocity" in out

    def test_the_diagram_does_not_absorb_the_prose_around_it(self) -> None:
        out = build_brief(self.SVG_HTML, source_name="x.html")

        assert "\nBefore.\n" in out
        assert "\nAfter.\n" in out


class TestChromeIsDropped:
    """Styling and navigation are not content."""

    def test_script_and_style_and_nav_and_footer_are_dropped(self) -> None:
        out = build_brief(read_fixture("headings_and_prose"), source_name="x.html")

        assert "analytics beacon" not in out  # <script>
        assert "Georgia" not in out  # <style>
        assert "Home" not in out  # <nav>
        assert "Generated in conversation" not in out  # <footer>

    def test_dropping_chrome_does_not_take_content_with_it(self) -> None:
        out = build_brief(read_fixture("headings_and_prose"), source_name="x.html")

        assert "Internal developer platforms are pitched as a cure" in out


# ═══════════════════════════════════════════════════════════════════════════
# Structure mapping — three fixture shapes, proving template independence
# ═══════════════════════════════════════════════════════════════════════════


class TestHeadingsAndProse:
    """Fixture 1: the ordinary shape — headings, paragraphs, lists, links."""

    @pytest.fixture
    def brief(self) -> str:
        return build_brief(read_fixture("headings_and_prose"), source_name="x.html")

    def test_h1_becomes_the_brief_title_at_top_level(self, brief: str) -> None:
        assert brief.startswith(
            "# Platform Engineering Adoption: What the Evidence Says\n"
        )

    def test_the_promoted_title_is_not_also_repeated_as_a_body_heading(
        self, brief: str
    ) -> None:
        headings = re.findall(r"(?m)^#+ .*$", brief)
        titles = [h for h in headings if "Platform Engineering Adoption" in h]
        assert titles == ["# Platform Engineering Adoption: What the Evidence Says"]

    def test_source_headings_are_demoted_below_the_brief_title(
        self, brief: str
    ) -> None:
        assert "\n### Where the claim comes from\n" in brief  # h2 → ###
        assert "\n#### The caveat everyone drops\n" in brief  # h3 → ####

    def test_links_keep_their_url_verbatim(self, brief: str) -> None:
        assert "[DORA report](https://dora.dev/research/2024/dora-report/)" in brief

    def test_emphasis_and_inline_code_are_preserved(self, brief: str) -> None:
        assert "**1,500 engineers**" in brief
        assert "*not*" in brief
        assert "`adopt`" in brief

    def test_unordered_list_nesting_is_preserved(self, brief: str) -> None:
        assert "- Platform team headcount as a share of engineering" in brief
        assert "  - Measured from repository creation" in brief

    def test_ordered_lists_are_numbered(self, brief: str) -> None:
        assert "1. Measure the baseline before building anything." in brief
        assert "3. Refuse to mandate it for six months." in brief


class TestBlockquoteHeavy:
    """Fixture 2: the quotes carry the argument, so they must survive byte-identical."""

    @pytest.fixture
    def brief(self) -> str:
        return build_brief(read_fixture("blockquote_heavy"), source_name="x.html")

    def test_blockquote_text_is_verbatim(self, brief: str) -> None:
        assert (
            "> The bot reviews in ninety seconds. The human still takes two days. "
            "We did not shorten the queue; we added a step to it." in brief
        )

    def test_blockquote_without_a_wrapping_paragraph_still_converts(
        self, brief: str
    ) -> None:
        assert (
            "> Every suggestion is plausible. That is exactly the problem — plausible "
            "is the hardest thing to reject." in brief
        )

    def test_multi_paragraph_blockquote_keeps_both_paragraphs_quoted(
        self, brief: str
    ) -> None:
        assert "> — Staff engineer, payments" in brief
        assert ">\n> — Staff engineer, payments" in brief

    def test_emphasis_inside_a_quote_survives(self, brief: str) -> None:
        assert "**thirty per cent**" in brief

    def test_pre_becomes_a_fenced_block_with_the_code_verbatim(
        self, brief: str
    ) -> None:
        assert (
            "```\nif (user) { await audit.log(user.token) }  // the class it catches\n```"
            in brief
        )


class TestTableBearing:
    """Fixture 3: dropping a table would lose the comparison entirely."""

    @pytest.fixture
    def brief(self) -> str:
        return build_brief(read_fixture("table_bearing"), source_name="x.html")

    def test_table_with_a_header_becomes_a_gfm_table(self, brief: str) -> None:
        assert "| Option | Year-one cost | Ongoing FTE | Notes |" in brief
        assert "| --- | --- | --- | --- |" in brief
        assert (
            "| Hybrid | $160,000 | 1.2 | Traces vendor-side, metrics local |" in brief
        )

    def test_pipes_inside_cells_are_escaped_so_the_table_stays_valid(
        self, brief: str
    ) -> None:
        assert r"Priced per host \| per GB ingested" in brief

    def test_line_breaks_inside_cells_do_not_break_the_row(self, brief: str) -> None:
        assert (
            "| Self-hosted OSS | $95,000 | 2.0 | Includes on-call rotation |" in brief
        )

    def test_headerless_table_still_renders_every_data_row(self, brief: str) -> None:
        assert (
            "| Retention | 13 months | Vendor default; extending costs 40% more |"
            in brief
        )
        assert (
            "| Cardinality ceiling | ~1M series | Self-hosted hits this first |"
            in brief
        )

    def test_query_string_urls_survive_unescaped(self, brief: str) -> None:
        assert "(https://example.com/pricing?tier=enterprise&region=us-east-1)" in brief

    def test_quotation_and_rule_and_bold_italic_elements_map(self, brief: str) -> None:
        assert (
            '"High-cardinality labels are the single most common cause of '
            'unexpected bills."' in brief
        )
        assert "\n---\n" in brief
        assert "**Bottom line:**" in brief
        assert "*trace volume*" in brief


# ═══════════════════════════════════════════════════════════════════════════
# The round-trip — asserted against the REAL loader, never a mirrored regex
# ═══════════════════════════════════════════════════════════════════════════


class TestRefutedRoundTrip:
    """``## Refuted`` is the one thing the loader actually does. Prove it end to end."""

    @pytest.fixture
    def brief_path(self, tmp_path: Path) -> Path:
        path = tmp_path / "brief.md"
        path.write_text(
            build_brief(read_fixture("headings_and_prose"), source_name="x.html")
        )
        return path

    def test_the_brief_always_carries_an_empty_refuted_section(
        self, brief_path: Path
    ) -> None:
        assert REFUTED_HEADING in brief_path.read_text()

    def test_the_real_loader_strips_the_refuted_section(self, brief_path: Path) -> None:
        loaded = load_brief_file(brief_path)

        assert "Refuted" not in loaded

    def test_the_real_loader_keeps_the_converted_body(self, brief_path: Path) -> None:
        loaded = load_brief_file(brief_path)

        assert "Internal developer platforms are pitched as a cure" in loaded
        assert "[DORA report](https://dora.dev/research/2024/dora-report/)" in loaded

    def test_a_claim_moved_into_refuted_is_excluded_by_construction(
        self, brief_path: Path
    ) -> None:
        text = brief_path.read_text()
        assert "The throughput figure is measured against teams" in text

        moved = text.replace(
            "The throughput figure is measured against teams that had no golden path at all.",
            "",
        ).replace(
            REFUTED_HEADING,
            f"{REFUTED_HEADING}\n\nThe throughput figure is measured against teams "
            "that had no golden path at all.",
        )
        brief_path.write_text(moved)

        loaded = load_brief_file(brief_path)

        assert "The throughput figure is measured against teams" not in loaded

    def test_refuted_is_the_last_section_so_the_loader_strips_to_eof(self) -> None:
        brief = build_brief(read_fixture("table_bearing"), source_name="x.html")

        heading_positions = [m.start() for m in re.finditer(r"(?m)^## ", brief)]
        assert heading_positions, "expected at least the Refuted heading"
        assert brief.index(REFUTED_HEADING) == heading_positions[-1]


# ═══════════════════════════════════════════════════════════════════════════
# Failure modes — a hollow brief is worse than an error
# ═══════════════════════════════════════════════════════════════════════════


class TestRefusesToEmitAHollowBrief:
    def test_empty_input_raises(self) -> None:
        with pytest.raises(BriefConversionError):
            build_brief("", source_name="x.html")

    def test_html_with_only_chrome_raises(self) -> None:
        with pytest.raises(BriefConversionError):
            build_brief(
                "<html><head><style>p{color:red}</style></head>"
                "<body><script>go()</script><nav>Home</nav></body></html>",
                source_name="x.html",
            )

    def test_the_error_message_names_the_source(self) -> None:
        with pytest.raises(BriefConversionError, match="conversation.html"):
            build_brief("   ", source_name="conversation.html")


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


class TestCli:
    def test_writes_the_brief_to_the_slug_path(self, tmp_path: Path) -> None:
        src = tmp_path / "artifact.html"
        src.write_text(read_fixture("headings_and_prose"))
        out_dir = tmp_path / "research"

        code = main([str(src), "--slug", "platform-eng", "--out-dir", str(out_dir)])

        assert code == 0
        written = out_dir / "platform-eng.md"
        assert written.exists()
        assert written.read_text().startswith("# Platform Engineering Adoption")

    def test_missing_input_file_exits_non_zero_without_writing(
        self, tmp_path: Path
    ) -> None:
        out_dir = tmp_path / "research"

        code = main(
            [str(tmp_path / "nope.html"), "--slug", "x", "--out-dir", str(out_dir)]
        )

        assert code != 0
        assert not (out_dir / "x.md").exists()

    def test_content_free_input_exits_non_zero_without_writing(
        self, tmp_path: Path
    ) -> None:
        src = tmp_path / "hollow.html"
        src.write_text("<html><body><script>x()</script></body></html>")
        out_dir = tmp_path / "research"

        code = main([str(src), "--slug", "hollow", "--out-dir", str(out_dir)])

        assert code != 0
        assert not (out_dir / "hollow.md").exists()

    def test_refuses_to_overwrite_an_edited_brief_unless_forced(
        self, tmp_path: Path
    ) -> None:
        src = tmp_path / "artifact.html"
        src.write_text(read_fixture("headings_and_prose"))
        out_dir = tmp_path / "research"
        out_dir.mkdir()
        existing = out_dir / "platform-eng.md"
        existing.write_text("# hand-edited, do not clobber\n")

        code = main([str(src), "--slug", "platform-eng", "--out-dir", str(out_dir)])

        assert code != 0
        assert existing.read_text() == "# hand-edited, do not clobber\n"

    def test_force_overwrites(self, tmp_path: Path) -> None:
        src = tmp_path / "artifact.html"
        src.write_text(read_fixture("headings_and_prose"))
        out_dir = tmp_path / "research"
        out_dir.mkdir()
        (out_dir / "platform-eng.md").write_text("stale\n")

        code = main(
            [str(src), "--slug", "platform-eng", "--out-dir", str(out_dir), "--force"]
        )

        assert code == 0
        assert "stale" not in (out_dir / "platform-eng.md").read_text()

    def test_a_slug_containing_a_path_separator_is_rejected(
        self, tmp_path: Path
    ) -> None:
        src = tmp_path / "artifact.html"
        src.write_text(read_fixture("headings_and_prose"))

        code = main(
            [str(src), "--slug", "../escape", "--out-dir", str(tmp_path / "research")]
        )

        assert code != 0

    def test_runs_as_a_script_end_to_end(self, tmp_path: Path) -> None:
        src = tmp_path / "artifact.html"
        src.write_text(read_fixture("table_bearing"))
        out_dir = tmp_path / "research"

        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "html_to_brief.py"),
                str(src),
                "--slug",
                "build-vs-buy",
                "--out-dir",
                str(out_dir),
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )

        assert result.returncode == 0, result.stderr
        assert (out_dir / "build-vs-buy.md").exists()


# ═══════════════════════════════════════════════════════════════════════════
# Real artifacts — synthetic fixtures only prove we handle HTML we imagined
# ═══════════════════════════════════════════════════════════════════════════


def _sample_artifacts() -> list[Path]:
    return sorted(SAMPLE_DIR.glob("*.html")) if SAMPLE_DIR.exists() else []


class TestRealClaudeArtifacts:
    """The repo's own Claude artifact, plus any real sample the owner has dropped in."""

    REAL_ARTIFACT = (
        REPO_ROOT / "docs" / "reviews" / "review-queue-throughput-tax-42d2fbb4.html"
    )

    def test_the_repo_artifact_converts_without_losing_content(self) -> None:
        html = self.REAL_ARTIFACT.read_text()

        brief = build_brief(html, source_name=self.REAL_ARTIFACT.name)

        missing = content_words(html) - words(brief)
        assert not missing, f"conversion dropped: {sorted(missing)}"

    def test_the_repo_artifact_round_trips_through_the_real_loader(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "brief.md"
        path.write_text(
            build_brief(
                self.REAL_ARTIFACT.read_text(), source_name=self.REAL_ARTIFACT.name
            )
        )

        loaded = load_brief_file(path)

        assert "Refuted" not in loaded
        assert len(loaded) > 1000

    @pytest.mark.parametrize(
        "sample",
        _sample_artifacts()
        or [
            pytest.param(
                None,
                marks=pytest.mark.skip(
                    reason="docs/research/samples/ holds no *.html — see B-038: the tool is not "
                    "yet proven against an owner-supplied artifact"
                ),
            )
        ],
        ids=lambda p: p.name if p else "no-sample",
    )
    def test_owner_supplied_samples_convert_without_losing_content(
        self, sample: Path
    ) -> None:
        html = sample.read_text()

        brief = build_brief(html, source_name=sample.name)

        missing = content_words(html) - words(brief)
        assert not missing, f"conversion dropped: {sorted(missing)}"


class TestHtmlToMarkdownDirectly:
    """``html_to_markdown`` is the body converter — no title, no Refuted section."""

    def test_returns_body_markdown_without_the_brief_scaffolding(self) -> None:
        body = html_to_markdown("<h2>Section</h2><p>Prose.</p>")

        assert "Section" in body
        assert "Prose." in body
        assert REFUTED_HEADING not in body


# ═══════════════════════════════════════════════════════════════════════════
# Proof of teeth for the no-drop invariant (B-043)
# ═══════════════════════════════════════════════════════════════════════════


class TestTheNoDropInvariantHasTeeth:
    """The third of the three mutations run by hand on 2026-08-01, recorded here
    so it stops living in shell history (B-043).

    `TestNothingSilentlyDropped` above is this converter's most important sensor:
    it is the only thing standing between a research brief and silently losing a
    paragraph on its way to the writer, and a lost paragraph is invisible
    downstream — the article simply never mentions it.

    A test that asserts an invariant holds says nothing about whether it would
    *notice* the invariant breaking. So this class breaks it on purpose. Adding
    `table` to `CHROME_TAGS` makes the converter discard tabular content, and the
    invariant must report the loss; the hand-run version of this reported 48 lost
    words.

    This is why `content_words()` computes the expected set from `SPEC_CHROME_TAGS`
    hardcoded in this file rather than importing `CHROME_TAGS` from the module. If
    it imported it, the expectation would move with the mutation and the whole
    check would pass while content vanished — a sensor calibrated against the thing
    it is measuring.
    """

    def test_dropping_a_content_tag_is_reported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        html = read_fixture("table_bearing")
        monkeypatch.setattr(
            html_to_brief, "CHROME_TAGS", (*SPEC_CHROME_TAGS, "table", "tbody", "tr")
        )

        out = words(build_brief(html, source_name="table_bearing.html"))

        missing = content_words(html) - out
        assert missing, (
            "CHROME_TAGS now discards tables, so the invariant must report the "
            "lost words — it did not, which means it could not have caught this"
        )

    def test_the_same_fixture_is_clean_unmutated(self) -> None:
        """The control. Without it the assertion above would also pass against an
        invariant that reports losses unconditionally."""
        html = read_fixture("table_bearing")

        out = words(build_brief(html, source_name="table_bearing.html"))

        assert not content_words(html) - out

    def test_the_runtime_check_reports_a_loss(self) -> None:
        """`find_dropped_words` runs on every real conversion, not only in tests.
        Feed it a markdown rendering with content removed and it must say so."""
        html = read_fixture("headings_and_prose")
        markdown = build_brief(html, source_name="headings_and_prose.html")

        truncated = "\n".join(markdown.splitlines()[:3])

        assert html_to_brief.find_dropped_words(html, truncated)

    def test_the_runtime_check_is_silent_on_a_faithful_conversion(self) -> None:
        html = read_fixture("headings_and_prose")
        markdown = build_brief(html, source_name="headings_and_prose.html")

        assert not html_to_brief.find_dropped_words(html, markdown)
