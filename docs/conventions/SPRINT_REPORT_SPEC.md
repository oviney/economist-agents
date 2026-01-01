# Sprint Report Specification

**Version**: 1.0  
**Created**: January 1, 2026  
**Purpose**: Define quality standards for sprint completion reports

---

## Overview

Sprint reports document deliverables and validate completeness. This spec ensures reports are actionable, verifiable, and linkable on GitHub.

---

## Required Sections

### 1. Executive Summary

**Requirements**:
- ✅ Date, Status, Points delivered
- ✅ Quality score (numerical)
- ✅ Goals achieved (checklist)

**Validation**:
```yaml
status: ["COMPLETE", "PARTIALLY_COMPLETE", "FAILED"]
points: "X/Y (Z%)"
quality: "A+ (98/100)" # Must include numerical score
```

### 2. Deliverables (Per Story)

**Requirements**:
- ✅ Story number and points
- ✅ Status (COMPLETE/INCOMPLETE)
- ✅ **Files created/modified with LINE NUMBERS**
- ✅ **GitHub links to all artifacts**
- ✅ Validation results (if applicable)

**CRITICAL**: Every file mentioned MUST have a clickable GitHub link.

**Link Format**:
```markdown
# ✅ CORRECT
- [scripts/economist_agent.py](https://github.com/oviney/economist-agents/blob/main/scripts/economist_agent.py#L1042-L1056)
- [skills/agent_metrics.json](https://github.com/oviney/economist-agents/blob/main/skills/agent_metrics.json)

# ❌ WRONG - No link
- scripts/economist_agent.py (+70 lines)
- skills/agent_metrics.json (working)
```

**Line Number Links**:
```markdown
# Single line
[file.py#L42](https://github.com/owner/repo/blob/main/file.py#L42)

# Range
[file.py#L42-L56](https://github.com/owner/repo/blob/main/file.py#L42-L56)
```

### 3. Testing Summary

**Requirements**:
- ✅ Test commands executed
- ✅ Test results (pass/fail with evidence)
- ✅ **Links to test output files**
- ✅ Quality metrics if applicable

**Evidence Format**:
```markdown
**Test Results**:
- ✅ Research Agent: 3 verified data points
- ✅ Metrics: [agent_metrics.json](https://github.com/.../agent_metrics.json)
```

### 4. Commit Details

**Requirements**:
- ✅ Commit SHA (7 chars)
- ✅ **GitHub commit link**
- ✅ Files changed count
- ✅ Insertions/deletions count
- ✅ Push confirmation

**Link Format**:
```markdown
**Commit**: [`b46870c`](https://github.com/oviney/economist-agents/commit/b46870c)
```

### 5. Metrics Comparison

**Requirements**:
- ✅ Sprint-to-sprint comparison table
- ✅ At least 5 metrics
- ✅ Direction indicators (⬆️⬇️=)

### 6. Known Issues

**Requirements**:
- ✅ Issue description
- ✅ Priority (P0/P1/P2)
- ✅ **GitHub issue link** (if created)
- ✅ Action items

### 7. Next Steps

**Requirements**:
- ✅ GitHub issues to close (with links)
- ✅ Sprint N+1 recommendations
- ✅ Backlog priorities

---

## Validation Checklist

Use this checklist to validate sprint reports before committing:

### Files & Links

- [ ] Every file mentioned has a GitHub link
- [ ] All links tested (no 404 errors)
- [ ] Line number links point to correct ranges
- [ ] Commit links resolve correctly
- [ ] Issue links resolve correctly

### Content Quality

- [ ] Executive summary complete
- [ ] All stories documented
- [ ] Testing evidence provided
- [ ] Metrics comparison included
- [ ] Known issues documented
- [ ] Next steps defined

### GitHub Integration

- [ ] Report committed to git
- [ ] Report accessible on GitHub
- [ ] All linked files exist in repository
- [ ] Commit references correct in report

### Completeness

- [ ] No "TBD" or placeholder text
- [ ] All sections filled out
- [ ] Quality score numerical and justified
- [ ] Retrospective reference included

---

## Link Construction Template

For economist-agents repository:

```bash
# Base URL
BASE="https://github.com/oviney/economist-agents/blob/main"

# File link
${BASE}/path/to/file.py

# File with line
${BASE}/path/to/file.py#L42

# File with range
${BASE}/path/to/file.py#L42-L56

# Commit link
https://github.com/oviney/economist-agents/commit/${COMMIT_SHA}

# Issue link
https://github.com/oviney/economist-agents/issues/${ISSUE_NUM}

# Pull request link
https://github.com/oviney/economist-agents/pull/${PR_NUM}
```

---

## Common Violations

### ❌ Missing Links

```markdown
# WRONG
**Files Modified**:
- scripts/economist_agent.py (+70 lines)
- skills/agent_metrics.json (working)
```

```markdown
# CORRECT
**Files Modified**:
- [`scripts/economist_agent.py`](https://github.com/oviney/economist-agents/blob/main/scripts/economist_agent.py) (+70 lines)
- [`skills/agent_metrics.json`](https://github.com/oviney/economist-agents/blob/main/skills/agent_metrics.json) (working)
```

### ❌ Vague File References

```markdown
# WRONG
- Modified economist_agent.py (tracking added)
```

