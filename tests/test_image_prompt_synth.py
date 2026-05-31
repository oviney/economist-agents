"""Tests for src/agent_sdk/image_prompt_synth.py (#403 slice 3, Task 3.1)."""

from __future__ import annotations

import pytest

from src.agent_sdk.image_prompt_synth import (
    PromptSynthError,
    compose_prompt,
)


def test_contains_all_hard_constraints() -> None:
    out = compose_prompt(title="X", image_alt="A scene description")
    assert "Aspect ratio: 1792x1024" in out
    assert "Economist red #E3120B" in out
    assert "no text, no words, no captions" in out
    assert "bold, high-contrast" in out


def test_title_appears_for_human_orientation() -> None:
    out = compose_prompt(
        title="Three People and a Fleet",
        image_alt="A scene of three figures and many small robots",
    )
    assert "Three People and a Fleet" in out


def test_image_alt_appears_as_subject_directive() -> None:
    alt = (
        "An Economist-style editorial illustration of a lone product "
        "manager directing a swarm of robotic agents"
    )
    out = compose_prompt(title="X", image_alt=alt)
    assert alt in out
    assert "Subject:" in out


def test_image_caption_surfaces_as_editorial_framing_when_provided() -> None:
    out = compose_prompt(
        title="X",
        image_alt="alt text",
        image_caption="Fewer humans does not mean fewer decisions",
    )
    assert "Editorial framing:" in out
    assert "Fewer humans does not mean fewer decisions" in out


def test_image_caption_omitted_when_empty() -> None:
    out = compose_prompt(title="X", image_alt="alt", image_caption="")
    assert "Editorial framing:" not in out


def test_output_contains_no_markdown_code_fences() -> None:
    # Image tools either ignore markdown or render it literally — both
    # are bad. The artefact must be plain text.
    out = compose_prompt(title="X", image_alt="alt")
    assert "```" not in out
    assert "**" not in out


def test_output_is_a_single_string_with_newlines() -> None:
    out = compose_prompt(title="X", image_alt="alt")
    assert isinstance(out, str)
    assert "\n" in out  # multi-line, not collapsed


def test_internal_whitespace_in_inputs_is_collapsed() -> None:
    # Defensive: a copy-pasted alt may have stray tabs / double spaces.
    out = compose_prompt(
        title="X",
        image_alt="A scene   with\tlots\n\nof   whitespace",
    )
    assert "A scene with lots of whitespace" in out


def test_long_inputs_truncated_to_protect_against_bloat() -> None:
    huge = "X" * 5000
    out = compose_prompt(title=huge, image_alt=huge)
    # 600 cap on each field; total output bounded.
    assert len(out) < 3000


def test_empty_title_raises() -> None:
    with pytest.raises(PromptSynthError, match="title"):
        compose_prompt(title="", image_alt="alt")


def test_whitespace_only_title_raises() -> None:
    with pytest.raises(PromptSynthError, match="title"):
        compose_prompt(title="   \n\t", image_alt="alt")


def test_empty_image_alt_raises() -> None:
    with pytest.raises(PromptSynthError, match="image_alt"):
        compose_prompt(title="X", image_alt="")
