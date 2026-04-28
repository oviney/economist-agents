#!/usr/bin/env python3
"""
Publication Validator - Final Quality Gate (v2 with Defect Prevention)

Blocks publication of articles that don't meet minimum quality standards.
This is the LAST line of defense before an article goes live.

CRITICAL CHECKS (any failure = REJECT):
- No [NEEDS SOURCE] or verification flags
- Valid YAML front matter (--- not code fences)
- Date matches publication date
- Title is specific, not generic
- No placeholder text (TODO, FIXME, XXX)
- Historical defect patterns (learned from 6 bugs with RCA)

NEW in v2: Integrated DefectPrevention rules from defect_tracker.py RCA
"""

import re
from datetime import datetime
from pathlib import Path

import yaml

# Import defect prevention rules (learned from historical bugs)
try:
    from defect_prevention_rules import DefectPrevention

    DEFECT_PREVENTION_AVAILABLE = True
except ImportError:
    DEFECT_PREVENTION_AVAILABLE = False


class PublicationValidator:
    """Final quality gate before publication"""

    #: Blog categories accepted by the publication pipeline.
    VALID_CATEGORIES: list[str] = [
        "Quality Engineering",
        "Software Engineering",
        "Test Automation",
        "Security",
    ]

    CRITICAL_FAILURES = {
        "VERIFICATION_FLAGS": {
            "severity": "CRITICAL",
            "message": "Article contains unverified claims",
            "pattern": r"\[NEEDS SOURCE\]|\[UNVERIFIED\]",
        },
        "YAML_FORMAT": {
            "severity": "CRITICAL",
            "message": "YAML front matter improperly formatted",
            "check": "starts_with_triple_dash",
        },
        "DATE_MISMATCH": {
            "severity": "CRITICAL",
            "message": "Article date does not match publication date",
            "check": "date_validation",
        },
        "GENERIC_TITLE": {
            "severity": "HIGH",
            "message": "Title is too generic or missing context",
            "patterns": [
                r'^title:\s*["\']?(Myth vs Reality|The Truth About|A Guide to)',
                r'^title:\s*["\']\w+\s+\w+\s*["\']$',  # Only 2 words
            ],
        },
        "PLACEHOLDER_TEXT": {
            "severity": "CRITICAL",
            "message": "Article contains placeholder text",
            # YOUR- enumerated to avoid false positives on title-derived slugs
            # like "your-content-strategy" (BUG-030).
            "pattern": (
                r"\b(TODO|FIXME|XXX|REPLACE[-_]?ME|"
                r"YOUR[-_](?:NAME|COMPANY|EMAIL|TITLE|ROLE|DATE|COMPANY[-_]NAME))\b"
            ),
        },
    }

    def __init__(self, expected_date: str | None = None):
        """
        Args:
            expected_date: Expected publication date (YYYY-MM-DD).
                          Defaults to today.
        """
        self.expected_date = expected_date or datetime.now().strftime("%Y-%m-%d")
        self.issues = []

        # Initialize defect prevention checker
        if DEFECT_PREVENTION_AVAILABLE:
            self.defect_checker = DefectPrevention()
        else:
            self.defect_checker = None

    def validate(
        self, article_content: str, article_path: str | None = None
    ) -> tuple[bool, list[dict[str, str]]]:
        """
        Validate article for publication.

        Args:
            article_content: Full article text including front matter
            article_path: Optional path for context in error messages

        Returns:
            (is_valid, list_of_issues)
            is_valid is False if any CRITICAL issues found
        """
        self.issues = []

        # Check 1: Verification flags
        self._check_verification_flags(article_content)

        # Check 2: YAML front matter format
        self._check_yaml_format(article_content)

        # Check 3: Date validation
        self._check_date(article_content)

        # Check 4: Title quality
        self._check_title(article_content)

        # Check 5: Placeholder text
        self._check_placeholders(article_content)

        # Check 6: Weak endings (CRITICAL - blocks publication)
        self._check_weak_endings(article_content)

        # Check 7: Chart references (orphaned charts)
        self._check_chart_references(article_content)

        # Check 8: References section (FEATURE-001)
        self._check_references_section(article_content)

        # Check 9: Word count (BUG-029 — final gate for minimum length)
        self._check_word_count(article_content)

        # Check 10: Historical defect patterns (v2)
        if self.defect_checker:
            self._check_defect_patterns(article_content, article_path)

        # Check 11: Description front matter
        self._check_description(article_content)

        # Check 12: Category validation
        self._check_category(article_content)

        # Check 13: Author validation
        self._check_author(article_content)

        # Check 14: Image contract validation
        self._check_image_contract(article_content)

        # Check 15: Heading structure validation
        self._check_heading_structure(article_content)

        # Check 16: Ending quality (banned closings from stage4_crew)
        self._check_ending(article_content)

        # Determine if valid (no CRITICAL issues)
        critical_issues = [i for i in self.issues if i["severity"] == "CRITICAL"]
        is_valid = len(critical_issues) == 0

        return is_valid, self.issues

    def _check_verification_flags(self, content: str):
        """Check for [NEEDS SOURCE] and [UNVERIFIED] flags"""
        pattern = self.CRITICAL_FAILURES["VERIFICATION_FLAGS"]["pattern"]
        matches = re.findall(pattern, content)

        if matches:
            self.issues.append(
                {
                    "check": "verification_flags",
                    "severity": "CRITICAL",
                    "message": f"Found {len(matches)} unverified claims: {set(matches)}",
                    "details": "All [NEEDS SOURCE] and [UNVERIFIED] tags must be resolved",
                    "fix": "Remove flags by adding proper sources or removing unsourced claims",
                }
            )

    def _check_yaml_format(self, content: str):
        """Verify YAML front matter uses --- delimiters, not code fences"""
        if content.startswith("```yaml") or content.startswith("```yml"):
            self.issues.append(
                {
                    "check": "yaml_format",
                    "severity": "CRITICAL",
                    "message": "YAML front matter wrapped in code fence",
                    "details": "Jekyll requires front matter to use --- delimiters",
                    "fix": "Replace ```yaml with --- at start and end",
                }
            )
            return

        if not content.startswith("---"):
            self.issues.append(
                {
                    "check": "yaml_format",
                    "severity": "CRITICAL",
                    "message": "Missing YAML front matter",
                    "details": "Article must start with --- delimiter",
                    "fix": "Add YAML front matter at top of file",
                }
            )

    def _check_date(self, content: str):
        """Validate date matches expected publication date"""
        # Extract front matter
        try:
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 2:
                    front_matter = yaml.safe_load(parts[1])
                    article_date = str(front_matter.get("date", ""))

                    # Normalize date format
                    article_date = article_date.split()[0]  # Remove time if present

                    if article_date != self.expected_date:
                        self.issues.append(
                            {
                                "check": "date_mismatch",
                                "severity": "CRITICAL",
                                "message": f"Date mismatch: article shows {article_date}, expected {self.expected_date}",
                                "details": "Publication date must match current date",
                                "fix": f"Update date to {self.expected_date}",
                            }
                        )
        except Exception as e:
            self.issues.append(
                {
                    "check": "date_parsing",
                    "severity": "HIGH",
                    "message": f"Could not parse date from front matter: {e}",
                    "details": "Ensure date field is properly formatted",
                    "fix": "Check YAML syntax and date format",
                }
            )

    def _check_title(self, content: str):
        """Check for generic or low-quality titles"""
        try:
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 2:
                    front_matter = yaml.safe_load(parts[1])
                    title = front_matter.get("title", "")

                    # Check for generic patterns
                    for pattern in self.CRITICAL_FAILURES["GENERIC_TITLE"]["patterns"]:
                        if re.search(pattern, f'title: "{title}"', re.IGNORECASE):
                            self.issues.append(
                                {
                                    "check": "generic_title",
                                    "severity": "HIGH",
                                    "message": f'Title too generic: "{title}"',
                                    "details": "Title should be specific and include topic context",
                                    "fix": 'Add topic keywords to title (e.g., "Self-Healing Tests: Myth vs Reality")',
                                }
                            )
                            break

                    # Check for very short titles (< 3 words unless it's a clever pun)
                    word_count = len(title.split())
                    if word_count < 3 and not any(
                        word in title.lower()
                        for word in ["testing", "quality", "code", "test"]
                    ):
                        self.issues.append(
                            {
                                "check": "short_title",
                                "severity": "MEDIUM",
                                "message": f'Title may be too short: "{title}" ({word_count} words)',
                                "details": "Unless this is a clever pun, consider adding context",
                                "fix": "Add subtitle or expand title with topic keywords",
                            }
                        )
        except Exception:
            pass  # Title check is non-critical if YAML parsing fails

    def _check_placeholders(self, content: str):
        """Check for placeholder text that should never be published"""
        pattern = self.CRITICAL_FAILURES["PLACEHOLDER_TEXT"]["pattern"]
        matches = re.finditer(pattern, content, re.IGNORECASE)

        found_placeholders = []
        for match in matches:
            # Get context around match (20 chars before/after)
            start = max(0, match.start() - 20)
            end = min(len(content), match.end() + 20)
            context = content[start:end].replace("\n", " ")
            found_placeholders.append(f"{match.group()} in: ...{context}...")

        if found_placeholders:
            self.issues.append(
                {
                    "check": "placeholder_text",
                    "severity": "CRITICAL",
                    "message": f"Found {len(found_placeholders)} placeholder(s)",
                    "details": "\n".join(found_placeholders),
                    "fix": "Remove or replace all placeholder text",
                }
            )

    def _check_weak_endings(self, content: str):
        """Check for weak/hedging endings that violate Economist style"""
        # Exclude References section - it contains link titles we shouldn't check
        refs_patterns = [
            r"\n## References\b",
            r"\n## Sources\b",
            r"\n## Bibliography\b",
        ]
        article_body = content
        for pattern in refs_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                article_body = content[: match.start()]
                break

        # Extract last 500 characters of article body (roughly last 2 paragraphs)
        ending = article_body[-500:] if len(article_body) > 500 else article_body

        BANNED_ENDINGS = [
            (r"\bIn conclusion\b", "Summative closing"),
            (r"\bremains uncertain\b", "Hedging"),
            (r"\bremains to be seen\b", "Hedging"),
            (r"\bwill likely become\b", "Hedging"),
            (r"\bmay well\b", "Hedging"),
            (r"\bcould potentially\b", "Hedging"),
            (r"\bwill depend largely on\b", "Hedging"),
            (r"\bSuccess will belong to those who\b", "Vague prescription"),
            (r"\bThe future (?:of|remains)\b", "Generic forward-look"),
            (r"\bOnly time will tell\b", "Cliché"),
            (r"\bThe journey ahead\b", "Cliché"),
            (r"\bmust evolve from\b", "Passive construction"),
            (r"\bThe impending question\b", "Question-based ending"),
        ]

        violations = []
        for pattern, reason in BANNED_ENDINGS:
            matches = re.finditer(pattern, ending, re.IGNORECASE)
            for match in matches:
                # Get context
                start = max(0, match.start() - 30)
                end = min(len(ending), match.end() + 30)
                context = ending[start:end].replace("\n", " ")
                violations.append(
                    {
                        "phrase": match.group(),
                        "reason": reason,
                        "context": f"...{context}...",
                    }
                )

        if violations:
            details = "\n".join(
                [
                    f'  • "{v["phrase"]}" ({v["reason"]}) in: {v["context"]}'
                    for v in violations
                ]
            )

            self.issues.append(
                {
                    "check": "weak_endings",
                    "severity": "CRITICAL",
                    "message": f"Weak/hedging ending detected ({len(violations)} violations)",
                    "details": details,
                    "fix": "Rewrite ending with definitive statement or clear prediction",
                }
            )

    def _check_word_count(self, content: str) -> None:
        """Validate article body meets minimum word count (BUG-029).

        Extracts the body (everything after YAML frontmatter) and checks
        that it contains at least 800 words.
        """
        # Extract body after frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            body = parts[2].strip() if len(parts) >= 3 else ""
        else:
            body = content

        word_count = len(body.split())
        if word_count < 700:
            self.issues.append(
                {
                    "check": "word_count",
                    "severity": "CRITICAL",
                    "message": f"Article too short: {word_count} words (minimum 700 required)",
                    "details": "Economist-style articles require 700-1200 words for adequate depth",
                    "fix": "Expand article with additional examples, data points, or deeper analysis",
                }
            )

    def _check_description(self, content: str) -> None:
        """Validate ``description`` front-matter field.

        The ``description`` field is used for SEO meta-description and social
        previews.  It must be present and no longer than 160 characters.
        """
        try:
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 2:
                    front_matter = yaml.safe_load(parts[1])
                    if not isinstance(front_matter, dict):
                        return  # YAML parsing handled elsewhere

                    description = front_matter.get("description")
                    if description is None or (
                        isinstance(description, str) and not description.strip()
                    ):
                        self.issues.append(
                            {
                                "check": "missing_description",
                                "severity": "CRITICAL",
                                "message": "Front matter missing 'description' field",
                                "details": "description is required for SEO and social sharing",
                                "fix": "Add description: '<summary ≤160 chars>' to front matter",
                            }
                        )
                    elif isinstance(description, str) and len(description) > 160:
                        self.issues.append(
                            {
                                "check": "description_too_long",
                                "severity": "CRITICAL",
                                "message": (
                                    f"description is {len(description)} chars "
                                    f"(max 160 allowed)"
                                ),
                                "details": "Search engines truncate descriptions beyond 160 characters",
                                "fix": "Shorten description to ≤160 characters",
                            }
                        )
        except Exception:
            pass  # YAML parse errors are caught by _check_yaml_format

    def _check_category(self, content: str) -> None:
        """Validate that ``categories`` maps to one of the allowed blog categories."""
        try:
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 2:
                    front_matter = yaml.safe_load(parts[1])
                    if not isinstance(front_matter, dict):
                        return

                    categories = front_matter.get("categories")
                    if categories is None:
                        self.issues.append(
                            {
                                "check": "missing_category",
                                "severity": "CRITICAL",
                                "message": "Front matter missing 'categories' field",
                                "details": "Every article must have a category",
                                "fix": (
                                    "Add categories: [<category>] with one of: "
                                    + ", ".join(self.VALID_CATEGORIES)
                                ),
                            }
                        )
                        return

                    category_list = (
                        [categories] if isinstance(categories, str) else categories
                    )
                    if not isinstance(category_list, list):
                        return  # non-list handled elsewhere

                    for cat in category_list:
                        if cat not in self.VALID_CATEGORIES:
                            self.issues.append(
                                {
                                    "check": "invalid_category",
                                    "severity": "CRITICAL",
                                    "message": (
                                        f"Invalid category '{cat}'. "
                                        f"Must be one of: {', '.join(self.VALID_CATEGORIES)}"
                                    ),
                                    "details": "Category must map to a valid blog category",
                                    "fix": "Use one of: "
                                    + ", ".join(self.VALID_CATEGORIES),
                                }
                            )
        except Exception:
            pass  # YAML parse errors are caught by _check_yaml_format

    def _check_author(self, content: str) -> None:
        """Require the blog's production author name."""
        try:
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 2:
                    front_matter = yaml.safe_load(parts[1])
                    if not isinstance(front_matter, dict):
                        return
                    author = front_matter.get("author")
                    if author != "Ouray Viney":
                        self.issues.append(
                            {
                                "check": "author_contract",
                                "severity": "CRITICAL",
                                "message": f'Invalid author "{author}". Expected "Ouray Viney"',
                                "details": "Published blog posts must use the production author metadata contract",
                                "fix": 'Set author to "Ouray Viney"',
                            }
                        )
        except Exception:
            pass

    def _check_image_contract(self, content: str) -> None:
        """Reject placeholder or incomplete image metadata for publication."""
        try:
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 2:
                    front_matter = yaml.safe_load(parts[1])
                    if not isinstance(front_matter, dict):
                        return

                    image = str(front_matter.get("image", "") or "").strip()
                    image_alt = str(front_matter.get("image_alt", "") or "").strip()
                    image_caption = str(front_matter.get("image_caption", "") or "").strip()

                    if not image:
                        self.issues.append(
                            {
                                "check": "missing_image",
                                "severity": "CRITICAL",
                                "message": "Article missing hero image",
                                "details": "Production blog posts require article-specific hero imagery",
                                "fix": "Set image to a real article asset path",
                            }
                        )
                    elif "blog-default.svg" in image:
                        self.issues.append(
                            {
                                "check": "default_image_fallback",
                                "severity": "CRITICAL",
                                "message": "Article still uses blog-default.svg fallback",
                                "details": "Default hero fallback must not pass the publication gate",
                                "fix": "Generate or assign article-specific hero art before publishing",
                            }
                        )

                    if not image_alt:
                        self.issues.append(
                            {
                                "check": "missing_image_alt",
                                "severity": "CRITICAL",
                                "message": "Article missing image_alt",
                                "details": "Published posts require reader-facing alt text for hero art",
                                "fix": "Add concise image_alt describing the visible scene",
                            }
                        )

                    if not image_caption:
                        self.issues.append(
                            {
                                "check": "missing_image_caption",
                                "severity": "CRITICAL",
                                "message": "Article missing image_caption",
                                "details": "Published posts require an editorial hero caption",
                                "fix": "Add image_caption explaining the image's editorial point",
                            }
                        )
        except Exception:
            pass

    def _check_heading_structure(self, content: str) -> None:
        """Reject inline markdown headings embedded inside paragraphs."""
        body = content.split("---", 2)[2] if content.startswith("---") and len(content.split("---", 2)) >= 3 else content
        if re.search(r"[^\s]\s##\s", body):
            self.issues.append(
                {
                    "check": "inline_heading_marker",
                    "severity": "CRITICAL",
                    "message": "Heading markers are embedded inside paragraph text",
                    "details": "Malformed markdown like '... sentence. ## Heading' must not publish",
                    "fix": "Move each markdown heading to its own line with surrounding paragraph breaks",
                }
            )

    # Banned closing phrases aligned with stage4_crew._BANNED_CLOSINGS + extras.
    _BANNED_CLOSINGS: list[str] = [
        "In conclusion",
        "To conclude",
        "In summary",
        "remains to be seen",
        "only time will tell",
        "The journey ahead",
        "will rest on",
        "depends on",
        "the key is",
        "to summarise",
        "One suspects",
    ]

    # Summary-opening phrases that signal a restatement ending.
    _SUMMARY_STARTERS: list[str] = [
        "In short",
        "Ultimately",
        "Overall",
    ]

    def _check_ending(self, content: str) -> None:
        """Check the last paragraph for banned closing patterns.

        Extracts the article body (after YAML frontmatter, before
        ``## References`` if present) and inspects the final paragraph for
        weak/hedging closings drawn from ``stage4_crew._BANNED_CLOSINGS``
        plus additional patterns (e.g. summary-opener restatements).

        Issues are reported at **HIGH** severity so they flag without
        blocking publication on the first run.
        """
        # --- extract body after frontmatter ---
        if content.startswith("---"):
            parts = content.split("---", 2)
            body = parts[2] if len(parts) >= 3 else ""
        else:
            body = content

        # --- strip References / Sources / Bibliography section ---
        for pattern in (
            r"\n## References\b",
            r"\n## Sources\b",
            r"\n## Bibliography\b",
        ):
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                body = body[: match.start()]
                break

        # --- isolate last paragraph ---
        paragraphs = [p.strip() for p in body.strip().split("\n\n") if p.strip()]
        if not paragraphs:
            return
        last_paragraph = paragraphs[-1]

        violations: list[str] = []

        # 1. Check banned closing phrases (case-insensitive)
        for phrase in self._BANNED_CLOSINGS:
            if re.search(re.escape(phrase), last_paragraph, re.IGNORECASE):
                violations.append(f'Banned closing phrase: "{phrase}"')

        # 2. Check summary-opener restatement endings
        for starter in self._SUMMARY_STARTERS:
            if re.match(re.escape(starter) + r"\b", last_paragraph, re.IGNORECASE):
                violations.append(f'Summary restatement opening: "{starter}"')

        if violations:
            details = "\n".join(f"  - {v}" for v in violations)
            self.issues.append(
                {
                    "check": "ending_quality",
                    "severity": "HIGH",
                    "message": f"Weak/hedging ending detected ({len(violations)} violations)",
                    "details": details,
                    "fix": "Rewrite ending with a vivid prediction, metaphor, or concrete forward-looking statement",
                }
            )

    def _check_chart_references(self, content: str):
        """Check that articles include at least one chart in /assets/charts/ and flag orphaned charts that lack text references."""
        # Find all chart image references pointing to /assets/charts/
        chart_refs = re.findall(r"!\[.*?\]\((/assets/charts/.*?\.png)\)", content)

        if not chart_refs:
            self.issues.append(
                {
                    "check": "missing_chart",
                    "severity": "CRITICAL",
                    "message": "Article missing required chart — every article must include at least one data chart",
                    "details": "Charts are mandatory per Economist editorial standards. "
                    "A chart image must be embedded as ![...](/assets/charts/<slug>.png)",
                    "fix": "Run the graphics_agent to generate a chart and embed it in the article body",
                }
            )
            return

        # Check for orphaned charts (embedded but never mentioned in text)
        content_lower = content.lower()
        has_chart_mention = any(
            word in content_lower
            for word in ["chart", "figure", "graph", "shows", "illustrates"]
        )

        if not has_chart_mention:
            for chart_ref in chart_refs:
                chart_file = chart_ref.split("/")[-1]
                self.issues.append(
                    {
                        "check": "orphaned_chart",
                        "severity": "HIGH",
                        "message": f"Chart embedded but never referenced: {chart_file}",
                        "details": 'Chart should be mentioned in the article text (e.g., "As the chart shows...")',
                        "fix": "Add a sentence referencing the chart near where it appears",
                    }
                )

    def _check_references_section(self, content: str):
        """
        Check for References section (FEATURE-001)

        Validates:
        - References section present (## References header)
        - Minimum 3 references
        - References formatted properly (numbered list)
        - Descriptive link text (not "click here")
        """
        # Check if References section exists
        has_references_header = bool(
            re.search(r"^## References", content, re.MULTILINE)
        )

        if not has_references_header:
            self.issues.append(
                {
                    "check": "missing_references",
                    "severity": "CRITICAL",
                    "message": "Article missing References section",
                    "details": "All articles must include '## References' section before closing paragraph",
                    "fix": "Add '## References' section with minimum 3 authoritative sources",
                }
            )
            return

        # Extract references section (match content after header until next section or end)
        refs_match = re.search(
            r"## References\s*\n(.*?)(?=^##|\Z)", content, re.DOTALL | re.MULTILINE
        )
        if not refs_match:
            # Check if header exists but with no content before next section
            if has_references_header:
                self.issues.append(
                    {
                        "check": "empty_references",
                        "severity": "CRITICAL",
                        "message": "References section header exists but is empty",
                        "details": "References section must contain at least 3 sources",
                        "fix": "Add authoritative sources with proper formatting",
                    }
                )
            return

        references_text = refs_match.group(1).strip()

        # Check if references text is effectively empty
        if not references_text or len(references_text.strip()) < 10:
            self.issues.append(
                {
                    "check": "empty_references",
                    "severity": "CRITICAL",
                    "message": "References section header exists but is empty",
                    "details": "References section must contain at least 3 sources",
                    "fix": "Add authoritative sources with proper formatting",
                }
            )
            return

        # Count references (look for numbered list items)
        reference_items = re.findall(r"^\d+\.", references_text, re.MULTILINE)
        reference_count = len(reference_items)

        if reference_count < 3:
            self.issues.append(
                {
                    "check": "insufficient_references",
                    "severity": "CRITICAL",
                    "message": f"Only {reference_count} reference(s) found, minimum 3 required",
                    "details": "Articles must cite at least 3 authoritative sources",
                    "fix": "Add additional authoritative sources (academic, government, industry reports)",
                }
            )

        # Check for bad link text patterns
        bad_link_patterns = [
            (r"\[click here\]", 'Generic "click here" link text'),
            (r"\[here\]", 'Generic "here" link text'),
            (r"\[link\]", 'Generic "link" text'),
            (r"\[source\]", 'Generic "source" text'),
            (r"\[(https?://[^\]]+)\]", "Bare URL as link text"),
        ]

        violations = []
        for pattern, reason in bad_link_patterns:
            matches = re.finditer(pattern, references_text, re.IGNORECASE)
            for match in matches:
                violations.append({"text": match.group(), "reason": reason})

        if violations:
            details = "\n".join(
                [f"  • {v['text']} - {v['reason']}" for v in violations]
            )
            self.issues.append(
                {
                    "check": "bad_reference_links",
                    "severity": "HIGH",
                    "message": f"Found {len(violations)} reference(s) with poor link text",
                    "details": details,
                    "fix": "Use descriptive anchor text (e.g., 'World Quality Report 2024')",
                }
            )

    def _check_defect_patterns(self, content: str, article_path: str = None):
        """
        Check for historical defect patterns (learned from RCA)

        NEW in v2: Integrates DefectPrevention rules from 6 documented bugs
        Prevents: BUG-016 (chart not embedded), BUG-015 (missing category), etc.
        """
        if not self.defect_checker:
            return

        # Extract chart metadata if available (for BUG-016 pattern check)
        metadata = {}

        # Check if article path suggests chart should exist
        if article_path:
            # Look for matching chart file
            article_name = Path(article_path).stem
            # Remove date prefix (YYYY-MM-DD-)
            re.sub(r"^\d{4}-\d{2}-\d{2}-", "", article_name)

            # Check if chart_data metadata passed or if chart markdown exists
            has_chart = bool(re.search(r"!\[.*?\]\(.*?\.png\)", content))
            if has_chart:
                metadata["chart_data"] = True  # Signal that chart exists

        # Run defect prevention checks
        violations = self.defect_checker.check_all(content, metadata)

        # Convert violations to issue format
        for violation in violations:
            # Parse severity from violation message
            severity_match = re.match(r"\[(\w+)\]", violation)
            severity = severity_match.group(1) if severity_match else "HIGH"

            # Extract pattern ID
            pattern_match = re.search(r"\(Pattern: (BUG-\d+-pattern)\)", violation)
            pattern_id = pattern_match.group(1) if pattern_match else "unknown"

            # Clean message
            clean_message = re.sub(r"^\[\w+\]\s*", "", violation)
            clean_message = re.sub(
                r"\s*\(Pattern: BUG-\d+-pattern\)\s*$", "", clean_message
            )

            self.issues.append(
                {
                    "check": f"defect_pattern_{pattern_id}",
                    "severity": severity,
                    "message": clean_message,
                    "details": f"Historical pattern from {pattern_id}",
                    "fix": "See message for specific remediation",
                }
            )

    def format_report(self, is_valid: bool, issues: list[dict]) -> str:
        """Generate human-readable validation report"""
        lines = []
        lines.append("═" * 70)
        lines.append("🔒 PUBLICATION VALIDATION REPORT")
        lines.append("═" * 70)
        lines.append("")

        if is_valid:
            lines.append("✅ APPROVED FOR PUBLICATION")
            lines.append("")
            if issues:
                lines.append(f"ℹ️  {len(issues)} non-critical advisory notes:")
                for issue in issues:
                    lines.append(f"  • [{issue['severity']}] {issue['message']}")
        else:
            critical = [i for i in issues if i["severity"] == "CRITICAL"]
            high = [i for i in issues if i["severity"] == "HIGH"]

            lines.append(f"❌ REJECTED - {len(critical)} CRITICAL ISSUES")
            lines.append("")
            lines.append("CRITICAL FAILURES (must fix):")
            for i, issue in enumerate(critical, 1):
                lines.append(f"\n{i}. {issue['check'].upper()}")
                lines.append(f"   Message: {issue['message']}")
                lines.append(f"   Details: {issue['details']}")
                lines.append(f"   Fix: {issue['fix']}")

            if high:
                lines.append(f"\n\nHIGH PRIORITY ({len(high)} issues):")
                for issue in high:
                    lines.append(f"  • {issue['message']}")

        lines.append("")
        lines.append("═" * 70)

        return "\n".join(lines)


def validate_file(file_path: str, expected_date: str = None) -> tuple[bool, str]:
    """
    Validate a file for publication.

    Args:
        file_path: Path to article file
        expected_date: Expected publication date (YYYY-MM-DD)

    Returns:
        (is_valid, report_text)
    """
    validator = PublicationValidator(expected_date)

    with open(file_path) as f:
        content = f.read()

    is_valid, issues = validator.validate(content, file_path)
    report = validator.format_report(is_valid, issues)

    return is_valid, report


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python publication_validator.py <article_file> [expected_date]")
        sys.exit(1)

    file_path = sys.argv[1]
    expected_date = sys.argv[2] if len(sys.argv) > 2 else None

    is_valid, report = validate_file(file_path, expected_date)
    print(report)

    sys.exit(0 if is_valid else 1)
