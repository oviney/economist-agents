# Story 2: Fix Issue #15 - Missing Category Tag

**Sprint**: 2
**Story Points**: 1
**Priority**: P1 (High)
**Status**: In Progress

---

## Problem Analysis

**Issue #15**: Article pages missing category tag display above title

**Current State**:
- Layout has breadcrumb with category (line 7-14 in post.html)
- Categories defined in front matter: `categories: [quality-engineering, ai]`
- Breadcrumb shows: `Quality-engineering | Article Title`

**The Economist Style**:
- Category tag appears as small, colored label ABOVE the title
- Example: `[QUALITY ENGINEERING]` in red box
- Not a breadcrumb navigation, but a visual category indicator

**Root Cause**:
- Current implementation uses breadcrumb navigation (lowercase, linked)
- Missing prominent category TAG (uppercase, styled) above title
- Inconsistent with The Economist visual style

---

## Solution Design

### Add Prominent Category Tag

**Location**: Above article title (before `<h1>`)

**Style**:
```html
<div class="category-tag">
  <span class="tag">QUALITY ENGINEERING</span>
</div>
```

**CSS** (to be added to stylesheet):
```css
.category-tag {
  margin-bottom: 1rem;
}

.category-tag .tag {
  display: inline-block;
  background-color: #e3120b;  /* Economist red */
  color: #fff;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  padding: 0.25rem 0.75rem;
  text-transform: uppercase;
}
```

**Graceful Degradation**:
- If no categories: Don't display tag (no empty box)
- If multiple categories: Display first one
- Keep existing breadcrumb for navigation

---

## Implementation Plan

### Phase 1: Update Layout (5 min)
1. ✅ Analyze current post.html
2. ⏳ Add category tag above title
3. ⏳ Preserve existing breadcrumb

### Phase 2: Test Locally (10 min)
1. ⏳ Start Jekyll server
2. ⏳ View multiple posts
3. ⏳ Test with/without categories
4. ⏳ Verify styling matches Economist

### Phase 3: Create PR (5 min)
1. ⏳ Create branch: fix-missing-category-tag
2. ⏳ Commit changes
3. ⏳ Push to GitHub
4. ⏳ Create pull request

### Phase 4: Document (5 min)
1. ⏳ Update SPRINT.md tasks
2. ⏳ Document fix in CHANGELOG
3. ⏳ Update GitHub Issue #15

**Total Estimated Time**: 25 minutes

---

## Test Cases

### Test 1: Post with Categories
**Input**: testing-times.md (has categories)
**Expected**: Red category tag "QUALITY ENGINEERING" above title
**Status**: ⏳ Pending

### Test 2: Post without Categories
**Input**: Post with no categories field
**Expected**: No category tag (graceful degradation)
**Status**: ⏳ Pending

### Test 3: Post with Multiple Categories
**Input**: Post with categories: [quality-engineering, ai]
**Expected**: Shows first category "QUALITY ENGINEERING"
**Status**: ⏳ Pending

### Test 4: Styling Consistency
**Input**: All posts
**Expected**: Red background, white text, uppercase, proper spacing
**Status**: ⏳ Pending

---

## Acceptance Criteria

- [ ] Category tag displays on all article pages (above title)
- [ ] Category uses The Economist red (#e3120b)
- [ ] Category text is uppercase and bold
- [ ] Articles without categories degrade gracefully (no tag shown)
- [ ] Existing breadcrumb navigation preserved
- [ ] Styling matches The Economist visual standard

---

**Status**: Planning complete, ready for implementation
