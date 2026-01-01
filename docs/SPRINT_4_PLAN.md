# Sprint 4 Planning - Quality Metrics & GenAI Features

**Sprint Duration:** Jan 2-8, 2026 (5 working days)  
**Sprint Goal:** Integrate metrics tracking into production pipeline and add GenAI featured images

---

## Sprint Retrospective: Sprint 3 Performance

### What We Delivered
- ✅ 5/5 story points (100% completion)
- ✅ Quality score: 98/100 (A+)
- ✅ Test pass rate: 11/11 (100%)
- ✅ Time accuracy: 100% (5 hours estimated, 5 hours actual)

### User Feedback Incorporated
> "I don't see us showing a quality trend, nor how the agents are achieving their goal (prediction vs actual)."

**Response:** Built comprehensive metrics system:
- Quality trend tracking (improving ⬆️ / stable ➡️ / declining ⬇️)
- Agent prediction vs actual tracking
- Dashboard visualization

**Status:** Prototype complete, ready for integration

---

## Sprint 4 Backlog (Prioritized)

### High Priority Stories

#### Story 1: **Integrate Metrics into Production Pipeline** (Issue #19)
**Priority:** P0 (Must Do - addresses user feedback)  
**Story Points:** 3  
**Estimated Time:** 3-4 hours

**Why This Story:**
- User requested trending and agent accountability
- Prototype is complete and working
- High value, low risk integration

**Tasks:**
- [ ] Import `AgentMetrics` into `economist_agent.py`
- [ ] Add tracking calls after each agent stage:
  - `track_research_agent()` after research
  - `track_writer_agent()` after writing
  - `track_editor_agent()` after editing
  - `track_graphics_agent()` after chart generation
- [ ] Save metrics in `generate_economist_post()`
- [ ] Test with live article generation
- [ ] Verify metrics accumulate correctly

**Acceptance Criteria:**
- [ ] Metrics collected on every article generation run
- [ ] `skills/agent_metrics.json` updates automatically
- [ ] Dashboard shows real production data
- [ ] No performance degradation (<100ms overhead)

**Risk:** Low - prototype tested with sample data

---

#### Story 2: **GenAI Featured Images** (Issue #14)
**Priority:** P1 (High Value Feature)  
**Story Points:** 5  
**Estimated Time:** 5-7 hours

**Why This Story:**
- Completes the article generation pipeline
- Adds visual appeal (key for blog engagement)
- Leverages DALL-E 3 for Economist-style illustrations

**Tasks:**
- [ ] Create `featured_image_agent.py`
- [ ] Design prompt template for Economist visual style
- [ ] Integrate DALL-E 3 API
- [ ] Add image generation to `economist_agent.py` pipeline
- [ ] Save images to `assets/images/`
- [ ] Update article front matter with `image:` field
- [ ] Add error handling (fallback if API fails)
- [ ] Test with 3 different article topics

**Acceptance Criteria:**
- [ ] Featured image generated for each article
- [ ] Image matches Economist editorial illustration style
- [ ] Image saved with article slug naming
- [ ] Front matter includes `image:` path
- [ ] Graceful degradation if DALL-E API unavailable

**Risk:** Medium - depends on DALL-E API, requires prompt tuning

**Prompt Design:**
```
Style: Editorial illustration for The Economist magazine
Subject: [Article topic/headline]
Requirements:
- Minimalist, conceptual, symbolic
- Limited color palette (navy #17648d, burgundy #843844, beige #f1f0e9)
- No text or labels
- Professional, businesslike tone
- Avoid clichés (lightbulbs, arrows, gears)
```

---

#### Story 3: **Metrics Documentation** (Part of Issue #19)
**Priority:** P2 (Medium)  
**Story Points:** 1  
**Estimated Time:** 1-2 hours

**Tasks:**
- [ ] Create `docs/METRICS_GUIDE.md`
- [ ] Document dashboard usage with examples
- [ ] Add metrics section to README
- [ ] Update SPRINT.md with Sprint 4 details

**Acceptance Criteria:**
- [ ] Guide explains dashboard commands
- [ ] Examples show how to interpret trends
- [ ] README links to metrics guide
- [ ] Sprint tracking updated

**Risk:** Low - straightforward documentation

---

### Deferred Stories (Not in Sprint 4)

**Issue #12:** CONTRIBUTING.md (P4, 1 pt) - Defer to Sprint 5  
**Issue #11:** Pre-commit Architecture Review (P4, 1 pt) - Defer to Sprint 5  
**Issue #10:** Expand Skills Categories (P3, 2 pts) - Defer to Sprint 5  
**Issue #9:** Anti-Pattern Detection (P3, 3 pts) - Defer to Sprint 5  
**Issue #8:** Integration Tests (P3, 5 pts) - Defer to Sprint 5  

