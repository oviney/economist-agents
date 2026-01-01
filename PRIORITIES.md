# Prioritized Backlog & Next Actions

**Last Updated**: 2026-01-01

## 🔴 P0: Production Bugs (Blocking)

**None currently** - All identified bugs fixed or documented.

## 🟠 P1: High Priority (Next Sprint)

### #15: Missing Category Tag on Article Pages
- **Type**: Bug
- **Impact**: UX inconsistency, navigation broken
- **Effort**: Small (1-2 hours)
- **Next Action**: 
  1. Investigate Jekyll template (_layouts/post.html)
  2. Check if front matter has categories field
  3. Add category rendering to template
  4. Test on all articles
- **Owner**: TBD

## 🟡 P2: Medium Priority (Quality Improvements)

### #7: Visual QA Metrics Tracking
- **Type**: Enhancement
- **Impact**: Better chart quality monitoring
- **Effort**: Small
- **Dependencies**: None

### #6: Chart Regression Tests
- **Type**: Enhancement
- **Impact**: Prevent chart rendering bugs
- **Effort**: Large
- **Dependencies**: None

## 🟢 P3: Future Enhancements

### #14: GenAI Featured Image Generation
- **Type**: Feature
- **Impact**: Visual appeal, brand consistency
- **Effort**: Medium (2-3 days)
- **Dependencies**: DALL-E 3 API
- **Next Action**: Design prompt template, implement Image Agent

### #10: Expand Skills Categories
- **Type**: Enhancement
- **Effort**: Medium

### #9: Anti-Pattern Detection
- **Type**: Enhancement
- **Effort**: Medium

### #8: Integration Tests
- **Type**: Enhancement
- **Effort**: Large

## 🔵 P4: Nice to Have

### #12: CONTRIBUTING.md
- **Type**: Documentation
- **Effort**: Small

### #11: Pre-commit Architecture Review
- **Type**: Enhancement
- **Effort**: Small

---

## 📋 Recommended Next Action

**IMMEDIATE (Today)**: Fix Issue #15 - Missing Category Tag

**Why this is next:**
1. ✅ Bug is already documented with screenshot
2. ✅ Small effort (1-2 hours)
3. ✅ High user-facing impact (every article page)
4. ✅ Completes today's bug fix cycle (3/3 bugs fixed)
5. ✅ Low risk (template-only change)

**Implementation Plan:**
```bash
# 1. Clone blog repo and create fix branch
git clone https://github.com/oviney/blog.git
cd blog
git checkout -b fix-missing-category-tag

# 2. Update _layouts/post.html
# Add category display in breadcrumb area:
# {% if page.categories %}
#   <a href="/{{ page.categories | first }}/">{{ page.categories | first }}</a> |
# {% endif %}

# 3. Test locally
bundle exec jekyll serve

# 4. Verify on multiple articles
# - Check category displays
# - Check category link works
# - Check articles without categories

# 5. Commit and merge
git add _layouts/post.html
git commit -m "Fix: Display category tag above article title"
git push origin fix-missing-category-tag

# 6. Merge via GitHub API (proven method)
curl -X POST https://api.github.com/repos/oviney/blog/merges \
  -H "Authorization: Bearer $(gh auth token)" \
  -d '{"base":"main","head":"fix-missing-category-tag","commit_message":"Fix: Display category tag above article title"}'

# 7. Verify deployment
gh run list --repo oviney/blog --limit 1
```

**Expected Outcome:**
- Category tag displays above title on all article pages
- Category link navigates to category archive (if exists)
- Consistent with The Economist's visual style
- Issue #15 can be closed

**Alternative Next Action (if #15 is deferred):**

#7: Visual QA Metrics Tracking (P2, small effort)
- Track visual QA success/failure rates
- Identify common chart issues
- Improve Graphics Agent over time
