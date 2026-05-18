"""Direct unit tests for src/quality/agent_reviewer.py (issue #376).

Existing tests/test_quality_system.py exercises ``review_agent_output`` with
"writer_agent" and "research_agent" only, covering happy paths. This file
complements it with tests for the uncovered branches:

- All issue-emitting paths of ``review_research_output``
- YAML / front-matter error paths of ``review_writer_output``
- The full ``review_editor_output`` method
- The full ``review_graphics_output`` method
- The editor / graphics / unknown-agent dispatch arms of ``review_agent_output``
- ``generate_review_report`` severity classification + empty-issues path
"""

from __future__ import annotations

import pytest

from src.quality.agent_reviewer import AgentReviewer, review_agent_output


@pytest.fixture
def reviewer() -> AgentReviewer:
    return AgentReviewer()


# ---------------------------------------------------------------------------
# AgentReviewer.__init__ + load_standards
# ---------------------------------------------------------------------------


def test_init_loads_banned_pattern_lists(reviewer: AgentReviewer) -> None:
    assert reviewer.banned_openings, "banned_openings should be populated"
    assert reviewer.banned_phrases, "banned_phrases should be populated"
    assert reviewer.banned_closings, "banned_closings should be populated"


def test_init_with_custom_standards_path_stores_it(tmp_path) -> None:
    """Custom path is stored even though load_standards is hardcoded."""
    custom = tmp_path / "standards.md"
    r = AgentReviewer(standards_file=custom)
    assert r.standards_file == custom


# ---------------------------------------------------------------------------
# review_research_output — issue-emitting branches
# ---------------------------------------------------------------------------


def test_research_missing_required_field_emits_critical(
    reviewer: AgentReviewer,
) -> None:
    is_valid, issues = reviewer.review_research_output({"headline_stat": {}})
    assert is_valid is False
    assert any("Missing required field 'data_points'" in i for i in issues)


def test_research_headline_stat_not_dict_emits_critical(
    reviewer: AgentReviewer,
) -> None:
    is_valid, issues = reviewer.review_research_output(
        {"headline_stat": "a string", "data_points": []},
    )
    assert is_valid is False
    assert any("headline_stat must be an object" in i for i in issues)


def test_research_headline_stat_missing_source_emits_critical(
    reviewer: AgentReviewer,
) -> None:
    is_valid, issues = reviewer.review_research_output(
        {
            "headline_stat": {"value": "80%", "verified": True},
            "data_points": [],
        },
    )
    assert is_valid is False
    assert any("headline_stat missing named source" in i for i in issues)


def test_research_headline_stat_missing_verified_emits_critical(
    reviewer: AgentReviewer,
) -> None:
    is_valid, issues = reviewer.review_research_output(
        {
            "headline_stat": {"value": "80%", "source": "Tricentis"},
            "data_points": [],
        },
    )
    assert is_valid is False
    assert any("headline_stat missing verification flag" in i for i in issues)


def test_research_data_point_missing_source_emits_critical(
    reviewer: AgentReviewer,
) -> None:
    is_valid, issues = reviewer.review_research_output(
        {
            "headline_stat": {"source": "X", "verified": True},
            "data_points": [
                {"stat": "10%", "verified": True},  # no source
            ],
        },
    )
    assert is_valid is False
    assert any("Data point 1 missing named source" in i for i in issues)


def test_research_data_point_with_generic_source_emits_banned(
    reviewer: AgentReviewer,
) -> None:
    is_valid, issues = reviewer.review_research_output(
        {
            "headline_stat": {"source": "X", "verified": True},
            "data_points": [
                {"stat": "10%", "source": "Studies show", "verified": True},
            ],
        },
    )
    assert is_valid is False
    assert any("BANNED" in i and "generic source 'Studies show'" in i for i in issues)


def test_research_low_verification_rate_emits_warning(
    reviewer: AgentReviewer,
) -> None:
    """Below 90% verified data points → WARNING, but is_valid still False."""
    is_valid, issues = reviewer.review_research_output(
        {
            "headline_stat": {"source": "X", "verified": True},
            "data_points": [
                {"stat": "10%", "source": "A", "verified": True},
                {"stat": "20%", "source": "B", "verified": True},
                {"stat": "30%", "source": "C", "verified": False},
            ],
        },
    )
    assert is_valid is False
    assert any("Verification rate 67%" in i and "WARNING" in i for i in issues)


