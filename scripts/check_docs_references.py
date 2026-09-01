#!/usr/bin/env python3
"""B-045 — the docs-truth gate.

Fails when an *instruction* document references a repo-relative path that does
not exist. It checks path existence only; it does not judge whether the prose
is true. That narrowness is deliberate and is stated in the spec: three doc
contradictions fixed in 2026-08 all named files that existed while describing
behaviour that had been deleted, and this gate would have passed every one of
them. What it does catch is the other failure — measured at ten dangling paths
across two documents on the base where it was written, four of them naming a
``src/crews/stage3_crew.py`` that has never existed in this repo.

History is deliberately out of scope. ``docs/archive*/``, ``docs/sprint_logs/``,
``docs/CHANGELOG.md`` and ``docs/adr/*`` record what was true when written; a
gate that forces you to edit history to satisfy a linter is worse than no gate.

Usage:
    python scripts/check_docs_references.py
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Documents that tell a human or an agent how to operate this repo. Explicit
#: rather than a glob, so adding one is a deliberate act.
INSTRUCTION_DOCS: tuple[str, ...] = (
    "CLAUDE.md",
    "README.md",
    "CONTRIBUTING.md",
    "copilot-instructions.md",
    ".github/copilot-instructions.md",
    "docs/keyless-pipeline-runbook.md",
)

#: Paths referenced on purpose although they no longer exist — always because
#: the document is *telling you they were removed*. The reason is mandatory: an
#: unexplained entry is indistinguishable from rot, so an empty one is an error.
#:
#: Starts empty by design (B-045). An earlier draft carried an entry excusing
#: ``scripts/economist_agent.py`` as "deleted by B-024"; B-024 was abandoned and
#: the file is still here, so that entry would have suppressed a live check.
#: Adding an entry is an owner-gated decision, not a way past a red gate.
ALLOWED_MISSING: dict[str, str] = {}

#: Only paths under these prefixes are checked. Anything else (``output/``,
#: ``.venv/``, bare words) is prose or generated, not a source reference.
#:
#: ``data/`` is deliberately absent: ``.gitignore:42`` ignores ``data/*``
#: wholesale, so those files are runtime state that does not exist on a clean
#: checkout. Scanning them would report correct references as breaks for anyone
#: who has not run the pipeline yet — the same false-positive noise that gets a
#: gate switched off.
SCANNABLE_PREFIXES: tuple[str, ...] = (
    "scripts/",
    "src/",
    "tests/",
    "docs/",
    "agents/",
    "mcp_servers/",
    ".github/",
)

#: A reference containing any of these is prose, a template, or a call
#: expression — never a path we can check.
_PLACEHOLDER_CHARS = frozenset("<>*{}$?!|\"' ()[]~,")

#: Trailing ``:123`` line citations — docs write ``scripts/foo.py:206``.
_LINE_SUFFIX = re.compile(r":\d+$")

#: A trailing fragment — a GitHub line anchor (``scripts/foo.py#L28-L65``) or a
#: heading link (``docs/adr/ADR-0015.md#context``). Not stripping the first form
#: was the gate's own bug: it reported three references to files that exist as
#: broken, and the backlog entry then recorded 13 real breaks where there were
#: 10. A leading ``#`` is handled earlier — that is an in-document anchor, not a
#: path.
_FRAGMENT = re.compile(r"#[^#/]*$")

_BACKTICKED = re.compile(r"`([^`\n]+)`")
_MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


class AllowlistError(Exception):
    """Raised when an ``ALLOWED_MISSING`` entry carries no reason."""


@dataclass(frozen=True)
class BrokenReference:
    """A reference in a document that does not resolve to a real path."""

    doc: str
    line: int
    path: str

    def __str__(self) -> str:
        return f"{self.doc}:{self.line} -> {self.path}"


def _collapse(path_str: str) -> str:
    """Resolve ``.`` and ``..`` segments textually, without touching disk.

    Args:
        path_str: A slash-separated path that may contain ``.`` or ``..``.

    Returns:
        The same path with those segments applied.
    """
    parts: list[str] = []
    for part in path_str.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
        else:
            parts.append(part)
    return "/".join(parts)


def _normalise(candidate: str, doc_relpath: str) -> str | None:
    """Return the repo-relative path a reference denotes, or None to skip it.

    Only ``./`` and ``../`` targets are resolved against the referring
    document's directory. Everything else is treated as already repo-relative.

    An earlier version resolved *every* token against the doc directory, which
    turned ``ANTHROPIC_API_KEY`` in a ``docs/`` file into
    ``docs/ANTHROPIC_API_KEY`` and produced 95 false positives. A gate that
    noisy gets switched off, so this stays strict about what looks like a path.

    Args:
        candidate: Raw text captured from a backtick span or link target.
        doc_relpath: Repo-relative path of the referring document.

    Returns:
        A repo-relative path under a scannable prefix, or None.
    """
    text = candidate.strip()
    if "://" in text or text.startswith(("#", "mailto:")):
        return None
    text = _FRAGMENT.sub("", text)
    text = _LINE_SUFFIX.sub("", text)
    if not text or _PLACEHOLDER_CHARS & set(text):
        return None

    if text.startswith(("./", "../")):
        text = _collapse(f"{Path(doc_relpath).parent}/{text}")

    return text if text.startswith(SCANNABLE_PREFIXES) else None


def extract_references(text: str, doc_relpath: str) -> list[tuple[int, str]]:
    """Extract (line number, repo-relative path) pairs from a document's text.

    Args:
        text: Full document contents.
        doc_relpath: Repo-relative path of the document, for resolving links.

    Returns:
        One entry per checkable reference, in document order.
    """
    found: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern in (_BACKTICKED, _MD_LINK):
            for match in pattern.finditer(line):
                path = _normalise(match.group(1), doc_relpath)
                if path is not None and (lineno, path) not in found:
                    found.append((lineno, path))
    return found


def check_all(
    root: Path,
    docs: tuple[str, ...] = INSTRUCTION_DOCS,
    allowed: dict[str, str] | None = None,
) -> list[BrokenReference]:
    """Check every reference in ``docs`` and return the breaks.

    Args:
        root: Repository root to resolve paths against.
        docs: Repo-relative instruction documents to scan.
        allowed: Path -> reason for deliberate references to missing files.

    Returns:
        Every broken reference found, in document then line order.

    Raises:
        AllowlistError: If an ``allowed`` entry has a blank reason.
    """
    allowed = ALLOWED_MISSING if allowed is None else allowed
    for path, reason in allowed.items():
        if not reason.strip():
            raise AllowlistError(
                f"ALLOWED_MISSING['{path}'] has no reason. Every entry must say "
                "why the reference is deliberate, or it is indistinguishable "
                "from rot."
            )

    breaks: list[BrokenReference] = []
    for doc in docs:
        doc_path = root / doc
        if not doc_path.is_file():
            breaks.append(BrokenReference(doc=doc, line=0, path=doc))
            continue
        text = doc_path.read_text(encoding="utf-8")
        for lineno, ref in extract_references(text, doc):
            if ref in allowed or (root / ref).exists():
                continue
            breaks.append(BrokenReference(doc=doc, line=lineno, path=ref))
    return breaks


def main() -> int:
    """Report broken references and return a process exit code.

    Returns:
        0 when every reference resolves, 1 otherwise.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    breaks = check_all(REPO_ROOT, INSTRUCTION_DOCS, ALLOWED_MISSING)
    if not breaks:
        logger.info("docs-truth gate: every referenced path resolves.")
        return 0
    logger.error("docs-truth gate: %d broken reference(s)", len(breaks))
    for item in breaks:
        logger.error("   %s", item)
    logger.error(
        "\nFix the reference, or add the path to ALLOWED_MISSING in %s with a "
        "reason (owner-gated — see docs/specs/B-045-docs-truth-gate.md).",
        Path(__file__).name,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
