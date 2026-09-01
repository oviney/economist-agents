#!/usr/bin/env python3
"""B-045 S1 — unit tests for the docs-truth gate.

The gate answers one narrow question: does every repo-relative path referenced
by an *instruction* document actually exist? It does not judge whether the prose
is true. Two of the three doc contradictions fixed in 2026-08 named files that
existed; this gate would have passed both. It exists for the other failure mode.

These tests build documents in ``tmp_path`` rather than asserting against the
real repo, so they do not break every time a doc is edited. The real-repo
regression guard arrives in S2, once the ten existing breaks are fixed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.check_docs_references import (
    AllowlistError,
    BrokenReference,
    check_all,
    extract_references,
)


def _write(root: Path, relpath: str, text: str) -> str:
    """Create a file under ``root`` and return its repo-relative path."""
    target = root / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return relpath


# ── extraction ──────────────────────────────────────────────────────────────


def test_extracts_a_backticked_path() -> None:
    refs = extract_references("See `scripts/foo.py` for details.", "CLAUDE.md")
    assert refs == [(1, "scripts/foo.py")]


def test_extracts_a_markdown_link_target_relative_to_its_document() -> None:
    """A link in .github/ that points at ../scripts/ resolves to scripts/."""
    refs = extract_references(
        "See [the agent](../scripts/foo.py).", ".github/copilot-instructions.md"
    )
    assert refs == [(1, "scripts/foo.py")]


def test_reports_the_line_number_of_each_reference() -> None:
    text = "intro\n\nSee `src/a.py`\nand `tests/b.py`\n"
    assert extract_references(text, "README.md") == [(3, "src/a.py"), (4, "tests/b.py")]


@pytest.mark.parametrize(
    "candidate",
    [
        "output/posts/<slug>-hero.svg",  # placeholder
        "scripts/*.py",  # glob
        "docs/${NAME}.md",  # shell interpolation
        "https://example.com/scripts/foo.py",  # URL
        "output/pipeline_result.json",  # generated, not source-controlled
        "some/other/thing.py",  # not a scannable prefix
    ],
)
def test_ignores_non_paths_and_unscannable_prefixes(candidate: str) -> None:
    """A noisy gate is a disabled gate — these must never be flagged."""
    assert extract_references(f"See `{candidate}` here.", "CLAUDE.md") == []


@pytest.mark.parametrize(
    "candidate",
    [
        "ANTHROPIC_API_KEY",  # env var
        "claude_web",  # a mode name
        "--brief",  # a CLI flag
        "0",  # an exit code
        "chart_only",  # an enum value
        "query()",  # a function call
        "SkillsManager.learn_pattern()",  # a method
        "~/.claude",  # a home-relative dir
        "oviney/blog",  # a GitHub repo slug, not a repo path
        "[UNVERIFIED]",  # a literal marker
    ],
)
def test_bare_tokens_in_backticks_are_never_treated_as_paths(candidate: str) -> None:
    """Regression: the first implementation resolved every backticked token
    relative to the referring document, so `ANTHROPIC_API_KEY` in a doc under
    docs/ became `docs/ANTHROPIC_API_KEY` and was reported as broken. That
    produced 95 false positives against the real repo — enough noise to get the
    gate switched off, which is the failure this whole item exists to prevent.
    """
    assert extract_references(f"Set `{candidate}` first.", "docs/runbook.md") == []


def test_gitignored_runtime_state_is_not_scanned() -> None:
    """`data/` is gitignored in its entirety (.gitignore:42 `data/*`).

    Those files are runtime state that does not exist on a clean checkout, so
    scanning them would make the gate fail for everyone who has not run the
    pipeline yet — correct references reported as breaks.
    """
    assert (
        extract_references("State lives in `data/skills_state/x.json`.", "CLAUDE.md")
        == []
    )


def test_a_non_scannable_relative_path_is_not_forced_under_the_doc_dir() -> None:
    """`output/posts` in a .github/ doc is still `output/`, not `.github/output/`."""
    assert extract_references("Written to `output/posts`.", ".github/x.md") == []


def test_a_line_suffix_is_stripped_from_a_path() -> None:
    """Docs cite `scripts/foo.py:206`; the file is what must exist."""
    assert extract_references("See `scripts/foo.py:206`.", "CLAUDE.md") == [
        (1, "scripts/foo.py")
    ]


# ── the anchor bug (B-045 regression guard) ─────────────────────────────────


@pytest.mark.parametrize(
    ("cited", "expected"),
    [
        ("scripts/economist_agent.py#L28-L65", "scripts/economist_agent.py"),
        ("scripts/editorial_board.py#L48-L145", "scripts/editorial_board.py"),
        ("scripts/economist_agent.py#L94-L137", "scripts/economist_agent.py"),
        ("src/agent_sdk/pipeline.py#L42", "src/agent_sdk/pipeline.py"),
        ("docs/adr/ADR-0015.md#L3-9", "docs/adr/ADR-0015.md"),
    ],
)
def test_a_github_line_anchor_is_stripped_from_a_path(
    cited: str, expected: str
) -> None:
    """Regression: the gate did not strip `#L28-L65`, so three references to
    files that exist were reported broken. The BACKLOG entry then recorded 13
    real breaks where there were 10 — the gate's own bug inflating its findings.
    """
    assert extract_references(f"See `{cited}`.", "CLAUDE.md") == [(1, expected)]


def test_a_bare_fragment_anchor_is_still_skipped() -> None:
    """`#section-name` is an in-document anchor, not a path."""
    assert extract_references("Jump to `#quality-gates`.", "CLAUDE.md") == []


# ── checking ────────────────────────────────────────────────────────────────


def test_an_existing_reference_is_not_a_break(tmp_path: Path) -> None:
    _write(tmp_path, "scripts/real.py", "x = 1\n")
    doc = _write(tmp_path, "CLAUDE.md", "Run `scripts/real.py`.\n")

    assert check_all(tmp_path, docs=(doc,), allowed={}) == []


def test_a_missing_reference_is_reported_with_doc_line_and_path(
    tmp_path: Path,
) -> None:
    doc = _write(tmp_path, "CLAUDE.md", "intro\nRun `scripts/gone.py`.\n")

    breaks = check_all(tmp_path, docs=(doc,), allowed={})

    assert breaks == [BrokenReference(doc="CLAUDE.md", line=2, path="scripts/gone.py")]


def test_an_allowlisted_missing_path_is_not_a_break(tmp_path: Path) -> None:
    """A doc may name a removed file on purpose, to say it was removed."""
    doc = _write(tmp_path, "CLAUDE.md", "`scripts/retired.py` was deleted.\n")

    breaks = check_all(
        tmp_path,
        docs=(doc,),
        allowed={"scripts/retired.py": "Named precisely to say it is gone."},
    )

    assert breaks == []


def test_the_shipped_allowlist_is_empty(tmp_path: Path) -> None:
    """B-045: it starts empty and every addition is owner-gated.

    A prior draft shipped one entry excusing `scripts/economist_agent.py` as
    deleted by B-024. B-024 was abandoned; the file is still here, so the entry
    would have suppressed a live check on a 49KB module.
    """
    from scripts.check_docs_references import ALLOWED_MISSING

    assert ALLOWED_MISSING == {}


def test_an_allowlist_entry_without_a_reason_is_itself_an_error(
    tmp_path: Path,
) -> None:
    """The reason is the whole point — an unexplained allowlist entry rots."""
    doc = _write(tmp_path, "CLAUDE.md", "`scripts/gone.py`\n")

    with pytest.raises(AllowlistError, match="scripts/gone.py"):
        check_all(tmp_path, docs=(doc,), allowed={"scripts/gone.py": "   "})


def test_a_document_that_does_not_exist_is_itself_a_break(tmp_path: Path) -> None:
    """Renaming an instruction doc without updating the list must not go quiet."""
    breaks = check_all(tmp_path, docs=("CLAUDE.md",), allowed={})

    assert [b.path for b in breaks] == ["CLAUDE.md"]


def test_breaks_from_several_documents_are_all_reported(tmp_path: Path) -> None:
    a = _write(tmp_path, "CLAUDE.md", "`scripts/gone_a.py`\n")
    b = _write(tmp_path, "README.md", "`src/gone_b.py`\n")

    breaks = check_all(tmp_path, docs=(a, b), allowed={})

    assert {x.path for x in breaks} == {"scripts/gone_a.py", "src/gone_b.py"}


def test_main_returns_zero_when_every_reference_resolves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The process exit code is what `ci-local` will gate on."""
    import scripts.check_docs_references as cdr

    _write(tmp_path, "scripts/real.py", "x = 1\n")
    _write(tmp_path, "CLAUDE.md", "Run `scripts/real.py`.\n")
    monkeypatch.setattr(cdr, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(cdr, "INSTRUCTION_DOCS", ("CLAUDE.md",))

    assert cdr.main() == 0


def test_main_returns_one_when_a_reference_is_broken(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import scripts.check_docs_references as cdr

    _write(tmp_path, "CLAUDE.md", "Run `scripts/gone.py`.\n")
    monkeypatch.setattr(cdr, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(cdr, "INSTRUCTION_DOCS", ("CLAUDE.md",))

    assert cdr.main() == 1
