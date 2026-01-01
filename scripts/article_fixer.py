#!/usr/bin/env python3
"""
Smart Article Fixer

Automatically fixes common validation failures without regenerating the entire article.
Saves OpenAI credits by fixing issues in-place when possible.

Fixable Issues:
1. Wrong YAML format (```yaml → ---)
2. Wrong date (updates to current date)
3. Generic titles (prompts for better title)
4. [NEEDS SOURCE] flags (prompts to remove or source)

Non-fixable (requires regeneration):
- Missing research data
- Poor content quality
- Structural issues
"""

import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from publication_validator import PublicationValidator


class ArticleFixer:
    """Smart fixer for common validation failures"""
    
    def __init__(self):
        self.fixes_applied = []
        
    def auto_fix(self, content: str, expected_date: str = None) -> Tuple[str, List[str], bool]:
        """
        Attempt to automatically fix common issues.
        
        Args:
            content: Article content
            expected_date: Expected publication date (YYYY-MM-DD)
        
        Returns:
            (fixed_content, list_of_fixes_applied, needs_human_review)
        """
        self.fixes_applied = []
        fixed = content
        needs_review = False
        
        # Fix 1: YAML format (```yaml → ---)
        if fixed.startswith('```yaml') or fixed.startswith('```yml'):
            fixed = self._fix_yaml_format(fixed)
            self.fixes_applied.append("Fixed YAML format (removed code fences)")
        
        # Fix 2: Date mismatch
        if expected_date:
            fixed, date_fixed = self._fix_date(fixed, expected_date)
            if date_fixed:
                self.fixes_applied.append(f"Updated date to {expected_date}")
        
        # Fix 3: Generic title (flag for review)
        if self._has_generic_title(fixed):
            needs_review = True
            self.fixes_applied.append("⚠️  Title is generic - needs manual review")
        
        # Fix 4: [NEEDS SOURCE] flags (flag for review)
        source_count = fixed.count('[NEEDS SOURCE]')
        if source_count > 0:
            needs_review = True
            self.fixes_applied.append(f"⚠️  {source_count} [NEEDS SOURCE] flags - needs manual review")
        
        # Fix 5: Placeholder text (flag for review)
        placeholders = re.findall(r'(TODO|FIXME|XXX|REPLACE[-_]?ME|YOUR-\w+)', fixed, re.IGNORECASE)
        if placeholders:
            needs_review = True
            self.fixes_applied.append(f"⚠️  Found placeholders: {set(placeholders)} - needs manual review")
        
        return fixed, self.fixes_applied, needs_review
    
    def _fix_yaml_format(self, content: str) -> str:
        """Convert ```yaml code fence to --- delimiters"""
        # Pattern: ```yaml\n...content...\n```
        pattern = r'^```ya?ml\s*\n(.*?)\n```'
        match = re.match(pattern, content, re.DOTALL)
        
        if match:
            yaml_content = match.group(1)
            rest_of_content = content[match.end():]
            return f"---\n{yaml_content}\n---{rest_of_content}"
        
        return content
    
    def _fix_date(self, content: str, expected_date: str) -> Tuple[str, bool]:
        """Update date in YAML front matter"""
        try:
            if not content.startswith('---'):
                return content, False
            
            parts = content.split('---', 2)
            if len(parts) < 3:
                return content, False
            
            front_matter = yaml.safe_load(parts[1])
            
            # Check if date needs updating
            current_date = str(front_matter.get('date', '')).split()[0]
            if current_date == expected_date:
                return content, False
            
            # Update date
            front_matter['date'] = expected_date
            
            # Reconstruct content
            new_yaml = yaml.dump(front_matter, default_flow_style=False, sort_keys=False)
            return f"---\n{new_yaml}---{parts[2]}", True
            
        except Exception as e:
            print(f"   ⚠️  Could not auto-fix date: {e}")
            return content, False
    
    def _has_generic_title(self, content: str) -> bool:
        """Check if title is generic"""
        try:
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 2:
                    front_matter = yaml.safe_load(parts[1])
                    title = front_matter.get('title', '')
                    
                    # Check for generic patterns
                    generic_patterns = [
                        r'Myth vs Reality',
                        r'^The Truth About',
                        r'^A Guide to',
                        r'^\w+\s+\w+$'  # Only 2 words
                    ]
                    
                    for pattern in generic_patterns:
                        if re.search(pattern, title, re.IGNORECASE):
                            return True
        except Exception:
            pass
        
        return False


def fix_quarantined_article(article_path: str, expected_date: str = None) -> bool:
    """
    Attempt to fix a quarantined article.
    
    Args:
        article_path: Path to quarantined article
        expected_date: Expected publication date (YYYY-MM-DD)
    
    Returns:
        True if article was fixed and validated, False otherwise
    """
    if expected_date is None:
        expected_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\n🔧 Attempting to fix: {Path(article_path).name}")
    print("=" * 70)
    
    # Read article
    with open(article_path, 'r') as f:
        content = f.read()
    
    # Apply fixes
    fixer = ArticleFixer()
    fixed_content, fixes, needs_review = fixer.auto_fix(content, expected_date)
    
    print("\n✅ Fixes Applied:")
    for fix in fixes:
        print(f"   • {fix}")
    
    if not fixes:
        print("   • No automatic fixes available")
    
    # Validate fixed version
    print("\n🔍 Re-validating...")
    validator = PublicationValidator(expected_date)
    is_valid, issues = validator.validate(fixed_content)
    
    if is_valid:
        print("\n✅ VALIDATION PASSED!")
        print(f"   Article is now ready for publication")
        
        # Save fixed version
        output_path = str(Path(article_path).parent.parent / Path(article_path).name)
        with open(output_path, 'w') as f:
            f.write(fixed_content)
        
        print(f"   Saved to: {output_path}")
        return True
    else:
        print("\n❌ Still has issues:")
        critical = [i for i in issues if i['severity'] == 'CRITICAL']
        for issue in critical:
            print(f"   • {issue['check']}: {issue['message']}")
        
        if needs_review:
            print("\n⚠️  Manual review required")
            print("   Some issues cannot be fixed automatically")
        
        return False


def batch_fix_quarantine(quarantine_dir: str = "output/quarantine", expected_date: str = None):
    """Fix all articles in quarantine directory"""
    quarantine_path = Path(quarantine_dir)
    
    if not quarantine_path.exists():
        print(f"Quarantine directory not found: {quarantine_dir}")
        return
    
    articles = list(quarantine_path.glob("*.md"))
    
    if not articles:
        print("No articles in quarantine")
        return
    
    print(f"\n🔧 Batch Fixing {len(articles)} Quarantined Articles")
    print("=" * 70)
    
    fixed_count = 0
    for article_path in articles:
        if fix_quarantined_article(str(article_path), expected_date):
            fixed_count += 1
        print()
    
    print("=" * 70)
    print(f"✅ Fixed {fixed_count}/{len(articles)} articles")
    print("=" * 70)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Fix single article:")
        print("    python article_fixer.py <article.md> [expected_date]")
        print()
        print("  Fix all quarantined articles:")
        print("    python article_fixer.py --batch [expected_date]")
        sys.exit(1)
    
    if sys.argv[1] == "--batch":
        expected_date = sys.argv[2] if len(sys.argv) > 2 else None
        batch_fix_quarantine(expected_date=expected_date)
    else:
        article_path = sys.argv[1]
        expected_date = sys.argv[2] if len(sys.argv) > 2 else None
        
        success = fix_quarantined_article(article_path, expected_date)
        sys.exit(0 if success else 1)
