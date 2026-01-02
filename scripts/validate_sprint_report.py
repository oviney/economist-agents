#!/usr/bin/env python3
"""
Sprint Report Validator

Validates sprint reports have proper GitHub links for all file references.
Enforces convention from docs/conventions/SPRINT_REPORT_SPEC.md

Usage:
    python3 scripts/validate_sprint_report.py docs/RETROSPECTIVE_S7.md
    python3 scripts/validate_sprint_report.py --check-all
"""

import re
import sys
from pathlib import Path


class SprintReportValidator:
    """Validate sprint reports have GitHub links for file references"""

    def __init__(self, repo_owner: str = "oviney", repo_name: str = "economist-agents"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_base = f"https://github.com/{repo_owner}/{repo_name}"

    def validate_report(self, report_path: Path) -> tuple[bool, list[str]]:
        """Validate sprint report has proper GitHub links"""
        issues = []

        with open(report_path) as f:
            content = f.read()

        # Pattern 1: File mentions without links (WRONG)
        # Look for: scripts/file.py, docs/file.md
        # But NOT if already in a markdown link [text](url) or [file](file)
        file_pattern = r"(?<!\[)(?<!\()(?:scripts|docs|skills|\.github)/[\w\-/]+\.(?:py|md|yml|json)"

        for match in re.finditer(file_pattern, content):
            file_path = match.group(0)
            # Check if this is part of a markdown link
            # Get surrounding context
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context = content[start:end]

            # If surrounded by [text](url) or [file](file), it's OK
            if not (
                "](" in context[: match.start() - start]
                and ")" in context[match.end() - start :]
            ):
                issues.append(
                    f"File reference without GitHub link: {file_path}\n"
                    f"  Should be: [{file_path}]({self.github_base}/blob/main/{file_path})"
                )

        # Pattern 2: Line number mentions without links
        # Look for: "Line 123", "lines 45-67", "at line X"
        line_pattern = r"(?:line|lines)\s+(\d+)(?:-(\d+))?"

        for match in re.finditer(line_pattern, content, re.IGNORECASE):
            # Check if preceded by a file reference
            start = max(0, match.start() - 100)
            preceding = content[start : match.start()]

            # Look for file path in preceding text
            file_match = re.search(
                r"(scripts|docs|skills|\.github)/[\w\-/]+\.(?:py|md|yml|json)",
                preceding,
            )

            if file_match:
                file_path = file_match.group(0)
                line_start = match.group(1)

                # Check if already in link
                if "](" not in content[match.start() - 10 : match.start()]:
                    issues.append(
                        f"Line reference without GitHub link: {file_path} line {line_start}\n"
                        f"  Should be: [{file_path}]({self.github_base}/blob/main/{file_path}#L{line_start})"
                    )

        # Pattern 3: Generic file mentions (file.py without path)
        # These should be expanded with full path
        generic_file_pattern = r"(?<!\[)(?<!/)(\w+\.(?:py|md|yml|json))(?!\))"

        for match in re.finditer(generic_file_pattern, content):
            filename = match.group(1)
            # Skip common words that happen to look like files
            if filename not in ["README.md", "TODO.md"]:
                # Check if in link context
                start = max(0, match.start() - 20)
                end = min(len(content), match.end() + 20)
                context = content[start:end]

                if "](" not in context[: match.start() - start]:
                    issues.append(
                        f"Generic file reference without path: {filename}\n"
                        f"  Should specify full path: scripts/{filename} or docs/{filename}\n"
                        f"  And link to GitHub"
                    )

        return len(issues) == 0, issues

    def check_all_reports(self) -> dict:
        """Check all retrospective and sprint reports"""
        results = {}

        # Check retrospectives
        retro_dir = Path("docs")
        for retro_file in retro_dir.glob("RETROSPECTIVE_S*.md"):
            is_valid, issues = self.validate_report(retro_file)
            results[str(retro_file)] = {"valid": is_valid, "issues": issues}

        # Check sprint completion reports
        for sprint_file in retro_dir.glob("SPRINT_*_COMPLETION.md"):
            is_valid, issues = self.validate_report(sprint_file)
            results[str(sprint_file)] = {"valid": is_valid, "issues": issues}

        # Check sprint final reports
        for report_file in retro_dir.glob("SPRINT_*_FINAL_REPORT.md"):
            is_valid, issues = self.validate_report(report_file)
            results[str(report_file)] = {"valid": is_valid, "issues": issues}

        return results


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate sprint reports have GitHub links"
    )
    parser.add_argument("report", nargs="?", help="Path to report file to validate")
    parser.add_argument(
        "--check-all", action="store_true", help="Check all sprint reports"
    )

    args = parser.parse_args()

    validator = SprintReportValidator()

    if args.check_all:
        print("🔍 Checking all sprint reports...\n")
        results = validator.check_all_reports()

        valid_count = sum(1 for r in results.values() if r["valid"])
        total_count = len(results)

        for report_path, result in results.items():
            if result["valid"]:
                print(f"✅ {report_path}")
            else:
                print(f"❌ {report_path}")
                for issue in result["issues"][:3]:  # Show first 3 issues
                    print(f"   {issue}")

        print(f"\n📊 Results: {valid_count}/{total_count} reports valid")

        if valid_count < total_count:
            sys.exit(1)

    elif args.report:
        report_path = Path(args.report)

        if not report_path.exists():
            print(f"❌ Report not found: {report_path}")
            sys.exit(1)

        print(f"🔍 Validating {report_path}...\n")

        is_valid, issues = validator.validate_report(report_path)

        if is_valid:
            print("✅ Report has proper GitHub links")
        else:
            print(f"❌ Found {len(issues)} issues:\n")
            for issue in issues:
                print(f"   {issue}\n")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
