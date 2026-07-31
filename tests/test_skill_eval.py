"""Tests for the B-033 skill eval harness.

8,031 lines of `SKILL.md` have never been measured. Boeckeler's point is not that skills
are useless but that nobody knows which ones earn their context cost — especially since
many are model-authored, so the model may already know their content.

This harness makes the guide layer measurable. Its contract:

* `--list` gives cheap triage without running anything.
* A skill with declared scenarios produces a with/without delta.
* A skill *without* scenarios reports UNMEASURED and never silently passes. That property
  is the whole point: an unmeasured guide must not look like a validated one.
"""

from __future__ import annotations

from pathlib import Path

from scripts.skill_eval import (
    UNMEASURED,
    SkillSummary,
    evaluate_skill,
    format_listing,
    list_skills,
    load_scenarios,
    score_text,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestListSkills:
    """Cheap triage: big, old and unreferenced surfaces first."""

    def test_finds_the_repo_skills(self) -> None:
        """Every `skills/` directory is discovered.

        This asserted `>= 30` when the repo also vendored 20 upstream copies.
        B-035 Task 3(a) deleted those — they loaded from the `agent-skills`
        plugin, never from here — so a floor tied to that count now measures
        nothing but the deletion. Comparing against the directories actually on
        disk keeps the test about discovery, which is what it is for.
        """
        on_disk = {
            d.name
            for d in (REPO_ROOT / "skills").iterdir()
            if (d / "SKILL.md").is_file()
        }
        skills = list_skills(REPO_ROOT / "skills")

        assert {s.name for s in skills} == on_disk
        assert all(isinstance(s, SkillSummary) for s in skills)

    def test_sorted_by_line_count_descending(self) -> None:
        skills = list_skills(REPO_ROOT / "skills")

        counts = [s.lines for s in skills]
        assert counts == sorted(counts, reverse=True)

    def test_reports_real_line_counts(self) -> None:
        skills = {s.name: s for s in list_skills(REPO_ROOT / "skills")}

        economist = skills["economist-writing"]
        actual = len(
            (REPO_ROOT / "skills" / "economist-writing" / "SKILL.md")
            .read_text(encoding="utf-8")
            .splitlines(),
        )
        assert economist.lines == actual

    def test_missing_directory_yields_no_skills(self, tmp_path: Path) -> None:
        assert list_skills(tmp_path / "nope") == []

    def test_listing_marks_unmeasured_skills(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "lonely"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: lonely\n---\n", encoding="utf-8"
        )

        listing = format_listing(list_skills(tmp_path))

        assert UNMEASURED in listing


class TestLoadScenarios:
    """Scenarios are declared beside the skill, in `eval.yaml`."""

    def test_absent_eval_file_yields_no_scenarios(self, tmp_path: Path) -> None:
        assert load_scenarios(tmp_path / "nothing") == []

    def test_loads_declared_scenarios(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "demo"
        skill_dir.mkdir()
        (skill_dir / "eval.yaml").write_text(
            "scenarios:\n"
            "  - name: british-spelling\n"
            "    with_skill: The organisation analysed the behaviour.\n"
            "    without_skill: The organization analyzed the behavior.\n",
            encoding="utf-8",
        )

        scenarios = load_scenarios(skill_dir)

        assert len(scenarios) == 1
        assert scenarios[0].name == "british-spelling"

    def test_malformed_yaml_yields_no_scenarios(self, tmp_path: Path) -> None:
        """A broken eval file must read as unmeasured, not crash the harness."""
        skill_dir = tmp_path / "broken"
        skill_dir.mkdir()
        (skill_dir / "eval.yaml").write_text("scenarios: [[[", encoding="utf-8")

        assert load_scenarios(skill_dir) == []


class TestScoring:
    """Scoring is deterministic, so the harness is free to run and cannot fail on auth."""

    def test_british_spelling_scores_above_american(self) -> None:
        british = score_text("The organisation analysed the behaviour of the centre.")
        american = score_text("The organization analyzed the behavior of the center.")

        assert british > american

    def test_hedging_lowers_the_score(self) -> None:
        plain = score_text("Throughput fell by 1.5%.")
        hedged = score_text("One suspects throughput fell by 1.5%.")

        assert hedged < plain

    def test_scoring_is_deterministic(self) -> None:
        text = "The organisation analysed throughput."

        assert score_text(text) == score_text(text)

    def test_empty_text_scores_zero(self) -> None:
        assert score_text("") == 0.0


class TestEvaluateSkill:
    """The delta is the deliverable: did the skill change the outcome?"""

    def test_unmeasured_skill_reports_unmeasured(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "bare"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: bare\n---\n", encoding="utf-8")

        result = evaluate_skill(skill_dir)

        assert result.status == UNMEASURED
        assert result.delta is None

    def test_measured_skill_reports_a_delta(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "spelling"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: spelling\n---\n", encoding="utf-8"
        )
        (skill_dir / "eval.yaml").write_text(
            "scenarios:\n"
            "  - name: british\n"
            "    with_skill: The organisation analysed the behaviour.\n"
            "    without_skill: The organization analyzed the behavior.\n",
            encoding="utf-8",
        )

        result = evaluate_skill(skill_dir)

        assert result.status == "MEASURED"
        assert result.delta is not None
        assert result.delta > 0, "the skill should measurably improve the output"

    def test_a_skill_that_changes_nothing_reports_a_zero_delta(
        self,
        tmp_path: Path,
    ) -> None:
        """The finding the audit expects: a guide the model did not need."""
        skill_dir = tmp_path / "inert"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: inert\n---\n", encoding="utf-8")
        (skill_dir / "eval.yaml").write_text(
            "scenarios:\n"
            "  - name: identical\n"
            "    with_skill: The organisation analysed throughput.\n"
            "    without_skill: The organisation analysed throughput.\n",
            encoding="utf-8",
        )

        result = evaluate_skill(skill_dir)

        assert result.delta == 0.0


class TestCli:
    """The CLI contract the spec promises."""

    def test_list_exits_zero(self) -> None:
        from scripts.skill_eval import main

        assert main(["--list"]) == 0

    def test_strict_fails_on_an_unmeasured_skill(self, tmp_path: Path) -> None:
        from scripts.skill_eval import main

        skill_dir = tmp_path / "bare"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: bare\n---\n", encoding="utf-8")

        assert main(["--list", "--strict", "--skills-dir", str(tmp_path)]) == 1

    def test_scoring_reaches_no_llm_client(self) -> None:
        """Deterministic by default, so it is free to run and cannot fail on auth.

        The harness must not acquire an LLM dependency by drift: the moment scoring needs
        a model, `--list` starts costing money and failing on auth, and then nobody runs
        it — which is how the guide layer became unmeasured in the first place.
        """
        source = (REPO_ROOT / "scripts" / "skill_eval.py").read_text(encoding="utf-8")

        for forbidden in ("import anthropic", "claude_agent_sdk", "from openai"):
            assert forbidden not in source, f"skill_eval must stay keyless: {forbidden}"
