# Chart Quality Metrics Report

**Generated:** 2026-01-01 12:40:31
**Last Updated:** 2026-01-01T12:39:58.818154

## Summary Metrics

| Metric | Value |
|--------|-------|
| Total Charts Generated | 2 |
| Visual QA Runs | 2 |
| Visual QA Pass Rate | 50.0% |
| Visual QA Passed | 1 |
| Visual QA Failed | 1 |
| Total Zone Violations | 2 |
| Avg Zone Violations/Chart | 1.00 |
| Total Regenerations | 1 |
| Avg Generation Time | 0.11s |

## Top Failure Patterns

| Rank | Count | Type | Issue |
|------|-------|------|-------|
| 1 | 1 | zone_violation | title overlaps red bar |
| 2 | 1 | zone_violation | inline label intrudes into x-axis zone |
| 3 | 1 | critical_issue | zone boundary violation: title/red bar overlap |
| 4 | 1 | critical_issue | zone boundary violation: label in x-axis zone |

## Trend Analysis

*Insufficient data for trend analysis (need 2+ sessions)*

## Recommendations

- ⚠️  **Low QA Pass Rate**: Visual QA pass rate below 80% - review agent prompts
- ⚠️  **Zone Violations**: High rate of zone violations - strengthen layout rules in prompt
- ⚠️  **High Regeneration Rate**: >30% regeneration rate - improve first-attempt quality
- 🎯 **Top Issue**: 'zone_violation' (1x) - prioritize fix
