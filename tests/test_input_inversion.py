"""B-048 slice 5: the pipeline starts from the owner's brief, research serves the
take, the writer is the editor of a practitioner's column, and the default research
mode is the one the documentation names (BUG-083)."""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from src.agent_sdk import pipeline, stage3_runner
from src.agent_sdk.brief import OwnerBrief
from src.agent_sdk.research import claude_web

REPO_ROOT = Path(__file__).resolve().parent.parent


def _brief(tmp_path: Path) -> OwnerBrief:
    return OwnerBrief(
        path=tmp_path / "flaky-tests.md",
        title="Flaky tests",
        take="Flaky tests are a budgeting failure, not a testing failure.",
        seen="At one client the retry budget exceeded the on-call budget.",
        change_mind="A suite whose flake rate fell without anyone paying for it.",
    )


class TestDefaultResearchMode:
    """BUG-083: the code's default and the documentation's default cannot drift."""

    def test_run_pipeline_defaults_to_claude_web(self) -> None:
        assert (
            inspect.signature(pipeline.run_pipeline).parameters["research_mode"].default
            == "claude_web"
        )

    def test_run_stage3_defaults_to_claude_web(self) -> None:
        assert (
            inspect.signature(stage3_runner.run_stage3)
            .parameters["research_mode"]
            .default
            == "claude_web"
        )

    def test_the_cli_default_matches(self, monkeypatch) -> None:
        seen: dict = {}
        monkeypatch.setattr(
            pipeline, "_run_end_to_end", lambda topic, **kw: seen.update(kw)
        )

        pipeline.main(["some topic"])

        assert seen["research_mode"] == "claude_web"
        assert "Serper" not in inspect.getsource(pipeline.main)

    def test_claude_md_names_the_same_default(self) -> None:
        text = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        assert re.search(r"Research is `claude_web`", text)


class TestTheWriterIsHandedTheTake:
    def test_writer_prompt_leads_with_the_brief(self, tmp_path: Path) -> None:
        prompt = stage3_runner._build_writer_prompt(
            "Flaky tests", "RESEARCH BRIEF BODY", "", owner_brief=_brief(tmp_path)
        )

        assert prompt.index("AUTHOR'S BRIEF") < prompt.index("RESEARCH BRIEF BODY")
        assert "budgeting failure" in prompt
        assert "retry budget" in prompt

    def test_writer_prompt_without_a_brief_is_unchanged_in_shape(self) -> None:
        prompt = stage3_runner._build_writer_prompt("Flaky tests", "BODY", "")

        assert "AUTHOR'S BRIEF" not in prompt
        assert "RESEARCH BRIEF" in prompt

    def test_system_prompt_is_a_practitioners_editor_not_an_institution(self) -> None:
        p = stage3_runner.WRITER_SYSTEM_PROMPT

        assert "practitioner" in p
        assert "first person" in p
        assert "Economist-style Writer" not in p


class TestResearchServesTheTake:
    def test_claude_web_prompt_carries_the_focus(self) -> None:
        prompt = claude_web._research_prompt("Flaky tests", focus="THE FOCUS TEXT")

        assert "THE FOCUS TEXT" in prompt
        assert "counter" in prompt.lower()

    def test_claude_web_prompt_without_focus_is_the_plain_topic_prompt(self) -> None:
        prompt = claude_web._research_prompt("Flaky tests", focus=None)

        assert prompt == claude_web._research_prompt("Flaky tests", focus="")


class TestTheTemplateExists:
    def test_briefs_template_has_every_section(self) -> None:
        text = (REPO_ROOT / "briefs" / "TEMPLATE.md").read_text(encoding="utf-8")
        for heading in (
            "## My take",
            "## What I've seen",
            "## Where I disagree",
            "## What would change my mind",
            "## Verdict",
        ):
            assert heading in text


class TestTheCli:
    def test_brief_flag_loads_the_brief_and_titles_the_topic(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        brief = tmp_path / "flaky-tests.md"
        brief.write_text("# Flaky tests are a budget line\n\n## My take\n\nX.\n")
        seen: dict = {}

        def fake_run(topic: str, **kwargs) -> None:
            seen["topic"] = topic
            seen.update(kwargs)

        monkeypatch.setattr(pipeline, "_run_end_to_end", fake_run)

        pipeline.main(["--brief", str(brief)])

        assert seen["topic"] == "Flaky tests are a budget line"
        assert seen["owner_brief"].take == "X."
        assert seen["research_mode"] == "claude_web"

    def test_no_brief_and_no_topic_is_an_error(self, monkeypatch) -> None:
        monkeypatch.setattr(pipeline, "_run_end_to_end", lambda *a, **k: None)

        with pytest.raises(SystemExit):
            pipeline.main([])

    def test_a_brief_without_a_take_is_a_cli_error(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        brief = tmp_path / "x.md"
        brief.write_text("# T\n\n## What I've seen\n\nY.\n")
        monkeypatch.setattr(pipeline, "_run_end_to_end", lambda *a, **k: None)

        with pytest.raises(SystemExit):
            pipeline.main(["--brief", str(brief)])
