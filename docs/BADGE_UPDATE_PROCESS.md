# Badge Update Process

**Purpose**: Keep README badges synchronized with actual project metrics (resolves BUG-023).

## Problem

README badges were showing stale/incorrect data:
- Quality score: 98/100 → Actually 67/100
- Sprint: 7 → Actually 9
- Tests: Not shown → 77 tests exist
- No automation → manual updates required

## Solution

Automated badge synchronization from live data sources.

## Data Sources

| Badge | Source | Update Method |
|-------|--------|---------------|
| **Quality Score** | `quality_dashboard.py` output | Auto-sync to `quality_score.json` |
| **Test Count** | `grep '^def test_' tests/*.py` | Direct badge update |
| **Sprint** | `skills/sprint_tracker.json` | Read `current_sprint` field |
| **Coverage** | pytest-cov (future) | CI artifact |

## Manual Update

```bash
# Validate badges (dry-run)
python3 scripts/update_badges.py --validate-only

# Update all badges
python3 scripts/update_badges.py

# Preview changes without applying
python3 scripts/update_badges.py --dry-run
```

## Automated Update

### Pre-Commit Hook (Recommended)

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Validate badge accuracy before commit
python3 scripts/update_badges.py --validate-only

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Badge validation failed!"
    echo "Run: python3 scripts/update_badges.py"
    exit 1
fi
```

### GitHub Actions (CI/CD)

Create `.github/workflows/badge-update.yml`:

```yaml
name: Update Badges

on:
  push:
    branches: [main]
  schedule:
    # Daily at 00:00 UTC
    - cron: '0 0 * * *'

jobs:
  update-badges:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Update badges
        run: python3 scripts/update_badges.py

      - name: Commit changes
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add README.md quality_score.json
          git diff --quiet && git diff --staged --quiet || \
            git commit -m "chore: Update badges with live data"
          git push
```

## Badge Configuration

### Quality Score (shields.io endpoint)

Uses `quality_score.json` as dynamic data source:

```json
{
  "schemaVersion": 1,
  "label": "quality",
  "message": "67/100",
  "color": "yellow"
}
```

Badge markdown:
```markdown
[![Quality Score](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/oviney/economist-agents/main/quality_score.json)](https://github.com/oviney/economist-agents/blob/main/docs/QUALITY_DASHBOARD.md)
```

Color thresholds:
- ≥90: `brightgreen`
- ≥70: `green`
- ≥50: `yellow`
- <50: `orange`

### Test Count (static badge)

Badge markdown:
```markdown
![Tests](https://img.shields.io/badge/tests-77_passing-brightgreen)
```

Updated by: `update_badges.py` (counts `def test_` in `tests/*.py`)

### Sprint (static badge)

Badge markdown:
```markdown
![Sprint](https://img.shields.io/badge/sprint-9-blue)
```

Updated by: `update_badges.py` (reads `skills/sprint_tracker.json`)

## Validation Checklist

Before committing badge changes:

- [ ] Quality score matches `quality_dashboard.py` output
- [ ] Test count matches actual test functions
- [ ] Sprint matches `sprint_tracker.json`
- [ ] All badge links work (no 404s)
- [ ] `quality_score.json` color matches score threshold

## Troubleshooting

**Badge shows old value after update:**
- shields.io caches badges for ~5 minutes
- Force refresh: Add `?timestamp=...` to URL
- Wait 5-10 minutes for cache invalidation

**Test count incorrect:**
- Verify pytest can find tests: `pytest --collect-only`
- Check test naming: must be `def test_*` in `tests/*.py`

**Quality score mismatch:**
- Run `python3 scripts/quality_dashboard.py`
- Check defect_tracker.json has latest data
- Verify agent_metrics.json exists

**Sprint badge wrong:**
- Check `skills/sprint_tracker.json` → `current_sprint`
- Run `python3 scripts/sprint_ceremony_tracker.py --report`

## Future Enhancements

1. **Coverage Badge** (HIGH)
   - Add pytest-cov integration
   - Upload coverage to codecov.io
   - Dynamic badge from CI artifact

2. **GitHub Actions Badge** (MEDIUM)
   - Already exists, validate accuracy
   - Link to workflow runs

3. **Defect Escape Rate Badge** (LOW)
   - Show current escape rate %
   - Color: green (<20%), yellow (20-40%), red (>40%)

4. **Agent Performance Badge** (LOW)
   - Show Writer/Editor/Graphics health
   - Aggregate gate pass rate

## Related Documentation

- [QUALITY_DASHBOARD.md](QUALITY_DASHBOARD.md) - Quality metrics source
- [DEFECT_PREVENTION.md](DEFECT_PREVENTION.md) - Prevention system
- [SPRINT_CEREMONY_GUIDE.md](SPRINT_CEREMONY_GUIDE.md) - Sprint tracking

## Version History

**v1.0 (2026-01-02)**: Initial implementation
- Automated badge sync for quality, tests, sprint
- Pre-commit validation
- Documentation complete
- Resolves BUG-023 (Issue #38)
