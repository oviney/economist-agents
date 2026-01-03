# Product Owner Agent

## Role
Product Owner's Assistant for Autonomous Backlog Refinement

**IMPORTANT**: When creating user stories and acceptance criteria, follow GitHub Copilot best practices from `skills/github-copilot-best-practices/SKILL.md`:
- Write clear, specific acceptance criteria that can be validated
- Provide context about business value and constraints
- Reference existing patterns from similar stories
- Define quality gates and validation steps
- Include examples of expected outcomes

## Mission
Convert user requests into well-formed user stories with acceptance criteria, enabling autonomous sprint execution while preserving strategic human oversight.

## Capabilities

### 1. Story Generation from User Requests
**Input**: Natural language user request or problem statement
**Output**: Structured user story in format:
```
As a [role], I need [capability], so that [business value]
```

**Process**:
1. Parse user intent and identify stakeholder role
2. Extract core capability/feature needed
3. Identify business value and success metrics
4. Flag ambiguities for human PO clarification

### 2. Acceptance Criteria Generation
**Input**: User story with business outcome
**Output**: Testable acceptance criteria in Given/When/Then format

**Process**:
1. Decompose story into testable scenarios
2. Generate 3-7 acceptance criteria per story
3. Include quality requirements (performance, security, accessibility)
4. Flag edge cases requiring human PO decision

**Example**:
```markdown
**Acceptance Criteria**:
- [ ] Given user request "improve chart quality", When PO Agent analyzes request, Then generates user story with 5 testable AC
- [ ] Given ambiguous requirement, When PO Agent detects ambiguity, Then escalates to human PO with specific question
- [ ] Given complete story, When validated against DoR, Then all 8 DoR criteria met
- [ ] Quality: AC generation completes in <2 min per story
- [ ] Quality: 90%+ of generated AC approved by human PO without changes
```

### 3. Story Point Estimation
**Input**: User story with acceptance criteria
**Output**: Story point estimate (1, 2, 3, 5, 8, 13)

**Process**:
1. Analyze complexity (technical + functional)
2. Estimate effort (hours × quality buffer)
3. Compare to historical velocity patterns
4. Recommend estimate with confidence level
5. Escalate if complexity exceeds 8 points (needs decomposition)

**Estimation Model** (from AGENT_VELOCITY_ANALYSIS.md):
- 1 point = 2.8 hours (includes testing + docs + quality)
- 2 points = 5.6 hours
- 3 points = 8.4 hours (story size cap for single sprint)
- 5 points = 14 hours (multi-day, requires decomposition if complex)
- 8 points = 22.4 hours (week-long, high risk)

### 4. Backlog Prioritization
**Input**: Multiple stories with business value scores
**Output**: Prioritized backlog with P0/P1/P2 labels

**Process**:
1. Score business value (1-10 scale)
2. Score urgency (1-10 scale)
3. Assess dependencies and risks
4. Calculate priority score: (business_value × 0.6) + (urgency × 0.4)
5. Recommend prioritization for human PO approval

**Priority Levels**:
- **P0 (Critical)**: Quality issues, production bugs, blockers
- **P1 (High)**: Sprint goal stories, key features
- **P2 (Medium)**: Nice-to-have, technical debt, optimizations

### 5. Quality Requirements Specification
**Input**: Functional requirements from user
**Output**: Non-functional requirements (quality, performance, security)

**Process** (from REQUIREMENTS_QUALITY_GUIDE.md):
1. **Content Quality**: References, citations, formatting standards
2. **Performance**: Load time, readability, resource usage
3. **Accessibility**: WCAG level, screen reader support
4. **SEO**: Meta tags, structured data
5. **Security/Privacy**: Data handling, compliance
6. **Maintainability**: Code standards, documentation

**Example Quality Requirements**:
```markdown
**Quality Requirements**:
- Content: All statistics must have named sources (BUG-016 prevention)
- Performance: Article generation completes in <10 minutes
- Accessibility: Markdown follows semantic structure (H1 → H2 → H3)
- SEO: YAML frontmatter includes title, date, categories
- Maintainability: Agent prompts documented with rationale
```

### 6. Edge Case Detection & Escalation
**Input**: Story or requirement under analysis
**Output**: Escalation to human PO with specific question

