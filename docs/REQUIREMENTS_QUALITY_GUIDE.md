# Requirements Quality Guide - Shift Quality Left

**Purpose**: Define quality attributes in requirements phase to prevent post-deployment discovery of "missing features" that look like bugs.

**Key Insight**: High defect escape rate (75%) reveals requirements gap, not implementation failure. Team builds to spec—spec is incomplete.

---

## The Problem: Quality as Afterthought

**Current State** (Sprint 7 Discovery):
- Requirements: "Generate blog posts in Economist style"
- Missing: References section, citation format, source attribution
- Result: BUG-024 - "posts lack references" (discovered post-deployment)
- Classification: Looks like defect, actually missing requirement

**Anti-Pattern**:
```
Story: "As reader, I need blog posts so I can learn about QE"
AC: [x] Post generated
     [x] Markdown formatted
     [x] Published to blog
     [ ] ??? References section (never specified)
```

**Impact**:
- False defect escape rate (requirements gaps counted as bugs)
- Late discovery increases fix cost (design → code → test → deploy)
- Team velocity appears low (rework that shouldn't exist)
- No baseline for regression (what was the original requirement?)

---

## The Solution: Quality Requirements Section

**New Pattern**: Every story MUST include explicit quality attributes.

### Story Template Enhancement

```markdown
## Story

As a [role], I need [capability], so that [benefit]

## Functional Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2

## Quality Requirements (NEW - MANDATORY)

### Content Quality
- [ ] References section required (yes/no/conditional)
- [ ] Citation format specified (if yes: Economist style, APA, MLA, etc.)
- [ ] Source attribution method (inline links, footnotes, bibliography)
- [ ] Verification process (peer review, fact-check, automated)

### Performance Criteria
- [ ] Load time target (< 2s initial render)
- [ ] Readability score (Hemingway < 10 for Economist style)
- [ ] Mobile responsiveness (viewport 320px - 1920px)

### Accessibility Requirements
- [ ] WCAG compliance level (A, AA, AAA)
- [ ] Screen reader compatibility (required/not required)
- [ ] Keyboard navigation (required/not required)
- [ ] Color contrast ratios (4.5:1 minimum for text)

### SEO Requirements
- [ ] Meta description (yes/character limit)
- [ ] Open Graph tags (required/optional)
- [ ] Structured data (Schema.org types specified)
- [ ] Canonical URLs (handling specified)

### Security/Privacy
- [ ] Data sanitization (XSS prevention)
- [ ] Authentication required (yes/no/conditional)
- [ ] PII handling (specified/none)

### Maintainability
- [ ] Documentation level (inline comments, external docs)
- [ ] Test coverage target (% line coverage)
- [ ] Code review required (yes/no)
```

---

## Updated Definition of Ready

**Before Sprint 7** (DoR v1.1):
```
□ Story written with clear goal
□ Acceptance criteria defined
□ Three Amigos review complete
□ Dependencies identified
□ Technical prerequisites validated
□ Risks documented
□ Story points estimated
□ Definition of Done agreed
□ User/Product Owner approval obtained
```

**Sprint 7+ Enhancement** (DoR v1.2):
```
□ Story written with clear goal
□ Acceptance criteria defined
□ Quality requirements explicitly documented ← NEW
  ├─ Content quality standards specified
  ├─ Performance criteria defined
  ├─ Accessibility requirements stated
  └─ SEO/security/maintainability requirements documented
□ Three Amigos review complete (includes quality review) ← ENHANCED
□ Dependencies identified
□ Technical prerequisites validated
□ Risks documented
□ Story points estimated (includes quality work) ← ENHANCED
□ Definition of Done agreed (includes quality gates) ← ENHANCED
□ User/Product Owner approval obtained
```

**Critical Rule**: If quality requirement section is placeholder ("TBD", "N/A without justification", "Same as before"), story FAILS DoR and CANNOT start.

---

## Content Quality Checklist (Blog Posts)

Use this for all blog/article generation stories:

### Pre-Story (Requirements Phase)

**Content Standards**:
- [ ] References section required? (YES/NO)
  - If YES: Format specified (inline links / footnotes / bibliography)
  - If YES: Citation style documented (Economist / APA / MLA / custom)
  - If YES: Minimum sources count (e.g., "3+ authoritative sources")
- [ ] Source attribution requirements
  - [ ] Research data must include source URLs
  - [ ] Statistics require named sources (not "studies show")
  - [ ] Expert quotes require attribution
- [ ] Fact-checking process defined
  - [ ] Verification method (automated / manual / hybrid)
  - [ ] Acceptable source types (journals, reports, interviews)
  - [ ] Disputed claims handling

**Formatting Requirements**:
- [ ] British vs American spelling (specify)
- [ ] Heading structure (specify levels: H1 for title, H2 for sections)
- [ ] Paragraph length targets (Economist: 3-4 sentences max)
- [ ] Lists formatting (bullet, numbered, when to use)

**Style Guide References**:
- [ ] Voice guide (Economist Editorial Style Guide v2024)
- [ ] Tone requirements (confident, direct, no hedging)
- [ ] Banned phrases documented (see BANNED_PHRASES list)
- [ ] Title format (puns, wordplay, subtitle structure)

### Post-Generation (Validation Phase)

**Verification Checklist**:
- [ ] All statistics have named sources
- [ ] References section present (if required)
- [ ] Citation format matches specification
- [ ] British spelling throughout (if specified)
- [ ] No banned phrases detected
- [ ] Readability score meets target
- [ ] Chart embedded and referenced (if chart_data provided)

---

## Bug Reclassification Framework

**Question**: Is this a defect or a requirements gap?

### Decision Tree

```
Issue discovered → Was it specified in requirements?
                   │
                   ├─ YES → Implementation defect (true bug)
                   │         - Log as defect
                   │         - Count toward escape rate
                   │         - Root cause: code_logic, validation_gap, etc.
                   │
                   └─ NO → Requirements gap (specification evolution)
                             - Log as requirements_gap
                             - Do NOT count toward defect escape rate
                             - Root cause: requirements_gap
                             - Update requirements baseline
```

### Examples

**TRUE DEFECT** (BUG-016):
- Requirement: "Chart embedded in article body"
- Acceptance Criteria: "[x] Chart markdown present"
- Actual: Chart generated but not embedded
- Classification: Implementation defect (code_logic)
- Escape rate: YES, counts

**REQUIREMENTS GAP** (BUG-024):
- Requirement: "Generate blog post in Economist style"
- Acceptance Criteria: "[x] Post generated, [x] Economist voice"
- Missing: References section requirement
- Actual: Post generated correctly per spec, but spec incomplete
- Classification: Requirements gap (requirements_gap)
- Escape rate: NO, don't count (no spec to violate)

**KEY INSIGHT**: You can't escape a requirement that never existed.

---

## Metrics Recalculation

### Before Reclassification (Sprint 7, Day 1)

```
Total bugs: 8
Production bugs: 6
Defect escape rate: 75.0% (6 production / 8 total)
Quality alert: 55 points from target (<20%)
```

### After Reclassification (Sprint 7, Day 2)

**Requirements Gaps** (exclude from escape rate):
- BUG-024: Missing references requirement (requirements_gap)
- [Need to review others for reclassification]

**True Implementation Defects**:
- BUG-015: validation_gap (layout check missing)
- BUG-016: prompt_engineering (chart embedding)
- BUG-017: requirements_gap? (duplicate chart display)
- BUG-020: integration_error (GitHub syntax)
- BUG-021: code_logic (doc automation)
- BUG-022: code_logic (doc automation)
- BUG-023: validation_gap (badge staleness)

**Action Required**: Run full reclassification analysis to separate specification evolution from implementation defects.

---

## Implementation Roadmap

### Immediate (Sprint 7, Day 2)

**Story 2 Addition**: Add quality requirements reclassification
- Task 2b: Reclassify all 8 bugs (requirements_gap vs implementation)
- Task 2c: Calculate true defect escape rate
- Task 2d: Update defect tracker with classification field

### Sprint 8 (Quality Requirements Deployment)

**Story: Deploy Quality Requirements Framework** (5 points)
- Task 1: Create story template with quality requirements section
- Task 2: Update DoR checklist in SCRUM_MASTER_PROTOCOL.md
- Task 3: Train team on quality requirements (workshop)
- Task 4: Validate with next 3 stories (pilot program)
- Task 5: Measure impact (escape rate, rework rate, velocity)

**Story: Content Quality Automation** (3 points)
- Task 1: Add Publication Validator check for references section
- Task 2: Enhance Blog QA with citation format validation
- Task 3: Create Economist-style reference template
- Task 4: Update Writer Agent prompt to output references

### Sprint 9 (Continuous Improvement)

**Story: Quality Requirements Retrospective** (2 points)
- Analyze: Did escape rate improve?
- Measure: Requirements completeness score
- Adjust: Refine quality requirements template
- Share: Document learnings in RETROSPECTIVE_S9.md

---

## Best Practices

### Writing Quality Requirements

**DO**:
- ✅ Be explicit: "References section with 3+ authoritative sources"
- ✅ Be measurable: "Load time < 2s on 3G connection"
- ✅ Be testable: "Readability score < 10 (Hemingway App)"
- ✅ Specify format: "Citations in Economist style (Source, Year)"

**DON'T**:
- ❌ Be vague: "Good quality content"
- ❌ Assume: "Standard format" (what standard?)
- ❌ Defer: "TBD" or "Will decide later"
- ❌ Omit: Leave quality section blank

### Three Amigos Review (Enhanced)

**Developer Perspective**: "How will we implement quality requirements?"
- Technical feasibility of quality checks
- Automated validation approach
- Performance impact of quality features

**QA Perspective**: "How will we test quality requirements?"
- Test cases for each quality criterion
- Automation vs manual validation
- Regression test baseline

**Product Perspective**: "Why these quality requirements?"
- User impact of each quality attribute
- Priority (must-have vs nice-to-have)
- Trade-offs (quality vs speed vs cost)

### Story Point Estimation (Enhanced)

**Include quality work in estimates**:
- Functional work: 60% (base implementation)
- Quality work: 40% (testing, validation, documentation)
- Example: 5-point story = 3 points functional + 2 points quality

**Red Flag**: If quality requirements are extensive but story points don't increase, estimate is incomplete.

---

## Tools & Templates

### Quality Requirements Template (Markdown)

```markdown
## Quality Requirements

### Content Quality
- References: [Required/Optional/Not Applicable]
  - Format: [Inline/Footnotes/Bibliography]
  - Style: [Economist/APA/MLA/Custom]
  - Minimum sources: [Number]
- Source attribution: [Requirements]
- Fact-checking: [Process]

### Performance
- Load time: [< Xs]
- Readability: [Score < Y]
- Mobile: [Responsive required]

### Accessibility
- WCAG: [Level A/AA/AAA]
- Screen reader: [Required/Optional]
- Keyboard nav: [Required/Optional]

### SEO
- Meta description: [Yes/No, character limit]
- Open Graph: [Required/Optional]
- Structured data: [Schema.org types]

### Security
- Sanitization: [XSS prevention required]
- Auth: [Required/Optional]
- PII: [Handling specified]

### Maintainability
- Documentation: [Level]
- Test coverage: [% target]
- Code review: [Required]
```

### Validation Checklist Template

```markdown
## Quality Validation Checklist

### Content Quality
- [ ] All statistics have named sources
- [ ] References section present (if required)
- [ ] Citation format correct
- [ ] Spelling matches specification
- [ ] No banned phrases

### Performance
- [ ] Load time measured and meets target
- [ ] Readability score calculated and meets target
- [ ] Mobile responsiveness verified

### Accessibility
- [ ] WCAG validation passed
- [ ] Screen reader tested (if required)
- [ ] Keyboard navigation verified

### SEO
- [ ] Meta tags present and correct
- [ ] Structured data validated
- [ ] Canonical URLs correct

### Regression
- [ ] Baseline documented for future comparison
- [ ] Tests added to prevent regression
```

---

## Success Metrics

### Leading Indicators (Predict Quality)

**Requirements Completeness Score**:
- Target: 100% of stories have quality requirements section
- Measure: % stories with complete quality requirements
- Green: >95%, Yellow: 80-95%, Red: <80%

**Quality Requirement Clarity**:
- Target: <5% clarification requests during implementation
- Measure: # questions about quality requirements / total stories
- Green: <5%, Yellow: 5-10%, Red: >10%

### Lagging Indicators (Measure Quality)

**True Defect Escape Rate** (implementation bugs only):
- Target: <20% (was 75% with requirements gaps included)
- Measure: Production implementation bugs / total implementation bugs
- Exclude: requirements_gap bugs from calculation

**Rework Rate**:
- Target: <10% of story work is rework
- Measure: Time spent on quality "bugs" / total story time
- Distinction: Requirements evolution vs implementation fixes

**Time to Market**:
- Target: Maintain or improve velocity with quality improvements
- Measure: Story cycle time (commit to deployment)
- Hypothesis: Upfront quality reduces late-stage rework

---

## Continuous Improvement Loop

```
1. Write Story with Quality Requirements
   ↓
2. Three Amigos Review (includes quality perspective)
   ↓
3. Implement to Specification (including quality attributes)
   ↓
4. Validate Quality (automated + manual)
   ↓
5. Deploy (quality gates passed)
   ↓
6. Monitor Production
   ↓
7. Classify Issues (defect vs requirements gap)
   ↓
8. Learn: Update requirements template
   ↓
9. Repeat (improved requirements next story)
```

**Key Insight**: Each requirements gap discovered becomes a checklist item for future stories. Quality requirements template evolves based on production learnings.

---

## Related Documentation

- [SCRUM_MASTER_PROTOCOL.md](SCRUM_MASTER_PROTOCOL.md) - Updated DoR checklist
- [DEFECT_PREVENTION.md](DEFECT_PREVENTION.md) - Prevention system patterns
- [SPRINT_7_LESSONS_LEARNED.md](SPRINT_7_LESSONS_LEARNED.md) - Sprint 7 insights

---

**Version**: 1.0 (Sprint 7, Day 2)
**Maintained By**: Scrum Master + Product Owner
**Review Frequency**: After each sprint retrospective
**Update Trigger**: New requirements gap discovered or quality metric trend changes
