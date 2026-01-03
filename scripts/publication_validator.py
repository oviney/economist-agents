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
            "pattern": r"(TODO|FIXME|XXX|REPLACE[-_]?ME|YOUR-\w+)",
        },
    }

    def __init__(self, expected_date: str = None):
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
        self, article_content: str, article_path: str = None
    ) -> tuple[bool, list[dict]]:
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

        # Check 7: Chart references
        self._check_chart_references(article_content)

        # Check 8: References section (FEATURE-001)
        self._check_references_section(article_content)

        # Check 9: Historical defect patterns (v2)
        if self.defect_checker:
            self._check_defect_patterns(article_content, article_path)

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
        # Extract last 500 characters (roughly last 2 paragraphs)
        ending = content[-500:] if len(content) > 500 else content

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

    def _check_chart_references(self, content: str):
        """Check for orphaned charts (embedded but never mentioned in text)"""
        # Find all chart image references
        chart_refs = re.findall(r"!\[.*?\]\((.*?\.png)\)", content)

        if chart_refs:
            # Check if "chart" is mentioned in the text
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
        has_references_header = bool(re.search(r'^## References', content, re.MULTILINE))
        
        if not has_references_header:
            self.issues.append({
                "check": "missing_references",
                "severity": "CRITICAL",
                "message": "Article missing References section",
                "details": "All articles must include '## References' section before closing paragraph",
                "fix": "Add '## References' section with minimum 3 authoritative sources",
            })
            return
        
        # Extract references section (match content after header until next section or end)
        refs_match = re.search(r'## References\s*\n(.*?)(?=^##|\Z)', content, re.DOTALL | re.MULTILINE)
        if not refs_match:
            # Check if header exists but with no content before next section
            if has_references_header:
                self.issues.append({
                    "check": "empty_references",
                    "severity": "CRITICAL",
                    "message": "References section header exists but is empty",
                    "details": "References section must contain at least 3 sources",
                    "fix": "Add authoritative sources with proper formatting",
                })
            return
        
        references_text = refs_match.group(1).strip()
        
        # Check if references text is effectively empty
        if not references_text or len(references_text.strip()) < 10:
            self.issues.append({
                "check": "empty_references",
                "severity": "CRITICAL",
                "message": "References section header exists but is empty",
                "details": "References section must contain at least 3 sources",
                "fix": "Add authoritative sources with proper formatting",
            })
            return
        
        # Count references (look for numbered list items)
        reference_items = re.findall(r'^\d+\.', references_text, re.MULTILINE)
        reference_count = len(reference_items)
        
        if reference_count < 3:
            self.issues.append({
                "check": "insufficient_references",
                "severity": "CRITICAL",
                "message": f"Only {reference_count} reference(s) found, minimum 3 required",
                "details": "Articles must cite at least 3 authoritative sources",
                "fix": "Add additional authoritative sources (academic, government, industry reports)",
            })
        
        # Check for bad link text patterns
        bad_link_patterns = [
            (r'\[click here\]', 'Generic "click here" link text'),
            (r'\[here\]', 'Generic "here" link text'),
            (r'\[link\]', 'Generic "link" text'),
            (r'\[source\]', 'Generic "source" text'),
            (r'\[(https?://[^\]]+)\]', 'Bare URL as link text'),
        ]
        
        violations = []
        for pattern, reason in bad_link_patterns:
            matches = re.finditer(pattern, references_text, re.IGNORECASE)
            for match in matches:
                violations.append({
                    "text": match.group(),
                    "reason": reason
                })
        
        if violations:
            details = "\n".join([f"  • {v['text']} - {v['reason']}" for v in violations])
            self.issues.append({
                "check": "bad_reference_links",
                "severity": "HIGH",
                "message": f"Found {len(violations)} reference(s) with poor link text",
                "details": details,
                "fix": "Use descriptive anchor text (e.g., 'World Quality Report 2024')",
            })

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
