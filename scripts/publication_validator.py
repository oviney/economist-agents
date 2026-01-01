#!/usr/bin/env python3
"""
Publication Validator - Final Quality Gate

Blocks publication of articles that don't meet minimum quality standards.
This is the LAST line of defense before an article goes live.

CRITICAL CHECKS (any failure = REJECT):
- No [NEEDS SOURCE] or verification flags
- Valid YAML front matter (--- not code fences)
- Date matches publication date
- Title is specific, not generic
- No placeholder text (TODO, FIXME, XXX)
"""

import re
import yaml
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path


class PublicationValidator:
    """Final quality gate before publication"""
    
    CRITICAL_FAILURES = {
        'VERIFICATION_FLAGS': {
            'severity': 'CRITICAL',
            'message': 'Article contains unverified claims',
            'pattern': r'\[NEEDS SOURCE\]|\[UNVERIFIED\]'
        },
        'YAML_FORMAT': {
            'severity': 'CRITICAL',
            'message': 'YAML front matter improperly formatted',
            'check': 'starts_with_triple_dash'
        },
        'DATE_MISMATCH': {
            'severity': 'CRITICAL',
            'message': 'Article date does not match publication date',
            'check': 'date_validation'
        },
        'GENERIC_TITLE': {
            'severity': 'HIGH',
            'message': 'Title is too generic or missing context',
            'patterns': [
                r'^title:\s*["\']?(Myth vs Reality|The Truth About|A Guide to)',
                r'^title:\s*["\']\w+\s+\w+\s*["\']$'  # Only 2 words
            ]
        },
        'PLACEHOLDER_TEXT': {
            'severity': 'CRITICAL',
            'message': 'Article contains placeholder text',
            'pattern': r'(TODO|FIXME|XXX|REPLACE[-_]?ME|YOUR-\w+)'
        }
    }
    
    def __init__(self, expected_date: str = None):
        """
        Args:
            expected_date: Expected publication date (YYYY-MM-DD). 
                          Defaults to today.
        """
        self.expected_date = expected_date or datetime.now().strftime('%Y-%m-%d')
        self.issues = []
        
    def validate(self, article_content: str, article_path: str = None) -> Tuple[bool, List[Dict]]:
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
        
        # Determine if valid (no CRITICAL issues)
        critical_issues = [i for i in self.issues if i['severity'] == 'CRITICAL']
        is_valid = len(critical_issues) == 0
        
        return is_valid, self.issues
    
    def _check_verification_flags(self, content: str):
        """Check for [NEEDS SOURCE] and [UNVERIFIED] flags"""
        pattern = self.CRITICAL_FAILURES['VERIFICATION_FLAGS']['pattern']
        matches = re.findall(pattern, content)
        
        if matches:
            self.issues.append({
                'check': 'verification_flags',
                'severity': 'CRITICAL',
                'message': f'Found {len(matches)} unverified claims: {set(matches)}',
                'details': 'All [NEEDS SOURCE] and [UNVERIFIED] tags must be resolved',
                'fix': 'Remove flags by adding proper sources or removing unsourced claims'
            })
    
    def _check_yaml_format(self, content: str):
        """Verify YAML front matter uses --- delimiters, not code fences"""
        if content.startswith('```yaml') or content.startswith('```yml'):
            self.issues.append({
                'check': 'yaml_format',
                'severity': 'CRITICAL',
                'message': 'YAML front matter wrapped in code fence',
                'details': 'Jekyll requires front matter to use --- delimiters',
                'fix': 'Replace ```yaml with --- at start and end'
            })
            return
        
        if not content.startswith('---'):
            self.issues.append({
                'check': 'yaml_format',
                'severity': 'CRITICAL',
                'message': 'Missing YAML front matter',
                'details': 'Article must start with --- delimiter',
                'fix': 'Add YAML front matter at top of file'
            })
    
    def _check_date(self, content: str):
        """Validate date matches expected publication date"""
        # Extract front matter
        try:
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 2:
                    front_matter = yaml.safe_load(parts[1])
                    article_date = str(front_matter.get('date', ''))
                    
                    # Normalize date format
                    article_date = article_date.split()[0]  # Remove time if present
                    
                    if article_date != self.expected_date:
                        self.issues.append({
                            'check': 'date_mismatch',
                            'severity': 'CRITICAL',
                            'message': f'Date mismatch: article shows {article_date}, expected {self.expected_date}',
                            'details': 'Publication date must match current date',
                            'fix': f'Update date to {self.expected_date}'
                        })
        except Exception as e:
            self.issues.append({
                'check': 'date_parsing',
                'severity': 'HIGH',
                'message': f'Could not parse date from front matter: {e}',
                'details': 'Ensure date field is properly formatted',
                'fix': 'Check YAML syntax and date format'
            })
    
    def _check_title(self, content: str):
        """Check for generic or low-quality titles"""
        try:
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 2:
                    front_matter = yaml.safe_load(parts[1])
                    title = front_matter.get('title', '')
                    
                    # Check for generic patterns
                    for pattern in self.CRITICAL_FAILURES['GENERIC_TITLE']['patterns']:
                        if re.search(pattern, f'title: "{title}"', re.IGNORECASE):
                            self.issues.append({
                                'check': 'generic_title',
                                'severity': 'HIGH',
                                'message': f'Title too generic: "{title}"',
                                'details': 'Title should be specific and include topic context',
                                'fix': 'Add topic keywords to title (e.g., "Self-Healing Tests: Myth vs Reality")'
                            })
                            break
                    
                    # Check for very short titles (< 3 words unless it's a clever pun)
                    word_count = len(title.split())
                    if word_count < 3 and not any(word in title.lower() for word in ['testing', 'quality', 'code', 'test']):
                        self.issues.append({
                            'check': 'short_title',
                            'severity': 'MEDIUM',
                            'message': f'Title may be too short: "{title}" ({word_count} words)',
                            'details': 'Unless this is a clever pun, consider adding context',
                            'fix': 'Add subtitle or expand title with topic keywords'
                        })
        except Exception:
            pass  # Title check is non-critical if YAML parsing fails
    
    def _check_placeholders(self, content: str):
        """Check for placeholder text that should never be published"""
        pattern = self.CRITICAL_FAILURES['PLACEHOLDER_TEXT']['pattern']
        matches = re.finditer(pattern, content, re.IGNORECASE)
        
        found_placeholders = []
        for match in matches:
            # Get context around match (20 chars before/after)
            start = max(0, match.start() - 20)
            end = min(len(content), match.end() + 20)
            context = content[start:end].replace('\n', ' ')
            found_placeholders.append(f"{match.group()} in: ...{context}...")
        
        if found_placeholders:
            self.issues.append({
                'check': 'placeholder_text',
                'severity': 'CRITICAL',
                'message': f'Found {len(found_placeholders)} placeholder(s)',
                'details': '\n'.join(found_placeholders),
                'fix': 'Remove or replace all placeholder text'
            })
    
    def format_report(self, is_valid: bool, issues: List[Dict]) -> str:
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
            critical = [i for i in issues if i['severity'] == 'CRITICAL']
            high = [i for i in issues if i['severity'] == 'HIGH']
            
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


def validate_file(file_path: str, expected_date: str = None) -> Tuple[bool, str]:
    """
    Validate a file for publication.
    
    Args:
        file_path: Path to article file
        expected_date: Expected publication date (YYYY-MM-DD)
    
    Returns:
        (is_valid, report_text)
    """
    validator = PublicationValidator(expected_date)
    
    with open(file_path, 'r') as f:
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