def test_research_chart_missing_required_field_emits_critical(
    reviewer: AgentReviewer,
) -> None:
    is_valid, issues = reviewer.review_research_output(
        {
            "headline_stat": {"source": "X", "verified": True},
            "data_points": [
                {"stat": "1", "source": "A", "verified": True},
            ],
            "chart_data": {"title": "ok"},  # missing 'data'
        },
    )
    assert is_valid is False
    assert any("Chart missing required field 'data'" in i for i in issues)


def test_research_fully_valid_returns_clean(reviewer: AgentReviewer) -> None:
    is_valid, issues = reviewer.review_research_output(
        {
            "headline_stat": {"source": "Tricentis", "verified": True},
            "data_points": [
                {"stat": "50%", "source": "Gartner", "verified": True},
            ],
        },
    )
    assert is_valid is True
    assert issues == []


# ---------------------------------------------------------------------------
# review_writer_output — YAML / front-matter error paths
# ---------------------------------------------------------------------------


def test_writer_no_front_matter_emits_critical_and_returns_early(
    reviewer: AgentReviewer,
) -> None:
    is_valid, issues = reviewer.review_writer_output("no front matter at all")
    assert is_valid is False
    # Early return — should contain ONLY the FM-missing issue
    assert issues == ["CRITICAL: No YAML front matter found"]


def test_writer_invalid_yaml_emits_critical_and_returns_early(
    reviewer: AgentReviewer,
) -> None:
    # Unclosed quote produces YAMLError
    bad_yaml = '---\ntitle: "unterminated\n---\n\nbody'
    is_valid, issues = reviewer.review_writer_output(bad_yaml)
    assert is_valid is False
    assert len(issues) == 1
    assert issues[0].startswith("CRITICAL: Invalid YAML front matter:")


def test_writer_generic_title_pattern_emits_warning(
    reviewer: AgentReviewer,
) -> None:
    article = (
        "---\n"
        "layout: post\n"
        'title: "The Ultimate Guide to Software Testing"\n'
        "date: 2026-01-01\n"
        'categories: ["Quality"]\n'
        'description: "A guide"\n'
        "---\n\n" + ("word " * 800)
    )
    _, issues = reviewer.review_writer_output(article)
    assert any("Generic title pattern" in i and "ultimate guide" in i for i in issues)


def test_writer_categories_not_list_emits_critical(reviewer: AgentReviewer) -> None:
    article = (
        "---\n"
        "layout: post\n"
        'title: "A Real Title With Four Words"\n'
        "date: 2026-01-01\n"
        'categories: "not a list"\n'
        'description: "desc"\n'
        "---\n\n" + ("word " * 800)
    )
    _, issues = reviewer.review_writer_output(article)
    assert any("categories must be an array" in i for i in issues)


def test_writer_categories_empty_list_emits_critical(reviewer: AgentReviewer) -> None:
    article = (
        "---\n"
        "layout: post\n"
        'title: "A Real Title With Four Words"\n'
        "date: 2026-01-01\n"
        "categories: []\n"
        'description: "desc"\n'
        "---\n\n" + ("word " * 800)
    )
    _, issues = reviewer.review_writer_output(article)
    assert any("categories array is empty" in i for i in issues)


def test_writer_article_too_long_emits_warning(reviewer: AgentReviewer) -> None:
    """word_count > 1500 → WARNING (not CRITICAL — over-long is softer)."""
    article = (
        "---\n"
        "layout: post\n"
        'title: "A Real Title With Four Words"\n'
        "date: 2026-01-01\n"
        'categories: ["Quality"]\n'
        'description: "desc"\n'
        "---\n\n" + ("word " * 1600)  # 1600 words → over limit
    )
    _, issues = reviewer.review_writer_output(article)
    assert any("Article too long" in i and "1600 words" in i for i in issues)


# ---------------------------------------------------------------------------
# review_editor_output — full method (was 0% covered)
# ---------------------------------------------------------------------------


def test_editor_clean_article_passes(reviewer: AgentReviewer) -> None:
    article = (
        "---\n"
        'title: "test"\n'
        "---\n\n"
        "A perfectly clean edited body with no banned content."
    )
    is_valid, issues = reviewer.review_editor_output(article)
    assert is_valid is True
    assert issues == []


