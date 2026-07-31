"""Tests for scripts/sync_copilot_context.py (B-035 Task 3(b)).

The defect under test: ``update_copilot_instructions`` appended a freshly
formatted ``## Learned Anti-Patterns`` section without removing the one it wrote
last time, so ``.github/copilot-instructions.md`` accumulated 20 copies of the
same section (2,267 of its 2,601 lines).

A second defect in the same six lines: the split on the insertion marker was
unbounded but the reassembly used only ``parts[0]`` and ``parts[1]``, so a
doubled marker would silently discard everything after it.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = Path(__file__).parent.parent / "scripts" / "sync_copilot_context.py"
_spec = importlib.util.spec_from_file_location("sync_copilot_context", _SCRIPT)
assert _spec is not None and _spec.loader is not None
sync_copilot_context = importlib.util.module_from_spec(_spec)
sys.modules["sync_copilot_context"] = sync_copilot_context
_spec.loader.exec_module(sync_copilot_context)

PatternExtractor = sync_copilot_context.PatternExtractor
GENERATED_HEADING = "## Learned Anti-Patterns"

HAND_AUTHORED = """# Copilot Instructions

## Project Purpose

Hand-authored prose that must survive every sync.

## Key Gotchas

- The blog repo is `oviney/blog`.
"""

TRAILER = """## Additional Resources

- CONTRIBUTING.md
"""


def _generated(marker: str) -> str:
    """Build a generated section carrying a distinguishing marker."""
    return f"""{GENERATED_HEADING}

*Auto-generated on 2026-01-0{marker}*

### Defect Prevention Patterns

**BUG-{marker}** (high) - component
- **Issue**: issue {marker}

