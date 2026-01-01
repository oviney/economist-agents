#!/usr/bin/env python3
"""
README Badge Updater

Automatically updates badge values in README.md based on actual metrics:
- Quality Score (from quality_score.json)
- Test Pass Rate (from test execution)
- Sprint Status (from sprint_history.json)

Usage:
    python3 scripts/update_readme_badges.py
    
This should be run as part of the build/CI process to keep badges current.
"""

import re
import json
from pathlib import Path
from datetime import datetime


def get_quality_score():
    """Get current quality score from quality_score.json"""
    score_file = Path(__file__).parent.parent / "quality_score.json"
    
    if score_file.exists():
        with open(score_file, 'r') as f:
            data = json.load(f)
            return data['message'], data['color']
    
    return "unknown", "lightgrey"


def get_test_status():
    """Get test pass rate from test execution"""
    # Run the test to get current status
    import subprocess
    
    try:
        result = subprocess.run(
            ['python3', 'tests/test_quality_system.py'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=30
        )
        
        output = result.stdout + result.stderr
        
        if '11/11 tests passed' in output or 'Total: 11/11' in output:
            return "11/11 passing", "brightgreen"
        elif 'tests passed' in output:
            match = re.search(r'(\d+)/(\d+) tests passed', output)
            if match:
                passed, total = match.group(1), match.group(2)
                if int(passed) == int(total):
                    return f"{passed}/{total} passing", "brightgreen"
                elif int(passed) >= int(total) * 0.8:
                    return f"{passed}/{total} passing", "yellow"
                else:
                    return f"{passed}/{total} passing", "red"
        
        return "status unknown", "lightgrey"
    except Exception as e:
        print(f"⚠️  Could not determine test status: {e}")
        return "status unknown", "lightgrey"


def get_sprint_status():
    """Get current sprint status from sprint_history.json"""
    sprint_file = Path(__file__).parent.parent / "skills" / "sprint_history.json"
    
    if sprint_file.exists():
        with open(sprint_file, 'r') as f:
            data = json.load(f)
            if data['sprints']:
                latest_sprint = data['sprints'][-1]
                sprint_id = latest_sprint['sprint_id']
                status = latest_sprint.get('status', 'active')
                
                if status == 'complete':
                    return f"{sprint_id} complete", "green"
                else:
                    return f"{sprint_id} active", "orange"
    
    return "no sprint", "lightgrey"


def update_readme_badges():
    """Update badges in README.md with current values"""
    readme_path = Path(__file__).parent.parent / "README.md"
    
    if not readme_path.exists():
        print("❌ README.md not found")
        return False
    
    print("\n" + "="*60)
    print("README BADGE UPDATER")
    print("="*60 + "\n")
    
    # Get current metrics
    quality_score, quality_color = get_quality_score()
    test_status, test_color = get_test_status()
    sprint_status, sprint_color = get_sprint_status()
    
    print(f"📊 Quality Score: {quality_score} ({quality_color})")
    print(f"🧪 Tests: {test_status} ({test_color})")
    print(f"🏃 Sprint: {sprint_status} ({sprint_color})")
    
    # Read README
    with open(readme_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Update Quality Score badge
    content = re.sub(
        r'\[!\[Quality Score\]\(https://img\.shields\.io/badge/quality-[^)]+\)',
        f'[![Quality Score](https://img.shields.io/badge/quality-{quality_score}-{quality_color}?style=flat-square)',
        content
    )
    
    # Update Tests badge
    content = re.sub(
        r'\[!\[Tests\]\(https://img\.shields\.io/badge/tests-[^)]+\)',
        f'[![Tests](https://img.shields.io/badge/tests-{test_status.replace(" ", "%20")}-{test_color}?style=flat-square)',
        content
    )
    
    # Update Sprint badge
    content = re.sub(
        r'\[!\[Sprint\]\(https://img\.shields\.io/badge/sprint-[^)]+\)',
        f'[![Sprint](https://img.shields.io/badge/sprint-{sprint_status.replace(" ", "%20")}-{sprint_color}?style=flat-square)',
        content
    )
    
    # Check if changes were made
    if content != original_content:
        # Write updated README
        with open(readme_path, 'w') as f:
            f.write(content)
        
        print("\n✅ README.md badges updated successfully")
        print(f"   Updated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
    else:
        print("\n⏭️  No changes needed - badges already current")
        return False


if __name__ == "__main__":
    success = update_readme_badges()
    exit(0 if success else 1)