def test_editor_verification_flags_remaining_emits_critical(
    reviewer: AgentReviewer,
) -> None:
    article = "---\nx: 1\n---\n\nBody with [NEEDS SOURCE] left in."
    is_valid, issues = reviewer.review_editor_output(article)
    assert is_valid is False
    assert any("Editor failed to remove verification flags" in i for i in issues)


def test_editor_unverified_flag_remaining_emits_critical(
    reviewer: AgentReviewer,
) -> None:
    article = "---\nx: 1\n---\n\nBody with [UNVERIFIED] still here."
    _, issues = reviewer.review_editor_output(article)
    assert any("Editor failed to remove verification flags" in i for i in issues)


def test_editor_banned_opening_pattern_emits_critical(
    reviewer: AgentReviewer,
) -> None:
    article = (
        "---\n"
        'title: "x"\n'
        "---\n\n"
        "In today's fast-paced world of testing, much is happening."
    )
    is_valid, issues = reviewer.review_editor_output(article)
    assert is_valid is False
    assert any(
        "Editor failed to remove banned pattern" in i and "today's" in i.lower()
        for i in issues
    )


def test_editor_banned_phrase_emits_critical(reviewer: AgentReviewer) -> None:
    article = "---\nx: 1\n---\n\nThis is a real game-changer for the industry."
    _, issues = reviewer.review_editor_output(article)
    assert any(
        "Editor failed to remove banned pattern" in i and "game-changer" in i
        for i in issues
    )


def test_editor_banned_closing_emits_critical(reviewer: AgentReviewer) -> None:
    article = "---\nx: 1\n---\n\nSome body. In conclusion, this is important."
    _, issues = reviewer.review_editor_output(article)
    assert any(
        "Editor failed to remove banned pattern" in i and "conclusion" in i
        for i in issues
    )


def test_editor_no_front_matter_treats_full_text_as_empty_body(
    reviewer: AgentReviewer,
) -> None:
    """If there are <2 '---' markers, body is empty — nothing to flag."""
    is_valid, issues = reviewer.review_editor_output("plain text no fm")
    assert is_valid is True
    assert issues == []


# ---------------------------------------------------------------------------
# review_graphics_output — full method (was 0% covered)
# ---------------------------------------------------------------------------


def test_graphics_fully_valid_spec_passes(reviewer: AgentReviewer) -> None:
    spec = {
        "title": "Concise chart title",
        "data": [{"x": 1}, {"x": 2}, {"x": 3}, {"x": 4}],
        "source_line": "Source: Tricentis 2026",
    }
    is_valid, issues = reviewer.review_graphics_output(spec)
    assert is_valid is True
    assert issues == []


def test_graphics_missing_title_emits_critical(reviewer: AgentReviewer) -> None:
    _, issues = reviewer.review_graphics_output(
        {"data": [1, 2, 3, 4], "source_line": "src"},
    )
    assert any("Chart spec missing 'title'" in i for i in issues)


def test_graphics_missing_data_emits_critical(reviewer: AgentReviewer) -> None:
    _, issues = reviewer.review_graphics_output(
        {"title": "ok", "source_line": "src"},
    )
    assert any("Chart spec missing 'data'" in i for i in issues)


def test_graphics_title_too_long_emits_warning(reviewer: AgentReviewer) -> None:
    long_title = "x" * 51
    _, issues = reviewer.review_graphics_output(
        {"title": long_title, "data": [1, 2, 3, 4], "source_line": "src"},
    )
    assert any("Chart title too long" in i and "51 chars" in i for i in issues)


def test_graphics_too_few_data_points_emits_warning(
    reviewer: AgentReviewer,
) -> None:
    _, issues = reviewer.review_graphics_output(
        {"title": "ok", "data": [1, 2], "source_line": "src"},
    )
    assert any("<3 data points" in i for i in issues)


def test_graphics_missing_source_line_emits_warning(
    reviewer: AgentReviewer,
) -> None:
    _, issues = reviewer.review_graphics_output(
        {"title": "ok", "data": [1, 2, 3, 4]},
    )
    assert any("missing source attribution line" in i for i in issues)


# ---------------------------------------------------------------------------
# generate_review_report — severity classification + empty-issues path
# ---------------------------------------------------------------------------