**Rationale:** Focus Sprint 4 on completing user-requested metrics + high-value GenAI feature

---

## Sprint 4 Capacity Planning

**Total Story Points:** 9 (3 + 5 + 1)  
**Estimated Time:** 9-13 hours  
**Days:** 5 working days  
**Velocity:** 8-10 points/week (historical average)

**Assessment:** ⚠️ Slightly over capacity (9 pts vs 8-10 target)

### Options:

**Option A: Full Sprint (9 points)**
- Story 1: Metrics Integration (3 pts) ✅
- Story 2: GenAI Featured Images (5 pts) ✅
- Story 3: Documentation (1 pt) ✅
- **Risk:** May need to cut Story 2 if complexity high

**Option B: Safe Sprint (4 points)**
- Story 1: Metrics Integration (3 pts) ✅
- Story 3: Documentation (1 pt) ✅
- **Risk:** Defers valuable GenAI feature

**Option C: Aggressive Sprint (9 points + buffer)**
- All 3 stories + start Issue #10 if time allows
- **Risk:** Overcommitment, potential incomplete work

---

## Recommendation: **Option A (Full Sprint - 9 points)**

**Rationale:**
1. **Metrics integration is critical** (user-requested, high value)
2. **GenAI images complete the pipeline** (blog-ready articles)
3. **Documentation enables adoption** (metrics won't be used without guide)
4. Story 2 can be de-scoped if needed (defer error handling to Sprint 5)

**Sprint Goal:**
> "Deliver production-ready metrics tracking with agent accountability, and add GenAI featured images to complete the article generation pipeline."

---

## Sprint 4 Schedule (Proposed)

### Day 1 (Jan 2): Metrics Integration
- **Morning:** Story 1 - Add metrics to `economist_agent.py`
- **Afternoon:** Test with live article generation
- **EOD:** Metrics dashboard shows real production data

### Day 2 (Jan 3): GenAI Setup
- **Morning:** Story 2 - Create `featured_image_agent.py`
- **Afternoon:** DALL-E 3 integration and prompt tuning
- **EOD:** First featured image generated

### Day 3 (Jan 4): GenAI Integration
- **Morning:** Add to `economist_agent.py` pipeline
- **Afternoon:** Test with 3 different article topics
- **EOD:** Featured images working end-to-end

### Day 4 (Jan 5): Polish & Documentation
- **Morning:** Error handling, graceful degradation
- **Afternoon:** Story 3 - Write metrics guide
- **EOD:** Documentation complete

### Day 5 (Jan 6): Buffer & Sprint Review
- **Morning:** Address any blockers
- **Afternoon:** Sprint retrospective
- **EOD:** Plan Sprint 5

---

## Success Metrics

**Metrics Integration:**
- [ ] 100% of article runs collect agent metrics
- [ ] Dashboard shows ≥5 historical runs
- [ ] Prediction accuracy visible for all 4 agents

**GenAI Featured Images:**
- [ ] ≥3 articles with GenAI featured images
- [ ] Images match Economist editorial style
- [ ] <5 seconds per image generation

**Documentation:**
- [ ] Metrics guide complete with examples
- [ ] README updated

---

## Risk Management

**Risk 1: DALL-E API Issues**
- **Mitigation:** Implement fallback (skip image, continue article)
- **Fallback Plan:** Defer to Sprint 5 if API unreliable

**Risk 2: Metrics Performance Impact**
- **Mitigation:** Benchmark before/after, optimize if needed
- **Target:** <100ms overhead per article

**Risk 3: Sprint Overcommitment**
- **Mitigation:** De-scope Story 2 error handling if needed
- **Minimum Viable:** GenAI images work in happy path only

---

## Definition of Done

### Story 1 (Metrics Integration)
- [x] Code committed and pushed
- [x] Metrics collected on article generation
- [x] Dashboard validated with production data
- [x] No performance regressions
- [x] Issue #19 closed

### Story 2 (GenAI Featured Images)
- [x] Code committed and pushed
- [x] ≥3 sample images generated
- [x] Images saved to correct directory
- [x] Front matter updated automatically
- [x] Error handling implemented
- [x] Issue #14 closed

### Story 3 (Documentation)
- [x] METRICS_GUIDE.md created
- [x] README updated
- [x] SPRINT.md updated with Sprint 4
- [x] Committed and pushed

---

## Sprint 4 Approval

**Awaiting Scrum Master Approval:**

Please review and choose:
- [ ] **Option A: Full Sprint (9 pts)** - Metrics + GenAI + Docs
- [ ] **Option B: Safe Sprint (4 pts)** - Metrics + Docs only
- [ ] **Option C: Aggressive Sprint (9+ pts)** - All + bonus work
- [ ] **Custom Scope** - Specify your preferred stories

**Your Decision:**