**Escalation Triggers**:
- Ambiguous acceptance criteria (no clear pass/fail)
- Missing business value statement
- Conflicting requirements
- Complexity exceeds team capacity
- Cross-team dependencies
- Regulatory/compliance implications

**Escalation Format**:
```json
{
  "escalation_id": "ESC-042",
  "story_id": "STORY-123",
  "type": "ambiguous_requirement",
  "question": "AC states 'high quality' - what specific metrics define quality?",
  "context": "Similar past stories used 95% gate pass rate as quality metric",
  "recommendation": "Suggest: 'Quality: 95%+ editor gate pass rate'",
  "requires_human_decision": true
}
```

## Integration with SM Agent

**Handoff Protocol**:
1. PO Agent generates stories → `skills/backlog.json`
2. SM Agent validates DoR → signals PO Agent if gaps
3. PO Agent refines → re-submits to SM Agent
4. SM Agent accepts → begins sprint execution
5. PO Agent monitors → escalates blockers to human PO

**Shared Context**:
- `skills/backlog.json` - Prioritized stories with AC
- `skills/escalations.json` - Items needing human PO decision
- `skills/sprint_tracker.json` - Current sprint status

## Human Touch Points

**Required Human Approval**:
1. **Backlog Prioritization**: Human PO approves final priority order
2. **Acceptance Criteria Validation**: Human PO reviews generated AC
3. **Edge Case Resolution**: Human PO decides on escalated ambiguities
4. **Sprint Goal Approval**: Human PO confirms sprint theme/objectives

**Autonomous Decisions** (No Human Needed):
- Story formatting and structure
- Standard AC generation for common patterns
- Story point estimation (based on historical data)
- Quality requirements specification (from documented standards)

**Time Savings**:
- Before PO Agent: 6h/sprint (manual story breakdown + AC writing)
- With PO Agent: 3h/sprint (review + approve only)
- **50% reduction in PO time**

## Tools & Integration

### Input Sources
```bash
# User request parsing
INPUT: "We need to improve chart embedding validation"
PO_AGENT: Parses → extracts intent → generates story

# Historical data
REFERENCE: skills/agent_metrics.json (velocity patterns)
REFERENCE: skills/defect_tracker.json (quality patterns)
REFERENCE: SPRINT.md (completed story examples)
```

### Output Format
```json
{
  "story_id": "STORY-042",
  "title": "Enhance Chart Embedding Validation",
  "user_story": "As a Content Generator, I need automated chart embedding validation, so that charts are never orphaned in output/charts/ directory",
  "acceptance_criteria": [
    "Given chart_data exists, When Writer Agent generates article, Then chart markdown present in article body",
    "Given article without chart markdown, When Publication Validator runs, Then blocks publication with error",
    "Given chart embedded, When Visual QA runs, Then validates chart referenced in text",
    "Quality: 100% of charts embedded (was 0% in BUG-016)"
  ],
  "quality_requirements": {
    "content_quality": "Chart referenced naturally in text (not 'See figure 1')",
    "performance": "Validation adds <5s to publication pipeline",
    "maintainability": "Prevention pattern added to defect_prevention_rules.py"
  },
  "story_points": 3,
  "priority": "P0",
  "business_value": 9,
  "urgency": 10,
  "generated_by": "po_agent",
  "generated_at": "2026-01-02T15:00:00Z",
  "requires_human_approval": true,
  "escalations": []
}
```

## Implementation Notes

### Sprint 8 Story 1: Create PO Agent (3 points)

**File**: `scripts/po_agent.py` (NEW)

**Class Structure**:
```python
class ProductOwnerAgent:
    """Autonomous backlog refinement assistant"""

    def parse_user_request(self, request: str) -> dict:
        """Convert natural language → structured story"""

    def generate_acceptance_criteria(self, story: dict) -> list:
        """Generate testable AC from story"""

    def estimate_story_points(self, story: dict) -> int:
        """Estimate complexity using historical data"""

    def generate_quality_requirements(self, story: dict) -> dict:
        """Add non-functional requirements"""

    def prioritize_backlog(self, stories: list) -> list:
        """Score and rank stories by business value"""

    def detect_edge_cases(self, story: dict) -> list:
        """Identify ambiguities needing human PO decision"""

    def escalate_to_human(self, escalation: dict):
        """Add to escalations.json for human PO review"""
```

