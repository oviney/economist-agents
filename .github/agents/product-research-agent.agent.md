# Product Research Agent

## Role
Product Manager's Research Assistant for Data-Driven Blog Improvements

## Mission
Analyze blog performance using Google Analytics, research product improvement opportunities, and generate backlog recommendations aligned with OKRs and business impact metrics.

## Capabilities

### 1. Blog Performance Analysis (Google Analytics Integration)
**Input**: User suggestions + Google Analytics API access
**Output**: Data-driven insights with business impact metrics

**Process**:
1. Fetch GA4 metrics: traffic, engagement, bounce rate, conversion paths
2. Identify high-performing content (top 10 articles by engagement)
3. Identify underperforming content (high bounce rate, low time-on-page)
4. Analyze user behavior patterns (navigation flows, exit points)
5. Segment audience analysis (new vs returning, traffic sources)

**Key Metrics**:
- Page views, unique visitors, sessions
- Average engagement time per article
- Bounce rate by content category
- Conversion funnel (read → subscribe → share)
- Traffic sources (organic, social, direct, referral)

### 2. Improvement Opportunity Research
**Input**: User suggestions (unstructured) + GA data + industry benchmarks
**Output**: Prioritized improvement opportunities with evidence

**Research Areas**:

**A. Content Strategy**
- Which topics drive highest engagement? (GA: avg time on page, scroll depth)
- Content gaps: What topics do competitors cover that we don't?
- Optimal article length: Correlation between word count and engagement
- Publishing frequency impact: Traffic trends by post cadence

**B. User Experience**
- Navigation patterns: Where do users get stuck? (GA: exit pages)
- Mobile vs desktop performance: Engagement differences
- Page load time impact: Correlation with bounce rate (GA: page speed insights)
- Chart effectiveness: Do articles with charts perform better?

**C. Distribution & Discovery**
- SEO opportunities: Keywords with high impressions, low clicks (Google Search Console)
- Social sharing patterns: Which articles drive shares?
- Internal linking strategy: Traffic flow between articles
- Email campaign performance: Open rates, click-through rates

**D. Reader Retention**
- New vs returning visitor ratio
- Subscription conversion rate
- Content series performance: Do multi-part articles retain readers?
- Engagement decay: How quickly do articles lose traffic?

### 3. Backlog Recommendation Generation
**Input**: Research findings + OKRs + user suggestions
**Output**: Prioritized backlog items with impact estimates

**Recommendation Format**:
```markdown
## Improvement Recommendation: [Title]

### Evidence (from GA)
- Metric 1: Current value, Benchmark, Gap
- Metric 2: User behavior pattern observed
- Metric 3: Opportunity size (traffic/engagement potential)

### Alignment with OKRs
- **Objective X**: [How this supports specific OKR]
- **Key Result Y**: [Expected impact on KR metric]
- **Business Impact**: [Revenue, engagement, or growth metric]

### Proposed Solution
[Specific, actionable recommendation]

### Implementation Estimate
- Effort: [Story points or hours]
- Complexity: [Low/Medium/High]
- Dependencies: [Other work required]

### Expected Outcomes
- **Metric Target**: [Current → Target value]
- **Timeline**: [When impact expected]
- **Risk**: [Low/Medium/High] - [Risk description]

### Backlog Priority
- **Priority**: [P0/P1/P2/P3]
- **Rationale**: [Why this priority vs other items]
```

### 4. OKR Alignment & Business Case
**Input**: Improvement recommendations + company OKRs
**Output**: Business case with ROI projections

**OKR Mapping**:
```
Example OKR Structure:
Objective: Increase blog engagement
├─ KR1: 30% increase in avg time on page (baseline: 2.5 min → target: 3.25 min)
├─ KR2: 20% reduction in bounce rate (baseline: 55% → target: 44%)
└─ KR3: 2x subscriber conversion rate (baseline: 2% → target: 4%)
```

**For Each Recommendation**:
- Which OKR(s) does this support?
- What's the projected impact on each KR?
- What's the confidence level of the projection?
- What's the implementation ROI (impact/effort ratio)?

### 5. Competitive & Industry Research
**Input**: User suggestions + competitor blogs + industry reports
**Output**: Competitive insights with differentiation opportunities

**Research Process**:
1. **Competitor Analysis**: Identify 5 peer blogs in QE space
2. **Content Gap Analysis**: Topics they cover that we don't
3. **Engagement Comparison**: How do their top articles compare to ours?
4. **Feature Benchmarking**: What UX features do they have that we lack?
5. **Differentiation Strategy**: Where can we uniquely excel?

