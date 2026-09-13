# Research Spike: Agent Performance as Team Skills Gap Indicator

**Issue**: #29
**Type**: Research Spike
**Story Points**: 5
**Status**: Ready for Pickup (blocked by defect RCA foundation)
**Owner**: Team (self-organized)

---

## Executive Summary

When AI agents produce bugs, this indicates skills gaps in the human roles they simulate. This spike researches how to translate agent performance metrics into actionable hiring/training insights.

**Current State**: We track agent bugs but can't answer "which roles need development?"
**Desired State**: Dashboard shows skills gaps by role with hiring/training recommendations

---

## Research Questions

### Phase 1: Role Mapping (1 day)

**Questions:**
1. Which human role does each agent simulate?
2. What are the key skills for each role (junior → mid → senior)?
3. How does current agent performance map to human skill levels?
4. What would "excellent" look like for each role?

**Deliverables:**
- Agent → Role mapping table
- Skills rubric per role (3-5 key skills per role)
- Current agent scoring on rubric
- Benchmark: Where should agents be performing?

**Example:**
```
Writer Agent → Content Writer role
Skills:
- Requirements adherence (junior: 50%, mid: 75%, senior: 95%)
- CMS knowledge (junior: basic, mid: proficient, senior: expert)
- Style compliance (junior: 60%, mid: 85%, senior: 98%)

Current Performance: 40/100 → Junior level
Evidence: 2 bugs (charts not embedded, duplicate display)
```

---

### Phase 2: Gap Analysis (1 day)

**Questions:**
1. What patterns emerge from agent bugs?
2. Which roles have the biggest gaps?
3. Are gaps due to prompt engineering or fundamental capability limits?
4. What's the ROI of fixing each gap? (prompt tuning vs hiring vs training)

**Deliverables:**
- Bug pattern analysis by role
- Gap prioritization matrix
- ROI estimation per intervention type
- Recommendations: Which gaps to address first?

**Analysis Framework:**
```
For each agent bug:
1. Map to human role skill
2. Score severity of skill gap (1-5)
3. Estimate fix effort (prompt vs hire vs train)
4. Calculate impact (velocity/quality/cost)
5. Prioritize interventions
```

---

### Phase 3: Framework Design (1.5 days)

**Questions:**
1. How do we visualize skills gaps in the dashboard?
2. What's the reporting format for hiring/training needs?
3. How do we integrate with existing defect/agent metrics?
4. What's the scoring algorithm (bugs → skill level)?

**Deliverables:**
- Dashboard mockup (Team Skills section)
- Reporting template (role → gaps → recommendations)
- Integration design with existing metrics
- Scoring algorithm specification

**Dashboard Mockup Concept:**
```markdown
## 👥 Team Skills Assessment

### By Role Performance
| Role | Skill Level | Top Gap | Recommendation |
|------|------------|---------|----------------|
| Content Writer | Junior (40/100) | Requirements | Prompt eng + Training |
| Research Analyst | Mid (73/100) | Verification | Prompt enhancement |
| Senior Editor | Mid-Senior (85/100) | None | Maintain current |
| Data Viz Designer | Senior (90/100) | None | Maintain current |

### Hiring Recommendations
🔴 **Urgent**: Senior Content Writer (current: junior level, 2 critical bugs)
🟡 **Consider**: Research training program (73% vs 80% target)

### Training Priorities
1. Jekyll/CMS Workshop (addresses Writer Agent bugs)
2. Source Verification Best Practices (improves Research Agent)
```

---

### Phase 4: Validation & Decision (0.5 day)

**Questions:**
1. Does the team find this valuable?
2. Is implementation worth the effort (8-13 points)?
3. What refinements are needed?
4. What are the risks/concerns?

**Deliverables:**
- Team presentation of findings
- Feedback incorporated
- Go/No-Go decision
- Implementation backlog (if approved)

---

## Research Methods

### Interviews (2-3 hours)
**Stakeholders to consult:**
- Product Owner: What roles matter most to you?
- QE Lead: What skills define "good" for each role?
- Engineering Manager: Hiring vs training tradeoffs?
- Team: Does this resonate with your experience?

### Data Analysis (2-3 hours)
**Data sources:**
- Existing 4 bugs with RCA data
- Agent metrics (skills/agent_metrics.json)
- Defect patterns (skills/defect_tracker.json)
- Quality dashboard baseline

### Industry Research (1-2 hours)
**Benchmarks:**
- What's a "good" verification rate for research analysts?
- How do human writers compare to Writer Agent on banned phrases?
- Industry skill level definitions (junior/mid/senior)

---

## Success Criteria

