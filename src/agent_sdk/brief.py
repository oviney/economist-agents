"""The owner's brief — the input the pipeline starts from (B-048, D1).

A post begins with what the owner thinks, not with a topic string. The brief is
a small markdown file the owner writes (or dictates to Claude and exports):

    # <working title>
    ## My take            — the thesis, in the owner's words
    ## What I've seen     — concrete experiences; clients anonymised, specifics kept
    ## Where I disagree   — with the consensus, the vendor line, or a younger self
    ## What would change my mind
    ## Sources I trust on this   (optional)
    ## Verdict            (filled in after publishing — D5)

Only the take is mandatory. Everything else is optional but reported, because a
brief with no experience in it produces the article any reader could have got
from Claude directly. Parsing is deliberately tolerant: heading text is matched
by keyword, case-insensitively, so "## My Take" and "## The take" both land.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

#: Section keywords → field names. Order is the template order.
_SECTIONS: tuple[tuple[str, str], ...] = (
    ("take", "take"),
    ("seen", "seen"),
    ("disagree", "disagree"),
    ("change my mind", "change_mind"),
    ("sources", "sources"),
    ("verdict", "verdict"),
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


class OwnerBriefError(ValueError):
    """The brief cannot drive a run — the message says what is missing."""


@dataclass
class OwnerBrief:
    """The owner's take, parsed from ``briefs/<slug>.md``."""

    path: Path
    title: str
    take: str
    seen: str = ""
    disagree: str = ""
    change_mind: str = ""
    sources: str = ""
    verdict: str = ""
    #: Optional sections the brief did not fill, by template name.
    missing: list[str] = field(default_factory=list)

    @property
    def slug(self) -> str:
        """The file stem — the owner chose it, and it becomes the URL."""
        return self.path.stem

    def writer_block(self) -> str:
        """The brief as the writer sees it: the spine of the article."""
        parts = [
            "AUTHOR'S BRIEF — this is the spine of the article. The research below "
            "is supporting steel, not the other way round.",
            "",
            f"THESIS (argue this, in the author's terms): {self.take}",
        ]
        if self.seen:
            parts += [
                "",
                "WHAT THE AUTHOR HAS SEEN (use in the first person, keep the "
                "specifics, never invent additional experiences):",
                self.seen,
            ]
        if self.disagree:
            parts += [
                "",
                "WHERE THE AUTHOR DISAGREES WITH THE CONSENSUS:",
                self.disagree,
            ]
        if self.change_mind:
            parts += [
                "",
                "WHAT WOULD CHANGE THE AUTHOR'S MIND (this is the counterpoint the "
                "article must take seriously):",
                self.change_mind,
            ]
        if self.sources:
            parts += ["", "SOURCES THE AUTHOR TRUSTS ON THIS:", self.sources]
        return "\n".join(parts)

    def research_focus(self) -> str:
        """What research should look for, given the take."""
        lines = [
            f"The author's thesis: {self.take}",
            "Find (a) the strongest quantified evidence FOR it, (b) the strongest "
            "counter-evidence against it, (c) named companies, people or cases "
            "that illustrate it.",
        ]
        if self.disagree:
            lines.append(f"The consensus position the author disputes: {self.disagree}")
        if self.sources:
            lines.append(f"Start from these sources: {self.sources}")
        return "\n".join(lines)


def _sections(text: str) -> tuple[str, dict[str, str]]:
    """Split markdown into (title, {field: body}) by the template's headings."""
    matches = list(_HEADING_RE.finditer(text))
    title = ""
    found: dict[str, str] = {}
    for idx, m in enumerate(matches):
        level, heading = len(m.group(1)), m.group(2).strip()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[m.end() : end].strip()
        if level == 1 and not title:
            title = heading
            continue
        lowered = heading.lower()
        for keyword, name in _SECTIONS:
            if keyword in lowered and name not in found:
                found[name] = body
                break
    return title, found


def recent_verdicts(briefs_dir: str | Path = "briefs", limit: int = 5) -> str:
    """The owner's last ``limit`` post-publish verdicts, newest first, as a block
    for the writer prompt — or ``""`` when none has been written yet (D5).

    This replaces the ChromaDB style memory, whose collection held zero
    documents for its entire life. Five honest sentences from the author about
    recent drafts beat four hundred regex scores.
    """
    d = Path(briefs_dir)
    if not d.is_dir():
        return ""
    entries: list[tuple[float, str, str]] = []
    for p in d.glob("*.md"):
        if p.name.upper() == "TEMPLATE.MD":
            continue
        _, found = _sections(p.read_text(encoding="utf-8"))
        verdict = found.get("verdict", "").strip()
        if verdict:
            entries.append((p.stat().st_mtime, p.stem, verdict))
    if not entries:
        return ""
    entries.sort(reverse=True)
    lines = [f"- {slug}: {verdict}" for _, slug, verdict in entries[:limit]]
    return "\n".join(lines)


def load_owner_brief(path: str | Path) -> OwnerBrief:
    """Parse the owner's brief. Raises ``OwnerBriefError`` when there is no take."""
    p = Path(path)
    if not p.is_file():
        raise OwnerBriefError(f"No brief at {p}")
    title, found = _sections(p.read_text(encoding="utf-8"))
    take = found.get("take", "")
    if not take:
        raise OwnerBriefError(
            f"{p} has no '## My take' section with text in it. The take is the one "
            "thing the pipeline cannot supply; write two or three sentences of what "
            "you actually think before running."
        )
    missing = [
        name
        for _, name in _SECTIONS
        if name not in ("take", "sources", "verdict") and not found.get(name)
    ]
    return OwnerBrief(
        path=p,
        title=title or p.stem.replace("-", " "),
        take=take,
        seen=found.get("seen", ""),
        disagree=found.get("disagree", ""),
        change_mind=found.get("change_mind", ""),
        sources=found.get("sources", ""),
        verdict=found.get("verdict", ""),
        missing=missing,
    )