"""


@pytest.fixture
def extractor(tmp_path: Path) -> Any:
    """A PatternExtractor rooted at a tmp_path with a .github/ directory."""
    (tmp_path / ".github").mkdir()
    return PatternExtractor(tmp_path)


def _write(extractor: Any, content: str) -> Path:
    extractor.copilot_file.write_text(content)
    return extractor.copilot_file


class TestReplacesInsteadOfAppends:
    """The core B-035 Task 3(b) defect."""

    def test_three_existing_sections_collapse_to_one(self, extractor: Any) -> None:
        """Pre-existing generated sections are removed, not accumulated."""
        path = _write(
            extractor,
            HAND_AUTHORED
            + _generated("1")
            + _generated("2")
            + _generated("3")
            + TRAILER,
        )

        assert extractor.update_copilot_instructions(_generated("9").rstrip())

        assert path.read_text().count(GENERATED_HEADING) == 1

    def test_stale_section_content_is_gone(self, extractor: Any) -> None:
        """Removal takes the section body with it, not just the heading."""
        path = _write(extractor, HAND_AUTHORED + _generated("1") + TRAILER)

        assert extractor.update_copilot_instructions(_generated("9").rstrip())

        content = path.read_text()
        assert "BUG-1" not in content
        assert "BUG-9" in content

    def test_sync_is_idempotent(self, extractor: Any) -> None:
        """Running the sync twice produces the same bytes as running it once."""
        _write(extractor, HAND_AUTHORED + TRAILER)
        section = _generated("9").rstrip()

        extractor.update_copilot_instructions(section)
        once = extractor.copilot_file.read_text()
        extractor.update_copilot_instructions(section)
        twice = extractor.copilot_file.read_text()

        assert once == twice

    def test_sync_twenty_times_still_yields_one_section(self, extractor: Any) -> None:
        """The observed failure mode, reproduced directly: 20 runs, 1 section."""
        _write(extractor, HAND_AUTHORED + TRAILER)
        section = _generated("9").rstrip()

        for _ in range(20):
            extractor.update_copilot_instructions(section)

        assert extractor.copilot_file.read_text().count(GENERATED_HEADING) == 1


class TestPreservesHandAuthoredContent:
    """Everything the generator did not write must survive verbatim."""

    def test_prose_above_and_trailer_below_survive(self, extractor: Any) -> None:
        path = _write(extractor, HAND_AUTHORED + _generated("1") + TRAILER)

        assert extractor.update_copilot_instructions(_generated("9").rstrip())

        content = path.read_text()
        assert "Hand-authored prose that must survive every sync." in content
        assert "The blog repo is `oviney/blog`." in content
        assert "## Additional Resources" in content
        assert "- CONTRIBUTING.md" in content

    def test_generated_section_sits_above_the_trailer(self, extractor: Any) -> None:
        """Insertion point is preserved: generated content precedes the trailer."""
        path = _write(extractor, HAND_AUTHORED + TRAILER)

        assert extractor.update_copilot_instructions(_generated("9").rstrip())

        content = path.read_text()
        assert content.index(GENERATED_HEADING) < content.index(
            "## Additional Resources"
        )

    def test_no_trailer_appends_at_end(self, extractor: Any) -> None:
        """Without the marker the section goes at the end, still exactly once."""
        path = _write(extractor, HAND_AUTHORED + _generated("1"))

        assert extractor.update_copilot_instructions(_generated("9").rstrip())

        content = path.read_text()
        assert content.count(GENERATED_HEADING) == 1
        assert "BUG-1" not in content
        assert content.rstrip().endswith("- **Issue**: issue 9")


class TestBoundedSplit:
    """The latent data-loss defect in the same function."""

    def test_doubled_marker_loses_no_content(self, extractor: Any) -> None:
        """A second '## Additional Resources' must not truncate the file."""
        path = _write(
            extractor,
            HAND_AUTHORED + TRAILER + "\n## Additional Resources\n\n- SECOND-MARKER\n",
        )

        assert extractor.update_copilot_instructions(_generated("9").rstrip())

        assert "- SECOND-MARKER" in path.read_text()


class TestDryRun:
    """--dry-run must not touch the file."""

    def test_dry_run_leaves_file_unmodified(self, extractor: Any) -> None:
        original = HAND_AUTHORED + _generated("1") + TRAILER
        path = _write(extractor, original)

        assert extractor.update_copilot_instructions(
            _generated("9").rstrip(),
            dry_run=True,
        )

        assert path.read_text() == original


class TestMissingFile:
    """Behaviour preserved from before the fix."""

    def test_missing_copilot_file_returns_false(self, extractor: Any) -> None:
        assert not extractor.update_copilot_instructions(_generated("9").rstrip())


class TestExtractorSourcePaths:
    """The extractors must read the state files where they actually live.

    ``defect_tracker.json`` and ``blog_qa_skills.json`` live in
    ``data/skills_state/`` (CLAUDE.md names it the runtime state directory), but
    the extractors looked in ``skills/``. Both returned empty and logged a
    warning, so a regeneration would silently drop the Defect Prevention and
    Content Quality subsections the committed file still carries.
    """

    def test_reads_defect_tracker_from_skills_state(self, tmp_path: Path) -> None:
        state = tmp_path / "data" / "skills_state"
        state.mkdir(parents=True)
        (state / "defect_tracker.json").write_bytes(
            b'{"bugs": [{"id": "BUG-001", "severity": "high", "component": "c",'
            b' "description": "d", "root_cause": "missing_test", "status": "fixed"}]}',
        )

        patterns = PatternExtractor(tmp_path).extract_defect_patterns()

        assert [p["id"] for p in patterns] == ["BUG-001"]

    def test_reads_qa_skills_from_skills_state(self, tmp_path: Path) -> None:
        state = tmp_path / "data" / "skills_state"
        state.mkdir(parents=True)
        (state / "blog_qa_skills.json").write_bytes(
            b'{"skills": {"voice": {"patterns": [{"id": "QA-001",'
            b' "pattern": "p", "check": "c"}]}}}',
        )

        patterns = PatternExtractor(tmp_path).extract_qa_skills()

        assert [p["id"] for p in patterns] == ["QA-001"]

    def test_real_repo_state_files_are_found(self) -> None:
        """Guard against the paths drifting again: both files must resolve."""
        root = Path(__file__).parent.parent
        extractor = PatternExtractor(root)

        assert (extractor.skills_dir / "defect_tracker.json").exists()
        assert (extractor.skills_dir / "blog_qa_skills.json").exists()