**Spike Passes If:**
- [ ] Agent → Role mapping complete and validated
- [ ] Skills rubric defined for 4 key roles
- [ ] Current 4 bugs analyzed through skills lens
- [ ] Dashboard mockup created
- [ ] Team consensus on value (>50% vote to implement)
- [ ] Implementation effort estimated

**Decision Criteria:**
- **Implement** if team sees >70% confidence in value
- **Archive** if effort outweighs benefit
- **Refine** if concept good but approach needs work

---

## Risk Assessment

**Risks:**

1. **Subjectivity**: "Junior vs mid" is opinion-based
   - **Mitigation**: Use data (bug counts, metrics) + industry benchmarks

2. **Small Sample**: Only 4 bugs logged so far
   - **Mitigation**: Note this is baseline, revisit at 20+ bugs

3. **Effort Uncertainty**: Implementation could balloon
   - **Mitigation**: Tight scope, estimate conservatively

4. **Low Adoption**: Dashboard ignored if not actionable
   - **Mitigation**: Focus on concrete recommendations, not just scores

**If Risks Materialize:**
- Recommendation: Archive and revisit when defect data richer

---

## Implementation Preview (If Approved)

**Estimated Effort**: 8-13 points (1-2 sprints)

**Components:**
1. `skills_gap_analyzer.py` - Analysis engine (3 pts)
2. Dashboard integration - Team Skills section (3 pts)
3. Defect tracker enhancement - "simulated_role" field (2 pts)
4. Reporting templates - Hiring/training recommendations (2 pts)
5. Testing/docs - Validation and documentation (2 pts)

**Acceptance Criteria (Implementation):**
- [ ] Dashboard shows skills assessment by role
- [ ] Hiring recommendations generated automatically
- [ ] Training priorities ranked by impact
- [ ] Integration with existing defect/agent metrics
- [ ] Documentation for stakeholders

---

## Dependencies

**Blocked By:**
- ⚠️ Defect RCA schema enhancement (need root cause data in bug records)
- ⚠️ Stable baseline (minimum 20 bugs with RCA for pattern analysis)

**Earliest Start**: Sprint 7 (after Sprint 6 defect RCA work complete)

**Enables:**
- Data-driven hiring decisions
- Targeted prompt engineering priorities
- Strategic workforce planning
- Training program ROI analysis

---

## Team Self-Organization

**This is a TEAM-DRIVEN spike. Scrum Master facilitates, team executes.**

**How Team Should Approach:**

1. **Self-assign**: Who has bandwidth in Sprint 7+?
2. **Collaborate**: Pair on research, share findings
3. **Timebox**: 5 points max, don't over-engineer
4. **Decide together**: Go/No-Go at end of spike
5. **Escalate only if**: Need leadership decision or external input

**Scrum Master Role:**
- Facilitate kick-off
- Remove blockers
- Check progress (not micromanage)
- Support decision-making
- Document outcomes

**DO NOT NEED LEADERSHIP FOR:**
- Technical design decisions
- Research methodology
- Dashboard mockup design
- Implementation approach
- Effort estimation

**DO NEED LEADERSHIP FOR:**
- Budget for hiring recommendations
- Strategic priority vs other work
- Org-wide rollout decisions

---

## Next Actions (When Team Ready)

**Pre-Sprint Planning:**
1. Review defect RCA completion status
2. Check bug count (need 20+ for good patterns)
3. Confirm team capacity

**Sprint Start:**
1. Team self-assigns spike owner(s)
2. Schedule kick-off (30 min)
3. Conduct stakeholder interviews
4. Execute research phases 1-4

**Sprint End:**
1. Demo findings to team
2. Facilitate Go/No-Go decision
3. Create implementation stories (if approved)
4. Update backlog

---

## References

**Related Documents:**
- Quality Dashboard: `docs/QUALITY_DASHBOARD.md`
- Defect Tracker: `scripts/defect_tracker.py`
- Agent Metrics: `scripts/agent_metrics.py`
- Scrum Master Report: `docs/SCRUM_MASTER_REPORT_METRICS.md`

**Industry Resources:**
- Skills matrices for content roles
- QE competency frameworks
- Hiring vs training ROI models

---

## Open Questions for Team

1. What roles matter most to you in this analysis?
2. How do you currently think about agent vs human performance?
3. What would make this actionable (not just interesting)?
4. Concerns about implementation complexity?
5. Alternative approaches we should consider?

---

**Status**: 📋 Ready for Team Pickup (Sprint 7+)
**Blocked By**: Defect RCA foundation
**Owner**: Team (self-organized)
**Escalation Needed**: No (team has autonomy)
