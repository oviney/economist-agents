#!/usr/bin/env python3
"""
Environment Validation Script

Validates technical prerequisites before sprint work begins.
Checks Python version, dependency compatibility, and critical imports.

Usage:
    python3 scripts/validate_environment.py
    python3 scripts/validate_environment.py --strict  # Fail on warnings
    python3 scripts/validate_environment.py --deps crewai anthropic  # Check specific deps

Sprint 7 Lesson Learned: Automated prerequisite validation prevents
costly mid-sprint blockers (3-hour Python 3.14 incompatibility delay).
"""

import argparse
import importlib
import platform
import subprocess
import sys
from pathlib import Path


class EnvironmentValidator:
    """Validates development environment prerequisites"""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.issues: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []

    def validate_all(self) -> bool:
        """Run all validation checks"""
        print("=" * 60)
        print("ENVIRONMENT VALIDATION")
        print("=" * 60 + "\n")

        self.check_python_version()
        self.check_requirements_installable()
        self.check_critical_imports()
        self.check_known_issues()

        return self.report_results()

    def check_python_version(self) -> None:
        """Validate Python version meets requirements"""
        print("📍 Python Version Check")

        version = sys.version_info
        current = f"{version.major}.{version.minor}.{version.micro}"

        print(f"   Current: Python {current}")

        # Check requirements.txt for version constraints
        requirements_file = Path(__file__).parent.parent / "requirements.txt"
        if requirements_file.exists():
            with open(requirements_file) as f:
                content = f.read()
                if "python_requires" in content or "Python >=" in content:
                    print("   ℹ️  Check requirements.txt for version constraints")

        # Known version constraints (Sprint 7 lesson)
        if version.major == 3 and version.minor >= 14:
            self.issues.append(
                {
                    "severity": "CRITICAL",
                    "category": "Python Version",
                    "issue": f"Python {current} may be incompatible with some dependencies",
                    "details": "CrewAI requires Python <=3.13 (Sprint 7 blocker)",
                    "fix": "Use pyenv to create Python 3.13 environment: pyenv install 3.13.0",
                }
            )
            print(f"   ❌ CRITICAL: Python {current} incompatible with CrewAI")
        elif version.major == 3 and version.minor >= 10:
            print(f"   ✅ Python {current} (compatible)")
        else:
            self.issues.append(
                {
                    "severity": "HIGH",
                    "category": "Python Version",
                    "issue": f"Python {current} too old",
                    "details": "Requires Python 3.10+",
                    "fix": "Upgrade to Python 3.13",
                }
            )
            print(f"   ❌ Python {current} too old (need 3.10+)")

    def check_requirements_installable(self) -> None:
        """Check if all requirements can be installed"""
        print("\n📦 Dependencies Check")

        requirements_file = Path(__file__).parent.parent / "requirements.txt"
        if not requirements_file.exists():
            print("   ⚠️  No requirements.txt found")
            return

        print(f"   Checking: {requirements_file}")

        try:
            # Try dry-run install
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--dry-run",
                    "-r",
                    str(requirements_file),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                print("   ✅ All dependencies installable")
            else:
                error = result.stderr.strip()
                self.issues.append(
                    {
                        "severity": "HIGH",
                        "category": "Dependencies",
                        "issue": "Some dependencies cannot be installed",
                        "details": error[:200],
                        "fix": "Review requirements.txt for version conflicts",
                    }
                )
                print("   ❌ Dependency installation issues")
                print(f"      {error[:100]}")

        except subprocess.TimeoutExpired:
            self.warnings.append(
                {
                    "severity": "MEDIUM",
                    "category": "Dependencies",
                    "issue": "Dependency check timed out (>30s)",
                    "fix": "Run manually: pip install --dry-run -r requirements.txt",
                }
            )
            print("   ⚠️  Dependency check timed out")
        except Exception as e:
            print(f"   ⚠️  Could not validate dependencies: {e}")

    def check_critical_imports(self) -> None:
        """Test imports for critical dependencies"""
        print("\n🔍 Critical Imports Check")

        critical_modules = [
            ("anthropic", "Anthropic API client"),
            ("yaml", "YAML parsing (PyYAML)"),
            ("matplotlib", "Chart generation"),
            ("slugify", "URL slug generation"),
        ]

        # Optional modules (warnings only)
        optional_modules = [
            ("crewai", "CrewAI framework (Sprint 7+)"),
            ("openai", "OpenAI API (optional)"),
        ]

        for module_name, description in critical_modules:
            try:
                importlib.import_module(module_name)
                print(f"   ✅ {module_name:15} ({description})")
            except ImportError:
                self.issues.append(
                    {
                        "severity": "CRITICAL",
                        "category": "Missing Dependency",
                        "issue": f"Cannot import {module_name}",
                        "details": description,
                        "fix": f"pip install {module_name}",
                    }
                )
                print(f"   ❌ {module_name:15} MISSING")

        for module_name, description in optional_modules:
            try:
                importlib.import_module(module_name)
                print(f"   ✅ {module_name:15} ({description})")
            except ImportError:
                self.warnings.append(
                    {
                        "severity": "LOW",
                        "category": "Optional Dependency",
                        "issue": f"Optional module {module_name} not available",
                        "details": description,
                    }
                )
                print(f"   ⚠️  {module_name:15} (optional, not installed)")

    def check_known_issues(self) -> None:
        """Check for known compatibility issues"""
        print("\n⚠️  Known Issues Check")

        # Sprint 7 Lesson: CrewAI + Python 3.14 incompatibility
        version = sys.version_info
        if version.major == 3 and version.minor >= 14:
            try:
                importlib.import_module("crewai")
                self.warnings.append(
                    {
                        "severity": "HIGH",
                        "category": "Version Incompatibility",
                        "issue": "CrewAI installed with Python 3.14+",
                        "details": "CrewAI requires Python <=3.13 (may fail at runtime)",
                        "fix": "Create Python 3.13 environment: pyenv install 3.13.0 && pyenv local 3.13.0",
                    }
                )
                print("   ⚠️  CrewAI installed but Python version incompatible")
            except ImportError:
                print("   ℹ️  CrewAI not installed (OK for Python 3.14+)")
        else:
            print("   ✅ No known version incompatibilities")

        # Check OS-specific issues
        os_name = platform.system()
        if os_name == "Darwin":  # macOS
            print(f"   ℹ️  Platform: {os_name} (macOS)")
        elif os_name == "Linux":
            print(f"   ℹ️  Platform: {os_name}")
        else:
            self.warnings.append(
                {
                    "severity": "MEDIUM",
                    "category": "Platform",
                    "issue": f"Untested platform: {os_name}",
                    "details": "Project primarily tested on macOS/Linux",
                }
            )
            print(f"   ⚠️  Platform: {os_name} (untested)")

    def report_results(self) -> bool:
        """Print validation report and return success status"""
        print("\n" + "=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60 + "\n")

        if self.issues:
            print(f"❌ {len(self.issues)} CRITICAL ISSUES FOUND:\n")
            for i, issue in enumerate(self.issues, 1):
                print(f"{i}. [{issue['severity']}] {issue['category']}")
                print(f"   Issue: {issue['issue']}")
                print(f"   Details: {issue['details']}")
                if "fix" in issue:
                    print(f"   Fix: {issue['fix']}")
                print()

        if self.warnings:
            print(f"⚠️  {len(self.warnings)} WARNINGS:\n")
            for i, warning in enumerate(self.warnings, 1):
                print(f"{i}. [{warning['severity']}] {warning['category']}")
                print(f"   {warning['issue']}")
                if "fix" in warning:
                    print(f"   Recommended: {warning['fix']}")
                print()

        if not self.issues and not self.warnings:
            print("✅ ALL CHECKS PASSED\n")
            print("Environment ready for sprint work.")
            return True
        elif not self.issues and self.warnings:
            if self.strict:
                print(
                    "❌ VALIDATION FAILED (strict mode, warnings treated as errors)\n"
                )
                return False
            else:
                print("✅ VALIDATION PASSED (with warnings)\n")
                print("Review warnings above but safe to proceed.")
                return True
        else:
            print("❌ VALIDATION FAILED\n")
            print("Fix critical issues above before starting sprint work.")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Validate development environment prerequisites"
    )
    parser.add_argument(
        "--strict", action="store_true", help="Treat warnings as errors"
    )
    parser.add_argument(
        "--deps",
        nargs="+",
        help="Check specific dependencies (e.g., crewai anthropic)",
    )

    args = parser.parse_args()

    validator = EnvironmentValidator(strict=args.strict)

    if args.deps:
        print(f"Checking specific dependencies: {', '.join(args.deps)}\n")
        for dep in args.deps:
            try:
                importlib.import_module(dep)
                print(f"✅ {dep} importable")
            except ImportError:
                print(f"❌ {dep} MISSING")
        return

    success = validator.validate_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