```markdown
# CORRECT
- [`scripts/economist_agent.py#L1042-L1056`](https://github.com/oviney/economist-agents/blob/main/scripts/economist_agent.py#L1042-L1056) - Research Agent tracking
- [`scripts/economist_agent.py#L1176-L1184`](https://github.com/oviney/economist-agents/blob/main/scripts/economist_agent.py#L1176-L1184) - Writer Agent tracking
```

### ❌ No Test Evidence

```markdown
# WRONG
**Test Results**: All tests passed ✅
```

```markdown
# CORRECT
**Test Results**:
- ✅ Research Agent: 3 verified data points
- ✅ Writer Agent: 535 words, [output file](https://github.com/.../output/2026-01-01-article.md)
- ✅ Metrics: [agent_metrics.json](https://github.com/.../agent_metrics.json)
```

### ❌ Broken Issue References

```markdown
# WRONG
Closes #19, #14
```

```markdown
# CORRECT
Closes [#19](https://github.com/oviney/economist-agents/issues/19), [#14](https://github.com/oviney/economist-agents/issues/14)
```

---

## Validation Script

```python
#!/usr/bin/env python3
"""Validate sprint report against spec"""

import re
from pathlib import Path

def validate_sprint_report(report_path):
    """Check if sprint report meets specification"""
    with open(report_path) as f:
        content = f.read()
    
    issues = []
    
    # Check for file mentions without links
    file_patterns = [
        r'scripts/\w+\.py',
        r'docs/\w+\.md',
        r'skills/\w+\.json',
    ]
    
    for pattern in file_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            # Check if this file mention has a link
            link_pattern = rf'\[.*{re.escape(match)}.*\]\(https://github\.com'
            if not re.search(link_pattern, content):
                issues.append(f"File mentioned without link: {match}")
    
    # Check for commit SHAs without links
    commit_shas = re.findall(r'Commit[:\s]+`?([a-f0-9]{7})`?', content, re.IGNORECASE)
    for sha in commit_shas:
        link_pattern = rf'\[`?{sha}`?\]\(https://github\.com.*commit/{sha}\)'
        if not re.search(link_pattern, content):
            issues.append(f"Commit SHA without link: {sha}")
    
    # Check for issue numbers without links
    issue_nums = re.findall(r'#(\d+)', content)
    for num in issue_nums:
        link_pattern = rf'\[#?{num}\]\(https://github\.com.*issues/{num}\)'
        if not re.search(link_pattern, content):
            issues.append(f"Issue number without link: #{num}")
    
    # Check required sections
    required_sections = [
        'Executive Summary',
        'Deliverables',
        'Testing Summary',
        'Commit Details',
        'Metrics Comparison',
        'Known Issues',
        'Next Steps',
    ]
    
    for section in required_sections:
        if section not in content:
            issues.append(f"Missing required section: {section}")
    
    return issues

if __name__ == '__main__':
    import sys
    report = sys.argv[1] if len(sys.argv) > 1 else 'SPRINT_4_COMPLETE.md'
    issues = validate_sprint_report(report)
    
    if issues:
        print(f"❌ {len(issues)} issues found:")
        for issue in issues:
            print(f"  • {issue}")
        sys.exit(1)
    else:
        print("✅ Sprint report meets specification")
        sys.exit(0)
```

---

## Skills Integration

Add to `skills/blog_qa_skills.json`:

```json
{
  "sprint_report_quality": {
    "description": "Sprint reports must have clickable GitHub links to all artifacts",
    "patterns": [
      {
        "id": "missing_artifact_links",
        "severity": "high",
        "pattern": "File mentioned in report but no GitHub link provided",
        "check": "Scan for file paths without accompanying [text](https://github.com/...) links",
        "learned_from": "Sprint 4 report - no links to generated artifacts"
      },
      {
        "id": "broken_commit_references",
        "severity": "high",
        "pattern": "Commit SHA mentioned but not linked",
        "check": "All commit SHAs must be clickable links to GitHub commits",
        "learned_from": "Sprint 4 report validation"
      },
      {
        "id": "unlinked_issues",
        "severity": "medium",
        "pattern": "Issue numbers mentioned without links",
        "check": "All #XX references must link to GitHub issues",
        "learned_from": "Sprint 4 report validation"
      }
    ]
  }
}
```

---

## Enforcement

**Pre-commit Hook**:
```bash
#!/bin/bash
# .git/hooks/pre-commit

# Validate sprint reports
for report in SPRINT_*_COMPLETE.md; do
    if git diff --cached --name-only | grep -q "$report"; then
        python3 scripts/validate_sprint_report.py "$report"
        if [ $? -ne 0 ]; then
            echo "❌ Sprint report validation failed"
            exit 1
        fi
    fi
done
```

**GitHub Actions**:
```yaml
- name: Validate Sprint Reports
  run: |
    for report in SPRINT_*_COMPLETE.md; do
      python3 scripts/validate_sprint_report.py "$report"
    done
```

---

## Example: Perfect Sprint Report

See: `docs/conventions/SPRINT_REPORT_EXAMPLE.md`

---

## Version History

**v1.0** (2026-01-01)
- Initial specification
- Learned from Sprint 4 bug: missing artifact links
- Added validation script template
- Defined required sections and link formats

---

**Next Review**: After Sprint 5 (validate spec effectiveness)