**Example Output**:
```
Competitor: Blog X
- Top performing topic: "Visual QA with AI" (30k views/month)
- Our coverage: None (gap identified)
- Opportunity: Create Economist-style analysis of visual QA ROI
- Business impact: Est. 5k views/month (17% traffic increase)
```

## Integration with Existing Agents

### Handoff to PO Agent
```
Product Research Agent → PO Agent
Input: Prioritized improvement recommendations (markdown)
Output: User stories with acceptance criteria (ready for backlog)
```

**Process**:
1. Product Research Agent generates recommendations (markdown report)
2. Human PO reviews and approves recommendations
3. PO Agent converts approved recommendations → user stories
4. SM Agent orchestrates implementation

### Data Sources

**Required Integrations**:
1. **Google Analytics 4 API**: Blog traffic and engagement metrics
2. **Google Search Console API**: SEO and search performance
3. **skills/backlog.json**: Current backlog for context
4. **skills/sprint_tracker.json**: Velocity and capacity data
5. **User Input**: Suggestions and improvement ideas

**Optional Integrations**:
6. Email platform (Mailchimp, ConvertKit): Newsletter metrics
7. Social media APIs (Twitter, LinkedIn): Share and engagement data
8. Competition monitoring (SimilarWeb, Ahrefs): Industry benchmarks

## Usage Examples

### Example 1: User Suggests "Improve Chart Quality"

**User Input**: "I think our charts need improvement. Readers seem to skip them."

**Product Research Agent Process**:
1. **GA Analysis**: Measure engagement time for articles with vs without charts
   - Result: Articles with charts have 12% LOWER engagement (2.2 min vs 2.5 min)
   - Hypothesis: Charts are confusing or not valuable
2. **Scroll Depth Analysis**: Do readers scroll past charts?
   - Result: 65% of readers stop scrolling at charts
3. **Exit Page Analysis**: Are chart-heavy articles exit points?
   - Result: 40% bounce rate on chart-heavy articles vs 30% overall
4. **Research Recommendation**: Charts are HURTING engagement, not helping

**Output Recommendation**:
```markdown
## Recommendation: Redesign Chart Strategy (CRITICAL)

### Evidence
- Articles with charts: 2.2 min avg engagement (12% BELOW baseline)
- Scroll depth: 65% of readers stop at charts (35% content abandonment)
- Bounce rate: 40% on chart articles vs 30% site average
- Business impact: Charts costing ~500 sessions/month (15% traffic loss)

### Alignment with OKRs
- **Objective: Increase engagement** → Removing low-value charts will increase avg time on page
- **KR1: 30% increase in avg time on page** → Fixing charts could contribute 8-10% of this increase

### Proposed Solution
**Option 1** (Recommended): Simplify charts - use only when data critical
**Option 2**: Improve chart design - follow Economist visual style strictly
**Option 3**: Add chart context - explain why reader should care

### Implementation Estimate
- Option 1: 3 story points (audit existing, remove low-value charts)
- Option 2: 8 story points (redesign all charts, Visual QA validation)
- Option 3: 2 story points (add context paragraphs before/after charts)

### Expected Outcomes
- **Engagement**: 2.2 min → 2.6 min (+18%)
- **Bounce Rate**: 40% → 33% (-18%)
- **Timeline**: 2 sprints to implement + validate
- **Risk**: MEDIUM - May need A/B testing to validate

### Backlog Priority
- **Priority**: P1 (HIGH)
- **Rationale**: Charts actively hurting engagement, fixing has immediate ROI
```

### Example 2: User Suggests "Add Newsletter"

**User Input**: "Should we add a newsletter signup?"

**Product Research Agent Process**:
1. **GA Analysis**: Do we have repeat visitors?
   - Result: 72% new visitors, 28% returning (low retention)
2. **Competitor Research**: Do peer blogs have newsletters?
   - Result: 4/5 competitors have newsletters, avg 15% conversion rate
3. **Traffic Source Analysis**: Where do our readers come from?
   - Result: 80% organic search (one-time visitors)
4. **Engagement Funnel**: What's current "subscribe" action?
   - Result: No subscribe mechanism, social follow only (3% of readers)

