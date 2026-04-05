#!/usr/bin/env python3
"""Editorial Judge Feedback Loop (Story #118).

When the editorial judge detects failures, this module:
1. Logs the failure pattern to a persistent store
2. Generates prevention rules from recurring patterns
3. Checks new articles against known failure patterns
4. Escalates recurring failures for human review

Usage:
    from scripts.feedback_loop import FeedbackLoop

    loop = FeedbackLoop()
    loop.log_failure({"check_name": "image_exists", "status": "fail", ...})
    rules = loop.generate_prevention_rules()
    warnings = loop.check_article(article_text)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Escalation threshold — patterns seen this many times trigger escalation
ESCALATION_THRESHOLD = 3

# Known check names → article validation functions
_CHECK_VALIDATORS: dict[str, Any] = {}


@dataclass
class PatternRecord:
    """A logged failure pattern from the editorial judge."""

    check_name: str
    message: str
    article_filename: str
    timestamp: str = ""
    status: str = "fail"

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict[str, str]:
        return {
            "check_name": self.check_name,
            "message": self.message,
            "article_filename": self.article_filename,
            "timestamp": self.timestamp,
            "status": self.status,
        }


class FeedbackLoop:
    """Feedback loop connecting editorial judge failures to prevention rules."""

    def __init__(self, patterns_file: str = "logs/defect_patterns.json") -> None:
        self._patterns_file = Path(patterns_file)
        self._patterns: list[PatternRecord] = []
        self._load_patterns()

    def _load_patterns(self) -> None:
        """Load existing patterns from file."""
        if self._patterns_file.exists():
            try:
                import orjson

                data = orjson.loads(self._patterns_file.read_bytes())
                self._patterns = [PatternRecord(**p) for p in data.get("patterns", [])]
            except Exception:
                self._patterns = []

    def _save_patterns(self) -> None:
        """Persist patterns to file."""
        import orjson

        self._patterns_file.parent.mkdir(parents=True, exist_ok=True)
        data = {"patterns": [p.to_dict() for p in self._patterns]}
        self._patterns_file.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))

    def log_failure(self, failure: dict[str, str]) -> PatternRecord:
        """Log a failure from the editorial judge.

        Args:
            failure: Dict with check_name, status, message, article_filename.

        Returns:
            The created PatternRecord.
        """
        record = PatternRecord(
            check_name=failure.get("check_name", "unknown"),
            message=failure.get("message", ""),
            article_filename=failure.get("article_filename", ""),
            status=failure.get("status", "fail"),
        )
        self._patterns.append(record)
        self._save_patterns()
        logger.info(
            "Logged failure pattern: %s (%s)", record.check_name, record.message
        )
        return record

    def get_patterns(self) -> list[PatternRecord]:
        """Get all logged patterns."""
        return list(self._patterns)

    def generate_prevention_rules(self) -> list[dict[str, Any]]:
        """Generate prevention rules from logged patterns.

        Groups patterns by check_name, counts occurrences, and
        generates a rule for each unique pattern.

        Returns:
            List of rule dicts with id, description, check_name, occurrence_count.
        """
        from collections import Counter

        counts: Counter[str] = Counter(p.check_name for p in self._patterns)
        rules: list[dict[str, Any]] = []

        for check_name, count in counts.items():
            # Find the most recent message for this check
            latest = next(
                p for p in reversed(self._patterns) if p.check_name == check_name
            )
            rules.append(
                {
                    "id": f"FEEDBACK-{check_name}",
                    "description": latest.message,
                    "check_name": check_name,
                    "occurrence_count": count,
                    "first_seen": min(
                        p.timestamp
                        for p in self._patterns
                        if p.check_name == check_name
                    ),
                    "last_seen": latest.timestamp,
                }
            )

        return rules

    def check_article(self, article: str) -> list[str]:
        """Check a new article against known failure patterns.

        Applies deterministic checks based on previously seen patterns.

        Args:
            article: Full article text with YAML frontmatter.

        Returns:
            List of warning messages for matched patterns.
        """
        warnings: list[str] = []
        known_checks = {p.check_name for p in self._patterns}

        if "frontmatter" in known_checks:
            # Check for missing layout field (most common frontmatter failure)
            if article.startswith("---"):
                parts = article.split("---", 2)
                if len(parts) >= 3:
                    fm_text = parts[1]
                    if "layout:" not in fm_text:
                        warnings.append(
                            "Known pattern: missing layout field in frontmatter "
                            "(previously caused deployment failure)"
                        )
                    if "categories:" not in fm_text:
                        warnings.append(
                            "Known pattern: missing categories field in frontmatter "
                            "(previously caused missing tags)"
                        )
            else:
                warnings.append(
                    "Known pattern: article missing YAML frontmatter entirely"
                )

        if "image_exists" in known_checks and article.startswith("---"):
            # Check for image field pointing to likely-missing file
            parts = article.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1]) or {}
                    image = fm.get("image", "")
                    if image and "blog-default" not in image:
                        warnings.append(
                            f"Known pattern: custom image path '{image}' — "
                            f"verify file exists before deployment"
                        )
                except yaml.YAMLError:
                    pass

        if "writing_quality" in known_checks:
            # Check for common writing failures
            body = article.split("---", 2)[2] if article.count("---") >= 2 else article
            if "[NEEDS SOURCE]" in body or "[UNVERIFIED]" in body:
                warnings.append(
                    "Known pattern: verification placeholders left in article"
                )

        if "structure" in known_checks:
            body = article.split("---", 2)[2] if article.count("---") >= 2 else article
            if "## References" not in body and "## references" not in body.lower():
                warnings.append(
                    "Known pattern: missing References section "
                    "(previously caused publication rejection)"
                )

        return warnings

    def get_escalations(self) -> list[dict[str, Any]]:
        """Get patterns that have recurred enough to warrant escalation.

        Returns:
            List of escalation dicts for patterns seen >= ESCALATION_THRESHOLD times.
        """
        from collections import Counter

        counts: Counter[str] = Counter(p.check_name for p in self._patterns)
        escalations: list[dict[str, Any]] = []

        for check_name, count in counts.items():
            if count >= ESCALATION_THRESHOLD:
                latest = next(
                    p for p in reversed(self._patterns) if p.check_name == check_name
                )
                escalations.append(
                    {
                        "check_name": check_name,
                        "occurrence_count": count,
                        "message": latest.message,
                        "action": f"Pattern '{check_name}' has occurred {count} times — "
                        f"requires human review to determine root cause fix",
                    }
                )

        return escalations
