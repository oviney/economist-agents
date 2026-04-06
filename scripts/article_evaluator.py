#!/usr/bin/env python3
"""Article Evaluator — 5-Dimension Quality Scoring (Story #116).

Scores every generated article on 5 quality dimensions deterministically.
Persists scores to logs/article_evals.json for trend tracking.

Usage:
    from scripts.article_evaluator import ArticleEvaluator

    evaluator = ArticleEvaluator()
    result = evaluator.evaluate(article_text)
    print(f"Score: {result.percentage}% ({result.total_score}/{result.max_score})")
    result.persist("logs/article_evals.json")
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# Constants (reused from existing validators)
# ═══════════════════════════════════════════════════════════════════════════

_BANNED_OPENINGS = [
    r"in today's world",
    r"in today's fast-paced",
    r"it's no secret",
    r"when it comes to",
    r"^amidst\b",
    r"the arrival of\b",
    r"the emergence of\b",
    r"the rise of\b",
]

_BANNED_PHRASES = [
    "game-changer",
    "game changer",
    "paradigm shift",
    "at the end of the day",
]

# Hedging phrases undermine the authoritative Economist voice (SKILL.md Rule 4)
_HEDGING_PHRASES: list[str] = [
    "it would be misguided",
    "one might",
    "it is worth noting",
    "it should be noted",
    "it is important to",
    "it is not a minor footnote",
    "further complicating matters",
    "invites closer scrutiny",
    "in practical terms",
]

_BANNED_CLOSINGS = [
    "in conclusion",
    "to conclude",
    "in summary",
    "remains to be seen",
    "only time will tell",
    "will rest on",
    "depends on",
    "the key is",
    "to summarise",
]

_VAGUE_ATTRIBUTION = [
    "studies show",
    "research shows",
    "experts say",
    "experts agree",
    "it is widely known",
    "it is well known",
    "research indicates",
]

_AMERICAN_SPELLINGS = [
    "organization",
    "optimization",
    "analyze",
    "behavior",
    "favor",
    "color",
    "labor",
    "center",
    "utilize",
    "recognize",
    "customize",
    "prioritize",
    "standardize",
    "modernize",
]

_REQUIRED_FRONTMATTER = ["layout", "title", "date", "categories", "image"]


# ═══════════════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class EvalResult:
    """Result of article evaluation across 5 dimensions."""

    scores: dict[str, int] = field(default_factory=dict)
    details: dict[str, str] = field(default_factory=dict)
    article_filename: str = ""

    @property
    def total_score(self) -> int:
        return sum(self.scores.values())

    @property
    def max_score(self) -> int:
        return 50

    @property
    def percentage(self) -> int:
        return round(self.total_score / self.max_score * 100) if self.max_score else 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON persistence."""
        return {
            "article_filename": self.article_filename,
            "timestamp": datetime.now().isoformat(),
            "scores": self.scores,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "details": self.details,
        }

    def persist(self, filepath: str = "logs/article_evals.json") -> None:
        """Append evaluation to JSON log file."""
        import orjson

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        evals: list[dict[str, Any]] = []
        if path.exists():
            try:
                evals = orjson.loads(path.read_bytes())
            except Exception:
                evals = []

        evals.append(self.to_dict())
        path.write_bytes(orjson.dumps(evals, option=orjson.OPT_INDENT_2))


# ═══════════════════════════════════════════════════════════════════════════
# Evaluator
# ═══════════════════════════════════════════════════════════════════════════