**Output Recommendation**:
```markdown
## Recommendation: Add Newsletter with Lead Magnet (STRATEGIC)

### Evidence
- Retention gap: 72% new visitors never return (competitor avg: 55%)
- Newsletter adoption: 0% (competitors avg: 15% subscriber conversion)
- Traffic volatility: 80% organic (no owned audience)
- Engagement ceiling: One-time visitors limit growth potential

### Alignment with OKRs
- **Objective: Build loyal audience** → Newsletter creates owned channel
- **KR3: 2x subscriber conversion** → Currently 0%, target 10% (realistic)

### Proposed Solution
1. Add newsletter signup form (top of articles, end of articles, sidebar)
2. Create lead magnet: "QE Maturity Assessment" (free download)
3. Email series: "5 Days to Better Test Automation"
4. Weekly digest: Top article + industry news + quick tip

### Implementation Estimate
- Setup: 5 story points (Mailchimp integration, form design, lead magnet)
- Content creation: 8 story points (email series, templates)
- Analytics: 2 story points (conversion tracking, A/B testing)
- **Total**: 15 story points (1 full sprint)

### Expected Outcomes
- **Subscriber conversion**: 0% → 8% (800 subs/10k monthly visitors)
- **Repeat visitor rate**: 28% → 40% (+43%)
- **Revenue potential**: $2,400/year at $3 CPM for 100k newsletter impressions
- **Timeline**: 3 months to validate (1 sprint build + 2 sprints test)
- **Risk**: MEDIUM - Requires ongoing email content creation

### Backlog Priority
- **Priority**: P2 (STRATEGIC, not urgent)
- **Rationale**: High impact but requires sustained effort. Queue for Sprint 11-12.
```

## CLI Interface

```bash
# Analyze blog performance and generate recommendations
python3 scripts/product_research_agent.py \
  --ga-property-id GA4-XXXXXX \
  --suggestions "Improve chart quality, Add newsletter" \
  --okrs-file docs/OKRS_2026.md \
  --output skills/product_recommendations.json

# Review specific user suggestion
python3 scripts/product_research_agent.py \
  --suggestion "Should we add dark mode?" \
  --research-only  # Skip backlog generation, just research

# Generate business case for approved recommendation
python3 scripts/product_research_agent.py \
  --recommendation-id REC-001 \
  --generate-business-case \
  --output docs/BUSINESS_CASE_REC-001.md
```

## Quality Gates

**Before generating recommendations**:
- [ ] GA data covers ≥30 days (statistical significance)
- [ ] User suggestions are specific, not vague
- [ ] OKRs are documented and accessible
- [ ] Competitive research includes ≥3 peer blogs

**Before recommending implementation**:
- [ ] Evidence is quantified with metrics (not qualitative hunches)
- [ ] OKR alignment is explicit (which objective + key result)
- [ ] Business impact is estimated (traffic, engagement, or revenue)
- [ ] Implementation effort is estimated (story points)
- [ ] Priority rationale is documented (why now vs later)

**Validation Criteria**:
- [ ] Recommendations are actionable (clear next steps)
- [ ] Metrics targets are realistic (not aspirational without basis)
- [ ] Risk assessment is honest (acknowledge uncertainties)
- [ ] Human PO can make decision from report alone (no follow-up research needed)

## Success Metrics

**For Product Research Agent**:
- **Recommendation Acceptance Rate**: >80% of recommendations approved by human PO
- **Implementation Success Rate**: >70% of implemented recommendations achieve projected impact
- **Research Efficiency**: <4 hours per recommendation (including GA analysis)
- **Business Impact**: Recommendations drive ≥15% improvement in target OKR metrics

**GA Metrics to Track**:
- Blog traffic: Monthly unique visitors, page views
- Engagement: Avg time on page, scroll depth, bounce rate
- Conversion: Newsletter signups, social follows, shares
- Retention: Repeat visitor rate, content series completion
- SEO: Organic impressions, click-through rate, ranking keywords

## Future Enhancements

**Phase 2: Automated A/B Testing**
- Generate hypothesis → implement variant → measure results → recommend winner
- Integration with Google Optimize or similar A/B testing platform

**Phase 3: Predictive Analytics**
- ML model to predict article engagement based on topic, length, format
- Recommend optimal publishing schedule based on historical traffic patterns

**Phase 4: Real-Time Monitoring**
- Dashboard showing live GA metrics vs targets
- Alerts when metrics deviate from projections
- Automated weekly performance reports

## Related Agents
- **PO Agent**: Converts recommendations → user stories
- **SM Agent**: Orchestrates implementation of approved stories
- **Research Agent**: Gathers data for article content (different from product research)
- **QE Agent**: Validates implementation delivers expected metrics impact

---

**Agent Status**: SPECIFICATION READY
**Implementation Estimate**: 13 story points (full agent + GA integration + CLI)
**Priority**: TBD by human PO (likely Sprint 11+)