def test_report_no_issues_renders_passed_status(reviewer: AgentReviewer) -> None:
    report = reviewer.generate_review_report("writer_agent", True, [])
    assert "PASSED" in report
    assert "Issues Found: 0" in report
    assert "No issues detected" in report


def test_report_classifies_critical_banned_and_warning(
    reviewer: AgentReviewer,
) -> None:
    issues = [
        "CRITICAL: bad thing",
        "BANNED: forbidden phrase used",
        "WARNING: minor thing",
    ]
    report = reviewer.generate_review_report("writer_agent", False, issues)
    assert "FAILED" in report
    assert "Issues Found: 3" in report
    assert "[CRITICAL]" in report
    assert "[BANNED]" in report
    assert "[WARNING]" in report


def test_report_unrecognized_severity_falls_back_to_warning(
    reviewer: AgentReviewer,
) -> None:
    """Issue strings with no CRITICAL/BANNED prefix → labelled WARNING."""
    report = reviewer.generate_review_report(
        "writer_agent",
        False,
        ["something opaque happened"],
    )
    assert "[WARNING] something opaque happened" in report


# ---------------------------------------------------------------------------
# review_agent_output — dispatch arms (editor / graphics / unknown)
# ---------------------------------------------------------------------------


def test_dispatch_editor_agent_invokes_editor_review(
    capsys: pytest.CaptureFixture[str],
) -> None:
    article = "---\nx: 1\n---\n\nClean editor body."
    is_valid, issues = review_agent_output("editor_agent", article)
    assert is_valid is True
    assert issues == []
    # Report should have been printed
    assert "editor_agent" in capsys.readouterr().out


def test_dispatch_graphics_agent_invokes_graphics_review(
    capsys: pytest.CaptureFixture[str],
) -> None:
    spec = {
        "title": "ok",
        "data": [1, 2, 3, 4],
        "source_line": "Source: X 2026",
    }
    is_valid, issues = review_agent_output("graphics_agent", spec)
    assert is_valid is True
    assert issues == []
    assert "graphics_agent" in capsys.readouterr().out


def test_dispatch_unknown_agent_returns_false_with_explanatory_issue(
    capsys: pytest.CaptureFixture[str],
) -> None:
    is_valid, issues = review_agent_output("mystery_agent", {})
    assert is_valid is False
    assert issues == ["Unknown agent type: mystery_agent"]
    # Unknown branch returns BEFORE the print — capsys should show no report header
    assert "AUTOMATED REVIEW" not in capsys.readouterr().out


def test_dispatch_research_agent_invokes_research_review(
    capsys: pytest.CaptureFixture[str],
) -> None:
    research_data = {
        "headline_stat": {"value": "80%", "source": "Gartner", "verified": True},
        "data_points": [
            {"stat": "50%", "source": "Forrester", "verified": True},
        ],
    }
    is_valid, issues = review_agent_output("research_agent", research_data)
    assert is_valid is True
    assert issues == []
    assert "research_agent" in capsys.readouterr().out


def test_dispatch_writer_agent_passes_chart_filename_context(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify the context dict's chart_filename is forwarded to review_writer_output."""
    article = (
        "---\n"
        "layout: post\n"
        'title: "A Real Title With Four Words"\n'
        "date: 2026-01-01\n"
        'categories: ["Quality"]\n'
        'description: "desc"\n'
        "---\n\n" + ("word " * 800)
        # body has no chart embed — should flag the missing chart
    )
    is_valid, issues = review_agent_output(
        "writer_agent",
        article,
        context={"chart_filename": "expected.png"},
    )
    capsys.readouterr()  # drain captured output
    assert is_valid is False
    assert any("Chart not embedded" in i and "expected.png" in i for i in issues)


def test_dispatch_writer_agent_with_none_context_uses_empty_dict(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """context=None should be treated as {} (no chart_filename → no chart checks)."""
    article = (
        "---\n"
        "layout: post\n"
        'title: "A Real Title With Four Words"\n'
        "date: 2026-01-01\n"
        'categories: ["Quality"]\n'
        'description: "desc"\n'
        "---\n\n" + ("word " * 800)
    )
    is_valid, issues = review_agent_output("writer_agent", article)
    capsys.readouterr()
    # No chart checks should appear in issues
    assert not any("Chart" in i for i in issues)
    assert is_valid is True