class ArticleEvaluator:
    """Deterministic 5-dimension article quality evaluator."""

    def evaluate(self, article: str, filename: str = "") -> EvalResult:
        """Evaluate an article across 5 quality dimensions.

        Args:
            article: Full article text with YAML frontmatter.
            filename: Optional filename for logging.

        Returns:
            EvalResult with scores (1-10 each), details, and total.
        """
        frontmatter = self._parse_frontmatter(article)
        body = self._extract_body(article)

        result = EvalResult(article_filename=filename)
        result.scores["opening_quality"] = self._score_opening(body)
        result.scores["evidence_sourcing"] = self._score_evidence(body)
        result.scores["voice_consistency"] = self._score_voice(body)
        result.scores["structure"] = self._score_structure(article, frontmatter, body)
        result.scores["visual_engagement"] = self._score_visual(frontmatter, body)

        result.details["opening_quality"] = self._detail_opening(body)
        result.details["evidence_sourcing"] = self._detail_evidence(body)
        result.details["voice_consistency"] = self._detail_voice(body)
        result.details["structure"] = self._detail_structure(frontmatter, body)
        result.details["visual_engagement"] = self._detail_visual(frontmatter, body)

        return result

    # --- Helpers ---

    @staticmethod
    def _parse_frontmatter(article: str) -> dict[str, Any]:
        if article.strip().startswith("---"):
            parts = article.split("---", 2)
            if len(parts) >= 3:
                try:
                    return yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError:
                    return {}
        return {}

    @staticmethod
    def _extract_body(article: str) -> str:
        if article.strip().startswith("---"):
            parts = article.split("---", 2)
            if len(parts) >= 3:
                return parts[2].strip()
        return article

    # --- Dimension 1: Opening Quality ---

    def _score_opening(self, body: str) -> int:
        first_para = body.split("\n\n")[0] if body else ""
        first_sentence = first_para.split(".")[0] if first_para else ""

        # Check for banned openings
        for pattern in _BANNED_OPENINGS:
            if re.search(pattern, first_para, re.IGNORECASE):
                return 2

        # Check for data in first sentence and first paragraph
        data_in_sentence = re.findall(
            r"\d+%|\$[\d,.]+|\d+\.?\d*\s*(billion|million|thousand)",
            first_sentence,
            re.IGNORECASE,
        )
        data_in_para = re.findall(
            r"\d+%|\$[\d,.]+|\d+\.?\d*\s*(billion|million|thousand)",
            first_para,
            re.IGNORECASE,
        )
        if len(data_in_sentence) >= 2:
            return 10
        if len(data_in_para) >= 2:
            return 9  # Data-rich opening paragraph
        if len(data_in_sentence) >= 1:
            return 8

        # Has some hook but no data
        if len(first_sentence.split()) > 5:
            return 6

        return 4

    def _detail_opening(self, body: str) -> str:
        first_para = body.split("\n\n")[0] if body else ""
        for pattern in _BANNED_OPENINGS:
            if re.search(pattern, first_para, re.IGNORECASE):
                return f"Banned opening detected: '{pattern}'"
        data_tokens = re.findall(r"\d+%|\$[\d,.]+|\d+", first_para[:200])
        return f"Opening has {len(data_tokens)} data tokens"

    # --- Dimension 2: Evidence Sourcing ---

    # Analyst firms whose reports count toward the 1-per-article cap
    # (skills/research-sourcing/SKILL.md)
    _ANALYST_FIRMS: list[str] = ["gartner", "forrester", "mckinsey", "bcg", "idc"]

    def _score_evidence(self, body: str) -> int:
        score = 10

        # Check for placeholders
        placeholders = len(re.findall(r"\[NEEDS SOURCE\]|\[UNVERIFIED\]", body))
        if placeholders > 0:
            score -= placeholders * 3

        # Check for vague attribution
        vague_count = sum(
            1 for phrase in _VAGUE_ATTRIBUTION if phrase.lower() in body.lower()
        )
        score -= vague_count * 2

        # Check references section
        ref_match = re.search(r"## References\s*\n(.*?)(?=\n##|\Z)", body, re.DOTALL)
        if not ref_match:
            score -= 4
        else:
            refs_text = ref_match.group(1)
            ref_count = len(re.findall(r"^\d+\.", refs_text, re.MULTILINE))
            if ref_count >= 5:
                score += 0  # Already max
            elif ref_count >= 3:
                score -= 1
            else:
                score -= 3

            # Source freshness check (skills/research-sourcing/SKILL.md):
            # At least 3 of 5 references must be from current or previous year.
            current_year = datetime.now().year
            years_in_refs = [
                int(y)
                for y in re.findall(r"\b(20\d{2})\b", refs_text)
                if int(y) <= current_year  # exclude impossible future years
            ]
            fresh_count = sum(1 for y in years_in_refs if y >= current_year - 1)
            if ref_count >= 5 and fresh_count < 3:
                score -= 2  # Penalty: fewer than 3 references are from recent years

            # Analyst report cap (skills/research-sourcing/SKILL.md): max 1 per article
            analyst_count = sum(
                1
                for firm in self._ANALYST_FIRMS
                if re.search(rf"\b{firm}\b", refs_text, re.IGNORECASE)
            )
            if analyst_count > 1:
                score -= analyst_count - 1  # -1 for each analyst report above the cap

        return max(1, min(10, score))

    def _detail_evidence(self, body: str) -> str:
        placeholders = len(re.findall(r"\[NEEDS SOURCE\]|\[UNVERIFIED\]", body))
        ref_match = re.search(r"## References\s*\n(.*?)(?=\n##|\Z)", body, re.DOTALL)
        if not ref_match:
            return f"0 references cited, {placeholders} placeholders"
        refs_text = ref_match.group(1)
        ref_count = len(re.findall(r"^\d+\.", refs_text, re.MULTILINE))
        current_year = datetime.now().year
        years_in_refs = [
            int(y)
            for y in re.findall(r"\b(20\d{2})\b", refs_text)
            if int(y) <= current_year  # exclude impossible future years
        ]
        fresh_count = sum(1 for y in years_in_refs if y >= current_year - 1)
        analyst_count = sum(
            1
            for firm in self._ANALYST_FIRMS
            if re.search(rf"\b{firm}\b", refs_text, re.IGNORECASE)
        )
        return (
            f"{ref_count} references cited, {placeholders} placeholders, "
            f"{fresh_count} fresh (≥{current_year - 1}), {analyst_count} analyst reports"
        )

    # --- Dimension 3: Voice Consistency ---

    def _score_voice(self, body: str) -> int:
        score = 10
        body_lower = body.lower()

        # Check banned phrases
        banned_count = sum(1 for p in _BANNED_PHRASES if p.lower() in body_lower)
        score -= banned_count * 2

        # Check hedging phrases (1 point each — undermine authoritative voice)
        hedging_count = sum(1 for p in _HEDGING_PHRASES if p.lower() in body_lower)
        score -= hedging_count

        # Check American spellings
        american_count = sum(1 for w in _AMERICAN_SPELLINGS if w in body_lower)
        score -= american_count

        # Check exclamation points
        exclamation_count = body.count("!")
        if exclamation_count > 0:
            score -= min(exclamation_count, 3)

        return max(1, min(10, score))

    def _detail_voice(self, body: str) -> str:
        body_lower = body.lower()
        banned = [p for p in _BANNED_PHRASES if p.lower() in body_lower]
        hedging = [p for p in _HEDGING_PHRASES if p.lower() in body_lower]
        american = [w for w in _AMERICAN_SPELLINGS if w in body_lower]
        parts = []
        if banned:
            parts.append(f"banned: {banned}")
        if hedging:
            parts.append(f"hedging: {hedging}")
        if american:
            parts.append(f"American spellings: {american}")
        return ", ".join(parts) if parts else "Clean voice"

    # --- Dimension 4: Structure ---

    def _score_structure(
        self, article: str, frontmatter: dict[str, Any], body: str
    ) -> int:
        score = 10

        # Check frontmatter fields
        missing = [f for f in _REQUIRED_FRONTMATTER if f not in frontmatter]
        score -= len(missing)

        # Check headings — too few or too many both indicate poor structure
        headings = re.findall(r"^#{2,3}\s", body, re.MULTILINE)
        if len(headings) < 2:
            score -= 2
        elif len(headings) > 5:
            score -= 2

        # Check for list formatting in prose (outside References section)
        prose_only = re.sub(r"## References.*", "", body, flags=re.DOTALL | re.IGNORECASE)
        list_items = re.findall(r"^[-*]\s|^\d+\.\s", prose_only, re.MULTILINE)
        if len(list_items) > 2:
            score -= 2

        # Check word count (600 minimum per economist-writing skill)
        word_count = len(body.split())
        if word_count < 600:
            score -= 3
        elif word_count > 1500:
            score -= 1

        # Check references
        if "## references" not in body.lower():
            score -= 2

        # Check for banned closings
        last_500 = body[-500:] if len(body) > 500 else body
        for closing in _BANNED_CLOSINGS:
            if closing.lower() in last_500.lower():
                score -= 1
                break

        return max(1, min(10, score))

    def _detail_structure(self, frontmatter: dict[str, Any], body: str) -> str:
        headings = len(re.findall(r"^#{2,3}\s", body, re.MULTILINE))
        words = len(body.split())
        missing = [f for f in _REQUIRED_FRONTMATTER if f not in frontmatter]
        has_refs = "## references" in body.lower()
        prose_only = re.sub(r"## References.*", "", body, flags=re.DOTALL | re.IGNORECASE)
        list_count = len(re.findall(r"^[-*]\s|^\d+\.\s", prose_only, re.MULTILINE))
        parts = [f"{headings} headings", f"{words} words"]
        if list_count > 0:
            parts.append(f"{list_count} list items in prose")
        if missing:
            parts.append(f"missing: {missing}")
        parts.append("references: yes" if has_refs else "references: no")
        return ", ".join(parts)

    # --- Dimension 5: Visual Engagement ---

    def _score_visual(self, frontmatter: dict[str, Any], body: str) -> int:
        score = 5  # Base score (not every article needs a chart)

        # Image field present
        if frontmatter.get("image"):
            score += 3

        # Chart/image embedded in body (bonus, not required)
        if re.search(r"!\[.*?\]\(.*?\)", body):
            score += 1

        # Chart referenced naturally
        chart_refs = [
            "as the chart",
            "chart shows",
            "chart illustrates",
            "figure shows",
        ]
        if any(ref in body.lower() for ref in chart_refs):
            score += 1

        # Good visual breaks (heading every ~300 words)
        headings = re.findall(r"^#{2,3}\s", body, re.MULTILINE)
        words = len(body.split())
        if headings and words > 0:
            avg_words_between = words / (len(headings) + 1)
            if avg_words_between <= 350:
                score += 1

        return max(1, min(10, score))

    def _detail_visual(self, frontmatter: dict[str, Any], body: str) -> str:
        has_image = bool(frontmatter.get("image"))
        has_chart = bool(re.search(r"!\[.*?\]\(.*?\)", body))
        return f"image: {'yes' if has_image else 'no'}, chart embedded: {'yes' if has_chart else 'no'}"
