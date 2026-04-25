# Bug: Quality gates bypassed — defective article published (oviney/blog@528689d)

**Labels:** `bug`, `priority:critical`, `area:quality-gates`, `area:publication-validator`

---

## Summary

The Flow pipeline auto-committed a post to `oviney/blog` with multiple defects that should have been caught by the editorial / publication validators. The commit message asserted "Editorial score: passed 5/5 quality gates + publication validator", so the gates are either wired up incorrectly or not actually executing.

## Evidence

| Item | Value |
|------|-------|
| Pipeline commit | [oviney/blog@528689d](https://github.com/oviney/blog/commit/528689d) |
| Article | `Platform Engineering's Third Era: The Release Paradox` |
| Author | `Economist Agent Bot <github-actions[bot]>` |
| Take-down PR | oviney/blog#837 |
| Generated file | `_posts/2026-04-21-platform-engineering-s-third-era--the-release-paradox.md` |

## Defects observed

| # | Defect | Likely upstream cause |
|---|--------|----------------------|
| 1 | Closing front-matter `---` delimiter concatenated onto same line as `description:` (`description: "..."---`). Breaks Jekyll YAML parsing. | Template/string-concat bug in front-matter writer — `---` appended without preceding newline when `description` is truncated. |
| 2 | Body references `/assets/charts/platform-engineering-third-era.png` which was not committed. Broken image. | Chart-generation step silently skipped/failed; publication validator does not check that referenced asset paths exist. |
| 3 | Hero image set to fallback `/assets/images/blog-default.svg` instead of generated featured image. | Featured-image step did not run; no validator flags fallback-image usage. |
| 4 | Citation URLs in References section do not resolve (e.g. fabricated `https://github.com/productivity-research`, `https://netflixtechblog.com` article URLs). | Citation validator checks shape only, not that URLs return 2xx. |
| 5 | Mid-paragraph `## Intelligence versus wisdom` header with no preceding blank line; multiple sub-sections collapsed into one paragraph. | Markdown-formatting validator missing or accepts headers after non-blank lines. |
| 6 | British-English over-correction: "elabourate" (should be "elaborate"). | Spell/style pass uses naive `or → our` find-and-replace with no word-list guard against false positives. |

## Pattern context

This is the **fourth post in a row** published by the pipeline that had to be reverted on the blog side:

| Commit | Reason |
|--------|--------|
| `9b8dd98` | Fabricated/unverified citations |
| `9022a84` | Fabricated/unverified citations |
| `fa3fe1d` | Fabricated/unverified citations |
| `528689d` | All of the above + front-matter + asset issues |

The defect surface is widening, which suggests the gates were **never actually validating** these things rather than recently regressing.

## Acceptance criteria

- [ ] **Audit:** Determine which of the 5 gates actually ran on commit `oviney/blog@528689d`. Provide logs/artifacts.
- [ ] **Fix #1:** Front-matter template — closing `---` always on its own line.
- [ ] **Fix #2:** Fail run if any referenced asset path (`image:`, inline `![](...)`, chart paths) is not committed.
- [ ] **Fix #3:** Fail run if any citation URL returns non-2xx (allow-list for known-flaky hosts if needed).
- [ ] **Fix #4:** Markdown-structure check — every `## ` header must be preceded by a blank line.
- [ ] **Fix #5:** Replace naive British-spelling pass with word-list-based transform (or real spell-checker).
- [ ] **Regression tests:** Add test cases for each defect to prevent recurrence.

## Out of scope

Mitigation on blog side (defensive `scripts/validate-posts.sh` checks) tracked separately on `oviney/blog`.

## Files to investigate

- `scripts/publication_validator.py` — the 5-gate validator
- `src/economist_agents/flow.py:quality_gate()` — where gates are invoked
- `src/crews/stage4_crew.py` — editorial review crew
- `scripts/deploy_to_blog.py` — commit/push logic
- `scripts/frontmatter_schema.py` — YAML frontmatter handling

---

*Filed from Claude Code session: https://claude.ai/code/session_015HT5f4zNA8TDqJN57hsDaC*
