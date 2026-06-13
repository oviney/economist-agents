#!/usr/bin/env python3
"""Regression tests for the blog author contract (issue #401).

The production author name must live in exactly one place and flow from there
into the Stage 3 writer prompt, the Stage 4 frontmatter safety net, and the
publication validator's author contract — so the writer never emits an author
that Stage 4 then rejects.
"""

from __future__ import annotations

import re

from scripts.publication_validator import BLOG_AUTHOR, PublicationValidator
from src.agent_sdk._shared import apply_editorial_fixes
from src.agent_sdk.stage3_runner import _build_writer_prompt


def test_blog_author_is_the_configured_production_author() -> None:
    assert BLOG_AUTHOR == "Ouray Viney"


def test_writer_prompt_pins_the_configured_author() -> None:
    """The Stage 3 writer prompt must tell the model the exact author to use.

    Previously the prompt only listed ``author`` as a required field without a
    value, so the model invented "Economist Writer" and Stage 4 failed.
    """
    prompt = _build_writer_prompt(
        topic="Test topic",
        research_brief="Some brief.",
        style_section="",
    )
    assert BLOG_AUTHOR in prompt
    assert "do not invent an author" in prompt.lower()


def test_writer_prompt_does_not_emit_the_known_bad_author() -> None:
    prompt = _build_writer_prompt("T", "B", "")
    assert "Economist Writer" not in prompt


def test_safety_net_emits_the_production_author_when_missing() -> None:
    """Behavioural guard: the Stage 4 frontmatter safety net fills in the
    production author when the writer omits it.

    NB: the safety net currently emits the value as a literal (it is not yet
    wired to ``BLOG_AUTHOR`` — see the constant's docstring), so this asserts
    the observable output equals the configured author, not the implementation.
    """
    article = '---\nlayout: post\ntitle: "X"\ncategories: ["Quality Engineering"]\n---\n\nBody text.'
    fixed = apply_editorial_fixes(article)
    assert f'author: "{BLOG_AUTHOR}"' in fixed


def test_validator_accepts_configured_author() -> None:
    validator = PublicationValidator()
    article = (
        f'---\nlayout: post\ntitle: "X"\ndate: 2026-06-11\n'
        f'author: "{BLOG_AUTHOR}"\ncategories: ["quality-engineering"]\n'
        f"---\n\nBody.\n"
    )
    validator._check_author(article)
    assert not any(i["check"] == "author_contract" for i in validator.issues)


def test_prompt_pinned_author_passes_the_validator_contract() -> None:
    """End-to-end: the exact author the writer prompt pins must satisfy the
    validator's author contract — verified dynamically, not via independent
    literal checks, so the two cannot silently drift.
    """
    prompt = _build_writer_prompt("T", "B", "")
    match = re.search(r'set exactly to "([^"]+)"', prompt)
    assert match, "writer prompt no longer pins an explicit author value"
    pinned_author = match.group(1)

    article = (
        f'---\nlayout: post\ntitle: "X"\ndate: 2026-06-11\n'
        f'author: "{pinned_author}"\ncategories: ["quality-engineering"]\n'
        f"---\n\nBody.\n"
    )
    validator = PublicationValidator()
    validator._check_author(article)
    assert not any(i["check"] == "author_contract" for i in validator.issues)


def test_validator_rejects_wrong_author_referencing_constant() -> None:
    validator = PublicationValidator()
    article = (
        '---\nlayout: post\ntitle: "X"\ndate: 2026-06-11\n'
        'author: "Economist Writer"\ncategories: ["quality-engineering"]\n'
        "---\n\nBody.\n"
    )
    validator._check_author(article)
    author_issues = [i for i in validator.issues if i["check"] == "author_contract"]
    assert len(author_issues) == 1
    assert BLOG_AUTHOR in author_issues[0]["message"]