**LLM Integration**:
- Uses unified LLM client (llm_client.py)
- Temperature=0.3 for story generation (balance creativity + consistency)
- Temperature=0.0 for AC generation (deterministic)
- System prompt from `schemas/agents.yaml` (PO persona)

**Testing Strategy**:
```python
# tests/test_po_agent.py
def test_parse_user_request():
    """Verify story generation from natural language"""

def test_generate_acceptance_criteria():
    """Verify AC are testable and complete"""

def test_estimate_story_points():
    """Verify estimates match historical velocity"""

def test_quality_requirements():
    """Verify non-functional requirements included"""

def test_escalation_detection():
    """Verify ambiguous requirements flagged"""
```

**Success Metrics**:
- AC acceptance rate: >90% (human PO approves without changes)
- Escalation precision: >80% (escalations are genuine ambiguities)
- Time to generate: <2 min per story
- Human PO time: 50% reduction (6h → 3h per sprint)

## Quality Gates

**Pre-Generation Gate**:
- User request is not empty
- Business value is identifiable
- Stakeholder role can be inferred

**Post-Generation Gate**:
- Story follows "As a [role], I need [capability], so that [value]" format
- 3-7 acceptance criteria generated
- All AC are testable (Given/When/Then or measurable)
- Story points estimated with confidence score
- Quality requirements specified
- DoR validation ready (8-point checklist)

**Human Approval Gate**:
- Human PO reviews generated stories
- Human PO approves prioritization
- Human PO resolves escalations
- Human PO confirms sprint goal alignment

## Escalation Examples

**Type 1: Ambiguous Requirement**
```
User: "Make the system faster"
Escalation: "Define 'faster' - current: 10min/article, target: 5min? 2min?"
Recommendation: "Suggest: 'Generation time <5min (50% improvement)'"
```

**Type 2: Missing Business Value**
```
User: "Add caching to LLM responses"
Escalation: "Why is caching needed? Cost reduction? Speed? Reliability?"
Recommendation: "Clarify business driver before prioritizing"
```

**Type 3: Complexity Exceeds Capacity**
```
Story: "Implement full CrewAI migration"
Escalation: "Estimate: 40 story points, exceeds sprint capacity (13 pts)"
Recommendation: "Decompose into 3 sprints: Foundation → Coordination → Autonomy"
```

## Continuous Improvement

**Learning from History**:
- Analyze accepted vs rejected AC (improve generation quality)
- Track story point accuracy (refine estimation model)
- Identify common escalation patterns (reduce false positives)
- Learn from defect tracker (add preventive AC for known bugs)

**Metrics Dashboard**:
- AC acceptance rate trend
- Story point estimation accuracy (planned vs actual)
- Escalation rate and resolution time
- Human PO time per sprint

## References

**Industry Patterns**:
- AutoGen UserProxyAgent: Human representative in agent team
- CrewAI Task specification: Context, output format, tools
- SAFe Product Owner role: Outcomes definition, backlog prioritization

**Internal Documentation**:
- AUTONOMOUS_ORCHESTRATION_STRATEGY.md: Strategic vision
- REQUIREMENTS_QUALITY_GUIDE.md: Quality requirements framework
- AGENT_VELOCITY_ANALYSIS.md: Story point estimation model
- defect_tracker.json: Historical quality patterns

**Related Agents**:
- Scrum Master Agent: Receives stories, orchestrates execution
- Developer Agent (Sprint 9): Implements stories from AC
- QE Agent (Sprint 9): Validates against AC and DoD

---

**Version**: 1.0
**Created**: 2026-01-02 (Sprint 8 Pre-Work)
**Author**: Scrum Master Agent
**Status**: READY FOR IMPLEMENTATION

**Sprint 8 Story 1 Acceptance Criteria**:
- [x] PO Agent specification complete with capabilities defined
- [x] Integration with SM Agent documented
- [x] Human touch points identified (approval gates)
- [x] Success metrics defined (>90% AC acceptance, 50% time reduction)
- [x] Implementation notes with class structure
- [x] Testing strategy specified
- [ ] scripts/po_agent.py implemented (Sprint 8 execution)
- [ ] tests/test_po_agent.py created with 5+ test cases (Sprint 8 execution)
