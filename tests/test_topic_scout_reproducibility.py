"""Tests for scripts/topic_scout_reproducibility.py.

All tests are hermetic — no live LLM calls and no filesystem side-effects
other than pytest's ``tmp_path`` fixture.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make scripts/ importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from topic_scout_reproducibility import (  # noqa: E402
    _cosine_similarity,
    _compute_tf,
    _extract_topic_text,
    _extract_top_performer_keywords,
    _normalise_title,
    _tokenize,
    compute_jaccard_matrix,
    compute_score_stats,
    compute_thematic_stability,
    compute_tfidf_cosine_matrix,
    compute_title_jaccard,
    detect_outlier_runs,
    format_jaccard_matrix,
    generate_report,
    mean_pairwise_jaccard,
    mean_pairwise_similarity,
    run_reproducibility_check,
)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _make_topic(n: int, score: int = 20) -> dict:
    """Build a minimal topic dict that mirrors scout_topics() output."""
    return {
        "topic": f"Topic {n}",
        "hook": f"Hook for topic {n}",
        "thesis": "Thesis text",
        "data_sources": [],
        "timeliness_trigger": "Now",
        "contrarian_angle": "Contrarian view",
        "title_ideas": [],
        "scores": {
            "timeliness": 4,
            "data_availability": 4,
            "contrarian_potential": 4,
            "audience_fit": 4,
            "economist_fit": 4,
        },
        "total_score": score,
        "talking_points": "points",
    }


@pytest.fixture()
def sample_report_kwargs() -> dict:
    """Keyword arguments for ``generate_report`` that cover all branches."""
    return {
        "n_requested": 3,
        "successful_runs": 2,
        "failed_runs": 1,
        "model": "gpt-4o",
        "perf_context": "## Performance Context\n\nSome data\n",
        "top_performer_titles": ["Great Article"],
        "runs_topics": [
            [{"topic": "AI Testing", "hook": "AI is great", "total_score": 21}],
            [{"topic": "Flaky Tests", "hook": "Flakiness hurts", "total_score": 19}],
        ],
        "run_timings": [5.0, 6.0],
        "cosine_matrix": [[1.0, 0.2], [0.2, 1.0]],
        "mean_cosine": 0.2,
        "jaccard_matrix": [[1.0, 0.3], [0.3, 1.0]],
        "mean_jaccard": 0.3,
        "thematic_stability": {"Great Article": 0.5},
        "score_stats": {
            "all_scores": [21.0, 19.0],
            "overall_mean": 20.0,
            "overall_std": 1.0,
            "per_run_mean": [21.0, 19.0],
            "per_run_std": [0.0, 0.0],
        },
        "outlier_run_indices": [],
        "timestamp": "2026-04-06T12:00:00",
    }


# ──────────────────────────────────────────────────────────────────────────────
# _normalise_title
# ──────────────────────────────────────────────────────────────────────────────


def test_normalise_strips_punctuation() -> None:
    result = _normalise_title("AI/ML Testing: The Future?")
    assert "ai" in result
    assert "ml" in result
    assert "testing" in result
    assert "future" in result
    for token in result:
        assert ":" not in token
        assert "?" not in token
        assert "/" not in token


def test_normalise_removes_stop_words() -> None:
    result = _normalise_title("The Art of Testing")
    assert "the" not in result
    assert "of" not in result
    assert "art" in result
    assert "testing" in result


def test_normalise_empty_string_returns_empty_frozenset() -> None:
    assert _normalise_title("") == frozenset()


# ──────────────────────────────────────────────────────────────────────────────
# compute_title_jaccard
# ──────────────────────────────────────────────────────────────────────────────


def test_jaccard_identical_lists_is_one() -> None:
    titles = ["AI Testing Revolution", "Flaky Tests Hidden Tax"]
    assert compute_title_jaccard(titles, titles) == pytest.approx(1.0)


def test_jaccard_completely_different_is_low() -> None:
    # Words from one list should not appear in the other.
    a = ["Zymurgy Fermentation Techniques"]
    b = ["Quantum Chromodynamics Breakthroughs"]
    score = compute_title_jaccard(a, b)
    assert 0.0 <= score < 0.3


def test_jaccard_partial_overlap_is_between_zero_and_one() -> None:
    a = ["AI Testing Revolution"]
    b = ["AI Performance Testing Guide"]
    score = compute_title_jaccard(a, b)
    assert 0.0 < score < 1.0


def test_jaccard_empty_lists_returns_zero() -> None:
    assert compute_title_jaccard([], []) == pytest.approx(0.0)


def test_jaccard_one_empty_list_returns_zero() -> None:
    assert compute_title_jaccard(["Some Topic"], []) == pytest.approx(0.0)


# ──────────────────────────────────────────────────────────────────────────────
# compute_jaccard_matrix
# ──────────────────────────────────────────────────────────────────────────────


def test_jaccard_matrix_diagonal_is_one() -> None:
    runs = [
        [{"topic": "Topic Alpha"}, {"topic": "Topic Beta"}],
        [{"topic": "Topic Gamma"}, {"topic": "Topic Delta"}],
    ]
    matrix = compute_jaccard_matrix(runs)
    assert matrix[0][0] == pytest.approx(1.0)
    assert matrix[1][1] == pytest.approx(1.0)


def test_jaccard_matrix_is_symmetric() -> None:
    runs = [
        [{"topic": "AI Testing"}, {"topic": "Flaky Tests"}],
        [{"topic": "Performance Engineering"}, {"topic": "Shift Left"}],
        [{"topic": "AI Quality"}, {"topic": "Testing Trends"}],
    ]
    matrix = compute_jaccard_matrix(runs)
    n = len(matrix)
    for i in range(n):
        for j in range(n):
            assert matrix[i][j] == pytest.approx(matrix[j][i], abs=1e-9)


def test_jaccard_matrix_shape() -> None:
    runs = [[{"topic": "T"}] for _ in range(4)]
    matrix = compute_jaccard_matrix(runs)
    assert len(matrix) == 4
    assert all(len(row) == 4 for row in matrix)


def test_jaccard_matrix_single_run_gives_1x1() -> None:
    matrix = compute_jaccard_matrix([[{"topic": "Solo Topic"}]])
    assert len(matrix) == 1
    assert len(matrix[0]) == 1
    assert matrix[0][0] == pytest.approx(1.0)


def test_jaccard_matrix_empty_input_gives_empty() -> None:
    assert compute_jaccard_matrix([]) == []


# ──────────────────────────────────────────────────────────────────────────────
# mean_pairwise_similarity (and backward-compat alias mean_pairwise_jaccard)
# ──────────────────────────────────────────────────────────────────────────────


def test_mean_pairwise_returns_zero_for_single_run() -> None:
    assert mean_pairwise_similarity([[1.0]]) == pytest.approx(0.0)


def test_mean_pairwise_returns_zero_for_empty_matrix() -> None:
    assert mean_pairwise_similarity([]) == pytest.approx(0.0)


def test_mean_pairwise_on_known_matrix() -> None:
    # 2×2 with off-diagonal = 0.5
    matrix = [[1.0, 0.5], [0.5, 1.0]]
    assert mean_pairwise_similarity(matrix) == pytest.approx(0.5)


def test_mean_pairwise_3x3_symmetric() -> None:
    matrix = [
        [1.0, 0.6, 0.4],
        [0.6, 1.0, 0.8],
        [0.4, 0.8, 1.0],
    ]
    result = mean_pairwise_similarity(matrix)
    # Off-diagonal values: 0.6, 0.4, 0.6, 0.8, 0.4, 0.8 → mean = 0.6
    assert result == pytest.approx(0.6)


def test_mean_pairwise_jaccard_alias_works() -> None:
    """Backward-compat alias resolves to the same function."""
    matrix = [[1.0, 0.5], [0.5, 1.0]]
    assert mean_pairwise_jaccard(matrix) == mean_pairwise_similarity(matrix)


# ──────────────────────────────────────────────────────────────────────────────
# _extract_top_performer_keywords
# ──────────────────────────────────────────────────────────────────────────────


def test_extract_top_performers_from_context() -> None:
    context = (
        "## Performance Context\n\n"
        "Over the last 30 days ...\n\n"
        "### Top performers (build on what's working)\n\n"
        "| Score | Pageviews | Title |\n"
        "|-------|-----------|-------|\n"
        "| 0.900 | 500 | Great Article About Testing |\n"
        "| 0.800 | 400 | Platform Engineering Guide |\n"
        "| 0.750 | 300 | AI in Quality Engineering |\n\n"
        "### Underperformers ...\n"
    )
    titles = _extract_top_performer_keywords(context, top_n=3)
    assert len(titles) == 3
    assert "Great Article About Testing" in titles
    assert "Platform Engineering Guide" in titles


def test_extract_honours_top_n_limit() -> None:
    context = (
        "### Top performers (build on what's working)\n\n"
        "| Score | Pageviews | Title |\n"
        "|-------|-----------|-------|\n"
        "| 0.9 | 100 | Article One |\n"
        "| 0.8 | 90 | Article Two |\n"
        "| 0.7 | 80 | Article Three |\n"
        "| 0.6 | 70 | Article Four |\n"
    )
    titles = _extract_top_performer_keywords(context, top_n=2)
    assert len(titles) == 2


def test_extract_returns_empty_when_no_top_section() -> None:
    context = "## Performance Context\n\n_No data available._\n"
    assert _extract_top_performer_keywords(context) == []


# ──────────────────────────────────────────────────────────────────────────────
# compute_thematic_stability
# ──────────────────────────────────────────────────────────────────────────────


def test_thematic_stability_full_match() -> None:
    runs = [
        [{"topic": "AI Testing Revolution", "hook": "AI changes testing"}],
        [{"topic": "AI Platform Engineering", "hook": "AI everywhere"}],
    ]
    stability = compute_thematic_stability(runs, ["AI Quality Engineering"])
    # "ai" should match both runs.
    assert stability["AI Quality Engineering"] == pytest.approx(1.0)


def test_thematic_stability_no_match() -> None:
    runs = [
        [{"topic": "Database Indexing Techniques", "hook": "SQL is back"}],
    ]
    stability = compute_thematic_stability(runs, ["Quantum Computing Future"])
    # "quantum", "computing", "future" appear in neither title nor hook.
    assert stability["Quantum Computing Future"] == pytest.approx(0.0)


def test_thematic_stability_partial_match() -> None:
    runs = [
        [{"topic": "AI Testing", "hook": "AI is useful"}],
        [{"topic": "Manual Testing Still Works", "hook": "humans matter"}],
    ]
    stability = compute_thematic_stability(runs, ["AI Quality"])
    # Only run 0 mentions "ai".
    assert stability["AI Quality"] == pytest.approx(0.5)


def test_thematic_stability_empty_runs() -> None:
    assert compute_thematic_stability([], ["Some Title"]) == {}


def test_thematic_stability_empty_top_titles() -> None:
    runs = [[{"topic": "T1", "hook": "h1"}]]
    assert compute_thematic_stability(runs, []) == {}


# ──────────────────────────────────────────────────────────────────────────────
# compute_score_stats
# ──────────────────────────────────────────────────────────────────────────────


def test_score_stats_basic() -> None:
    runs = [
        [{"total_score": 20}, {"total_score": 22}, {"total_score": 18}],
        [{"total_score": 21}, {"total_score": 19}, {"total_score": 20}],
    ]
    stats = compute_score_stats(runs)
    assert stats["overall_mean"] == pytest.approx(20.0)
    assert len(stats["per_run_mean"]) == 2
    assert stats["per_run_mean"][0] == pytest.approx(20.0)
    assert stats["per_run_mean"][1] == pytest.approx(20.0)


def test_score_stats_empty_runs() -> None:
    stats = compute_score_stats([])
    assert stats["overall_mean"] == pytest.approx(0.0)
    assert stats["overall_std"] == pytest.approx(0.0)
    assert stats["per_run_mean"] == []
    assert stats["per_run_std"] == []


def test_score_stats_single_run_single_topic() -> None:
    stats = compute_score_stats([[{"total_score": 15}]])
    assert stats["overall_mean"] == pytest.approx(15.0)
    assert stats["per_run_std"][0] == pytest.approx(0.0)


# ──────────────────────────────────────────────────────────────────────────────
# detect_outlier_runs
# ──────────────────────────────────────────────────────────────────────────────


def test_detect_outliers_needs_three_runs() -> None:
    matrix = [[1.0, 0.5], [0.5, 1.0]]
    assert detect_outlier_runs(matrix) == []


def test_detect_outliers_identifies_divergent_run() -> None:
    # Run 2 is totally different from Runs 0 and 1.
    matrix = [
        [1.0, 0.9, 0.1],
        [0.9, 1.0, 0.1],
        [0.1, 0.1, 1.0],
    ]
    outliers = detect_outlier_runs(matrix)
    assert 2 in outliers


def test_detect_no_outliers_when_all_similar() -> None:
    matrix = [
        [1.0, 0.8, 0.9],
        [0.8, 1.0, 0.85],
        [0.9, 0.85, 1.0],
    ]
    assert detect_outlier_runs(matrix) == []


def test_detect_outliers_empty_matrix() -> None:
    assert detect_outlier_runs([]) == []


# ──────────────────────────────────────────────────────────────────────────────
# format_jaccard_matrix
# ──────────────────────────────────────────────────────────────────────────────


def test_format_jaccard_matrix_contains_labels() -> None:
    matrix = [[1.0, 0.5], [0.5, 1.0]]
    labels = ["Run 1", "Run 2"]
    rendered = format_jaccard_matrix(matrix, labels)
    assert "Run 1" in rendered
    assert "Run 2" in rendered
    assert "0.500" in rendered
    assert "1.000" in rendered


def test_format_jaccard_matrix_correct_row_count() -> None:
    matrix = [[1.0, 0.4, 0.6], [0.4, 1.0, 0.7], [0.6, 0.7, 1.0]]
    labels = ["Run 1", "Run 2", "Run 3"]
    rendered = format_jaccard_matrix(matrix, labels)
    # Header + separator + 3 data rows = 5 lines.
    assert rendered.count("\n") == 4


# ──────────────────────────────────────────────────────────────────────────────
# generate_report
# ──────────────────────────────────────────────────────────────────────────────


def test_generate_report_unstable_verdict(sample_report_kwargs: dict) -> None:
    report = generate_report(**sample_report_kwargs)
    assert "## Verdict" in report
    assert "UNSTABLE" in report  # mean_cosine=0.2 < threshold (0.25)


def test_generate_report_reproducible_verdict(sample_report_kwargs: dict) -> None:
    kwargs = dict(sample_report_kwargs)
    kwargs["mean_cosine"] = 0.8  # primary metric drives verdict
    report = generate_report(**kwargs)
    assert "REPRODUCIBLE" in report


def test_generate_report_contains_jaccard_matrix(sample_report_kwargs: dict) -> None:
    report = generate_report(**sample_report_kwargs)
    assert "Lexical Similarity Matrix (Jaccard)" in report
    assert "0.300" in report


def test_generate_report_contains_cosine_matrix(sample_report_kwargs: dict) -> None:
    report = generate_report(**sample_report_kwargs)
    assert "TF-IDF Cosine Similarity Matrix" in report
    assert "0.200" in report


def test_generate_report_contains_model_name(sample_report_kwargs: dict) -> None:
    report = generate_report(**sample_report_kwargs)
    assert "gpt-4o" in report


def test_generate_report_contains_thematic_stability(
    sample_report_kwargs: dict,
) -> None:
    report = generate_report(**sample_report_kwargs)
    assert "Thematic Stability" in report
    assert "Great Article" in report


def test_generate_report_insufficient_runs_message(
    sample_report_kwargs: dict,
) -> None:
    kwargs = dict(sample_report_kwargs)
    kwargs["successful_runs"] = 1
    kwargs["runs_topics"] = [
        [{"topic": "Only Topic", "hook": "Only hook", "total_score": 20}]
    ]
    kwargs["run_timings"] = [4.0]
    kwargs["cosine_matrix"] = []
    kwargs["mean_cosine"] = 0.0
    kwargs["jaccard_matrix"] = []
    kwargs["mean_jaccard"] = 0.0
    kwargs["thematic_stability"] = {}
    kwargs["score_stats"] = {
        "all_scores": [20.0],
        "overall_mean": 20.0,
        "overall_std": 0.0,
        "per_run_mean": [20.0],
        "per_run_std": [0.0],
    }
    kwargs["outlier_run_indices"] = []
    report = generate_report(**kwargs)
    assert "Insufficient successful runs" in report


def test_generate_report_with_zero_successful_runs(
    sample_report_kwargs: dict,
) -> None:
    kwargs = dict(sample_report_kwargs)
    kwargs["successful_runs"] = 0
    kwargs["runs_topics"] = []
    kwargs["run_timings"] = []
    kwargs["cosine_matrix"] = []
    kwargs["mean_cosine"] = 0.0
    kwargs["jaccard_matrix"] = []
    kwargs["mean_jaccard"] = 0.0
    kwargs["thematic_stability"] = {}
    kwargs["score_stats"] = {
        "all_scores": [],
        "overall_mean": 0.0,
        "overall_std": 0.0,
        "per_run_mean": [],
        "per_run_std": [],
    }
    kwargs["outlier_run_indices"] = []
    report = generate_report(**kwargs)
    assert "Topic Scout Reproducibility Report" in report
    assert "Insufficient successful runs" in report


def test_generate_report_outlier_section(sample_report_kwargs: dict) -> None:
    kwargs = dict(sample_report_kwargs)
    kwargs["successful_runs"] = 3
    kwargs["runs_topics"] = [
        [{"topic": "AI Testing", "hook": "hook", "total_score": 21}],
        [{"topic": "Flaky Tests", "hook": "hook", "total_score": 19}],
        [{"topic": "Quantum Zymurgy", "hook": "hook", "total_score": 10}],
    ]
    kwargs["run_timings"] = [5.0, 6.0, 7.0]
    kwargs["cosine_matrix"] = [
        [1.0, 0.9, 0.1],
        [0.9, 1.0, 0.1],
        [0.1, 0.1, 1.0],
    ]
    kwargs["mean_cosine"] = 0.4
    kwargs["jaccard_matrix"] = [
        [1.0, 0.9, 0.1],
        [0.9, 1.0, 0.1],
        [0.1, 0.1, 1.0],
    ]
    kwargs["outlier_run_indices"] = [2]
    kwargs["score_stats"] = {
        "all_scores": [21.0, 19.0, 10.0],
        "overall_mean": 16.7,
        "overall_std": 5.8,
        "per_run_mean": [21.0, 19.0, 10.0],
        "per_run_std": [0.0, 0.0, 0.0],
    }
    report = generate_report(**kwargs)
    assert "Run 3" in report
    assert "outlier" in report.lower()


# ──────────────────────────────────────────────────────────────────────────────
# run_reproducibility_check (integration — mocked LLM)
# ──────────────────────────────────────────────────────────────────────────────


def test_run_reproducibility_check_writes_report(tmp_path: Path) -> None:
    """Full integration test with mocked LLM calls."""
    topics_payload = [_make_topic(i) for i in range(5)]
    mock_client = MagicMock()
    mock_client.model = "gpt-4o-mock"

    with (
        patch(
            "topic_scout_reproducibility.get_performance_context"
        ) as mock_ctx,
        patch("topic_scout_reproducibility.scout_topics") as mock_scout,
    ):
        mock_ctx.return_value = "## Performance Context\n\nSome data\n"
        mock_scout.return_value = topics_payload

        report_path = run_reproducibility_check(
            n_runs=2, output_dir=tmp_path, client=mock_client
        )

    assert report_path.exists()
    report_text = report_path.read_text()
    assert "Topic Scout Reproducibility Report" in report_text
    assert "## Verdict" in report_text
    assert "gpt-4o-mock" in report_text

    # JSON companion file should also exist.
    json_path = report_path.with_suffix(".json")
    assert json_path.exists()


def test_run_reproducibility_check_counts_failed_run(tmp_path: Path) -> None:
    """A run returning empty topics is counted as a failure."""
    mock_client = MagicMock()
    mock_client.model = "gpt-4o"

    with (
        patch(
            "topic_scout_reproducibility.get_performance_context"
        ) as mock_ctx,
        patch("topic_scout_reproducibility.scout_topics") as mock_scout,
    ):
        mock_ctx.return_value = "## Performance Context\n\nSome data\n"
        # First call succeeds; second returns empty (simulates JSON failure).
        mock_scout.side_effect = [
            [_make_topic(i) for i in range(5)],
            [],
        ]

        report_path = run_reproducibility_check(
            n_runs=2, output_dir=tmp_path, client=mock_client
        )

    report_text = report_path.read_text()
    assert "Failed:** 1" in report_text


def test_run_reproducibility_check_handles_exception(tmp_path: Path) -> None:
    """A run that raises an exception is counted as a failure."""
    mock_client = MagicMock()
    mock_client.model = "gpt-4o"

    with (
        patch(
            "topic_scout_reproducibility.get_performance_context"
        ) as mock_ctx,
        patch("topic_scout_reproducibility.scout_topics") as mock_scout,
    ):
        mock_ctx.return_value = "## Performance Context\n\nSome data\n"
        mock_scout.side_effect = RuntimeError("API quota exceeded")

        report_path = run_reproducibility_check(
            n_runs=3, output_dir=tmp_path, client=mock_client
        )

    report_text = report_path.read_text()
    assert "Failed:** 3" in report_text


def test_run_reproducibility_check_creates_output_dir(tmp_path: Path) -> None:
    """The output directory is created if it does not exist."""
    mock_client = MagicMock()
    mock_client.model = "gpt-4o"
    nested = tmp_path / "deep" / "nested" / "output"

    with (
        patch(
            "topic_scout_reproducibility.get_performance_context"
        ) as mock_ctx,
        patch("topic_scout_reproducibility.scout_topics") as mock_scout,
    ):
        mock_ctx.return_value = "## Performance Context\n\nSome data\n"
        mock_scout.return_value = [_make_topic(i) for i in range(3)]

        run_reproducibility_check(n_runs=1, output_dir=nested, client=mock_client)

    assert nested.exists()


# ──────────────────────────────────────────────────────────────────────────────
# _tokenize
# ──────────────────────────────────────────────────────────────────────────────


def test_tokenize_splits_on_punctuation() -> None:
    tokens = _tokenize("AI/ML testing: future?")
    assert "ai" in tokens
    assert "ml" in tokens
    assert "testing" in tokens
    assert "future" in tokens


def test_tokenize_removes_stop_words() -> None:
    tokens = _tokenize("the art of testing")
    assert "the" not in tokens
    assert "of" not in tokens
    assert "art" in tokens


def test_tokenize_empty_string() -> None:
    assert _tokenize("") == []


def test_tokenize_returns_list_with_duplicates() -> None:
    tokens = _tokenize("testing testing one two testing")
    assert tokens.count("testing") == 3


# ──────────────────────────────────────────────────────────────────────────────
# _extract_topic_text
# ──────────────────────────────────────────────────────────────────────────────


def test_extract_topic_text_combines_fields() -> None:
    topic = {
        "topic": "AI Testing",
        "hook": "AI changes everything",
        "thesis": "Costs are hidden",
        "contrarian_angle": "Automation is oversold",
        "talking_points": "ROI metrics matter",
    }
    text = _extract_topic_text(topic)
    assert "AI Testing" in text
    assert "AI changes everything" in text
    assert "Costs are hidden" in text
    assert "Automation is oversold" in text
    assert "ROI metrics matter" in text


def test_extract_topic_text_skips_missing_fields() -> None:
    topic = {"topic": "Testing", "hook": "Test hook"}
    text = _extract_topic_text(topic)
    assert "Testing" in text
    assert "Test hook" in text


def test_extract_topic_text_empty_topic() -> None:
    assert _extract_topic_text({}) == ""


# ──────────────────────────────────────────────────────────────────────────────
# _compute_tf
# ──────────────────────────────────────────────────────────────────────────────


def test_compute_tf_basic() -> None:
    tf = _compute_tf(["a", "b", "a"])
    assert tf["a"] == pytest.approx(2 / 3)
    assert tf["b"] == pytest.approx(1 / 3)


def test_compute_tf_empty_returns_empty() -> None:
    assert _compute_tf([]) == {}


# ──────────────────────────────────────────────────────────────────────────────
# _cosine_similarity
# ──────────────────────────────────────────────────────────────────────────────


def test_cosine_similarity_identical_vectors() -> None:
    vec = {"a": 0.5, "b": 0.5}
    assert _cosine_similarity(vec, vec) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors() -> None:
    assert _cosine_similarity({"a": 1.0}, {"b": 1.0}) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector() -> None:
    assert _cosine_similarity({"a": 0.0}, {"a": 1.0}) == pytest.approx(0.0)


# ──────────────────────────────────────────────────────────────────────────────
# compute_tfidf_cosine_matrix
# ──────────────────────────────────────────────────────────────────────────────


def test_tfidf_matrix_diagonal_is_one() -> None:
    runs = [
        [_make_topic(0), _make_topic(1)],
        [_make_topic(2), _make_topic(3)],
    ]
    matrix = compute_tfidf_cosine_matrix(runs)
    assert matrix[0][0] == pytest.approx(1.0)
    assert matrix[1][1] == pytest.approx(1.0)


def test_tfidf_matrix_is_symmetric() -> None:
    runs = [
        [{"topic": "AI Testing ROI", "hook": "costs are hidden", "thesis": "t", "contrarian_angle": "c", "talking_points": "p"}],
        [{"topic": "Automation Myths", "hook": "maintenance burden", "thesis": "t", "contrarian_angle": "c", "talking_points": "p"}],
        [{"topic": "Developer Experience", "hook": "roi illusion", "thesis": "t", "contrarian_angle": "c", "talking_points": "p"}],
    ]
    matrix = compute_tfidf_cosine_matrix(runs)
    n = len(matrix)
    for i in range(n):
        for j in range(n):
            assert matrix[i][j] == pytest.approx(matrix[j][i], abs=1e-9)


def test_tfidf_matrix_shape() -> None:
    runs = [[_make_topic(i)] for i in range(4)]
    matrix = compute_tfidf_cosine_matrix(runs)
    assert len(matrix) == 4
    assert all(len(row) == 4 for row in matrix)


def test_tfidf_matrix_empty_input_gives_empty() -> None:
    assert compute_tfidf_cosine_matrix([]) == []


def test_tfidf_matrix_single_run_gives_1x1() -> None:
    matrix = compute_tfidf_cosine_matrix([[_make_topic(0)]])
    assert len(matrix) == 1
    assert matrix[0][0] == pytest.approx(1.0)


def test_tfidf_thematic_runs_exceed_threshold() -> None:
    """Thematically similar runs should produce mean cosine >= 0.25."""
    # Mirror the 2026-04-06 live-run evidence from the issue.
    run1 = [
        {"topic": "Illusion of Speed", "hook": "AI testing faster but costlier", "thesis": "Hidden costs outweigh gains", "contrarian_angle": "Speed metrics mislead teams", "talking_points": "ROI automation testing cost"},
        {"topic": "Hidden Costs of AI-Driven Testing", "hook": "Maintenance burden rises", "thesis": "AI test tools create debt", "contrarian_angle": "Automation is not free", "talking_points": "maintenance automation testing cost"},
        {"topic": "Embedded QE", "hook": "Quality shifted left", "thesis": "QE embedded in teams", "contrarian_angle": "Centralised QA still has value", "talking_points": "quality engineering embedded team"},
    ]
    run2 = [
        {"topic": "Myth of Complete Automation", "hook": "Automation cannot cover all", "thesis": "Human testing still needed", "contrarian_angle": "100 percent automation is a myth", "talking_points": "automation testing manual coverage"},
        {"topic": "Overpromising on Maintenance Costs", "hook": "Vendors hide maintenance costs", "thesis": "Long term cost of AI testing high", "contrarian_angle": "Automation creates debt not savings", "talking_points": "maintenance cost automation testing ROI"},
        {"topic": "Security Testing", "hook": "Security gaps in AI pipelines", "thesis": "Automation misses security flaws", "contrarian_angle": "Automated security is insufficient", "talking_points": "security testing automation gaps"},
    ]
    run3 = [
        {"topic": "Developer Experience", "hook": "DX drives quality", "thesis": "Happy developers write better tests", "contrarian_angle": "Tooling without culture fails", "talking_points": "developer experience quality testing"},
        {"topic": "ROI Illusion", "hook": "ROI of AI testing inflated", "thesis": "Hidden costs erode ROI", "contrarian_angle": "Automation ROI is overstated", "talking_points": "ROI automation testing cost illusion"},
        {"topic": "Debunking the AI-Driven Test Automation Revolution", "hook": "Hype exceeds reality", "thesis": "AI testing needs calibration", "contrarian_angle": "Revolution overstated automation AI testing", "talking_points": "AI automation testing debunking ROI cost"},
    ]
    matrix = compute_tfidf_cosine_matrix([run1, run2, run3])
    mean_cosine = mean_pairwise_similarity(matrix)
    assert mean_cosine >= 0.25, (
        f"Expected mean cosine >= 0.25 for thematically similar runs, got {mean_cosine:.3f}"
    )
