# Agent Prompt Patterns Library

**Purpose**: Reusable prompt templates validated through Sprint 7 Day 1-2 execution.

**Status**: Production-validated patterns with proven effectiveness.

**Last Updated**: 2026-01-02

---

## Pattern Catalog

### 1. Bug Logging Pattern

**Use When**: New defect discovered requiring GitHub issue + defect tracker entry.

**Template**:
```
New bug: [issue description]
Current state: [what's wrong]
Impact: [severity - CRITICAL/HIGH/MEDIUM/LOW]
Expected: [correct behavior]

Create GitHub issue and log in defect tracker.
```

**Example**:
```
New bug: README badges show stale data
Current state: Quality score badge links to outdated report, coverage shows 45% but actual is 52%
Impact: HIGH - New developers/stakeholders see incorrect metrics
Expected: Badges dynamically pull from latest CI artifacts or shield.io dynamic sources

Create GitHub issue and log in defect tracker.
```

**Expected Outcome**:
- GitHub issue created with proper labels
- Defect tracker entry with RCA template
- Severity properly classified
- Clear reproduction steps

**Validation**: Used in Sprint 7 for BUG-023, resulted in complete issue documentation.

---

### 2. Process Improvement Pattern

**Use When**: Process gap identified requiring systematic fix (not just one-time correction).

**Template**:
```
PROCESS IMPROVEMENT: [gap identified]
Root cause: [analysis of why gap exists]
Actions:
1. [First improvement action]
2. [Second improvement action]
3. [Third improvement action]

Execute improvements and report when complete.
```

**Example**:
```
PROCESS IMPROVEMENT: DoR violations caught manually instead of automated gate
Root cause: No system validation of sprint ceremony sequence
Actions:
1. Create sprint_ceremony_tracker.py with state management
2. Implement --can-start validation blocking
3. Add pre-commit hook integration
4. Document end-of-sprint workflow

Execute improvements and report when complete.
```

**Expected Outcome**:
- Root cause analysis documented
- Numbered action plan clear and executable
- Implementation completed autonomously
- Results reported with metrics

**Validation**: Used in Sprint 6 for Sprint Ceremony Tracker, delivered in 3 hours with full automation.

---

### 3. Story Execution Pattern

**Use When**: Starting work on a sprint story with clear brief/context.

**Template**:
```
Execute Story N: [title]
Read [context file/brief]
Tasks:
1. [Task description] (effort estimate)
2. [Task description] (effort estimate)
3. [Task description] (effort estimate)

Report at [checkpoint - e.g., "each task completion", "final completion", "every 2 hours"]
```

**Example**:
```
Execute Story 1: Strengthen Editor Agent Prompt
Read docs/EDITOR_AGENT_DIAGNOSIS.md for background
Tasks:
1. Enhance EDITOR_AGENT_PROMPT with explicit PASS/FAIL format (60 min)
2. Add "REQUIRED OUTPUT FORMAT" section with template (30 min)
3. Test with sample article, measure gate pass rate (30 min)

Report at each task completion
```

**Expected Outcome**:
- All tasks completed in sequence
- Effort estimates validated (actual vs estimated)
- Progress checkpoints reported as specified
- DoD criteria met before marking complete

**Validation**: Used in Sprint 8 Stories 1-3, all completed with 100% acceptance criteria met.

---

### 4. Blocker Escalation Pattern

**Use When**: Critical decision needed that blocks sprint progress.

**Template**:
```
CRITICAL BLOCKER: [issue description]
Options:
A. [Option name] - [pros/cons]
B. [Option name] - [pros/cons]
C. [Option name] - [pros/cons]

Recommend [Option X] based on:
- Sprint priorities: [alignment]
- Risk assessment: [analysis]
- Effort trade-offs: [comparison]

Request approval to proceed.
```

**Example**:
```
CRITICAL BLOCKER: Sprint Ceremony Tracker vs Sprint 7 planning
Options:
A. Build tracker first (3h) - Dogfood immediately, validate before committing
B. Manual ceremonies (1h), tracker as Story 1 - Faster sprint start, deferred validation
C. Skip tracker - Fast but no prevention of future DoR violations

Recommend Option A based on:
- Sprint priorities: Quality-first culture (proven by prevention system)
- Risk assessment: 2h delay acceptable for systematic prevention
- Effort trade-offs: 3h investment prevents recurring manual catching

Request approval to proceed.
```

**Expected Outcome**:
- All viable options presented with analysis
- Clear recommendation with justification
- User makes informed decision
- Chosen path executed autonomously

**Validation**: Used in Sprint 6 for Sprint Ceremony Tracker decision, team voted 3-1 for Option A.

---

### 5. Requirement Traceability Pattern

**Use When**: Bug report needs classification (defect vs enhancement).

**Template**:
```
REQUIREMENT TRACEABILITY: Does [behavior] align with original requirement?

Check docs/REQUIREMENTS_REGISTRY.md for:
- Component: [agent/system name]
- Original story: [STORY-XXX if known]
- Expected behavior: [what was specified]

If requirement existed → Bug with requirement link
If requirement missing → Enhancement/Feature request

Classify and route appropriately.
```

**Example**:
```
REQUIREMENT TRACEABILITY: Does Writer Agent article length requirement exist?

Check docs/REQUIREMENTS_REGISTRY.md for:
- Component: writer_agent
- Original story: STORY-002 (Writer Agent implementation)
- Expected behavior: 800-1200 words specified in prompt

Query: Was 800-word minimum explicitly required?

If YES → Bug (articles violating minimum)
If NO → Enhancement (add length requirement)

Classify and route appropriately.
```

**Expected Outcome**:
- Requirements registry consulted
- Original specification retrieved
- Classification correct (bug vs enhancement)
- Prevents misclassification of enhancements as bugs

**Validation**: Pattern documented in Sprint 7 after BUG-024 misclassification risk identified.

---

### 6. Sprint Orchestration Pattern

**Use When**: Multiple parallel workstreams require coordination within sprint.

**Template**:
```
Orchestrate parallel execution:

Track 1: [Agent/team] - [work description]
- Checkpoint: [time interval]
- Deliverable: [output]

Track 2: [Agent/team] - [work description]
- Checkpoint: [time interval]
- Deliverable: [output]

Track 3: [Agent/team] - [work description]
- Checkpoint: [time interval]
- Deliverable: [output]

Monitor every [interval]. Update [log location]. Report consolidated status.
```

**Example**:
```
Orchestrate parallel execution:

Track 1: Research Agent - Gather 10 topic candidates
- Checkpoint: Every 30 minutes
- Deliverable: content_queue.json with scored topics

Track 2: Editorial Board - Review queued topics
- Checkpoint: After Track 1 complete
- Deliverable: board_decision.json with ranked picks

Track 3: Writer Agent - Generate article for top pick
- Checkpoint: After Track 2 complete
- Deliverable: Markdown article + embedded chart

Monitor every 2h. Update docs/SPRINT.md. Report consolidated status.
```

**Expected Outcome**:
- Parallel work streams clear and non-overlapping
- Dependencies identified (Track 2 waits for Track 1)
- Regular checkpoints enable early intervention
- Consolidated reporting shows holistic progress

**Validation**: Pattern used in Sprint 5 for parallel story execution, enabled autonomous multi-track work.

---

### 7. Fresh Start Pattern

**Use When**: Resuming work after context switch, new session, or handoff.

**Template**:
```
Resume [story/sprint/task]

Context:
- Read [context file] for background
- Current status: [brief state summary]
- Last checkpoint: [what was completed]

Proceed with: [next action/task]
```

**Example**:
```
Resume Sprint 7 Story 2

Context:
- Read docs/STORY_2_CONTEXT.md for background
- Current status: Test gap analyzer implemented, 4 recommendations generated
- Last checkpoint: test_gap_analyzer.py complete with CLI

Proceed with: Generate TEST_GAP_REPORT.md with actionable recommendations
```

**Expected Outcome**:
- Context quickly restored from designated file
- No redundant work (knows what's done)
- Smooth continuation from last checkpoint
- Maintains sprint momentum across sessions

**Validation**: Pattern used in Sprint 7 Day 2, enabled seamless continuation after 12h break.

---

## Pattern Usage Guidelines

### When to Use Templates

**DO use templates for**:
- Repetitive operations (bug logging, story execution)
- Critical decisions requiring structure (blockers, options analysis)
- Handoffs between sessions/agents
- Process improvements requiring systematic action

**DON'T use templates for**:
- Exploratory conversations
- Clarifying questions
- Simple status checks
- One-off unique situations

### Template Customization

**Mandatory Fields**: All [...] placeholders must be filled
**Optional Fields**: May be omitted if not applicable
**Format**: Maintain structure, adapt content to context

### Combining Patterns

Templates can be combined for complex scenarios:

```
Fresh Start Pattern → Story Execution Pattern → Bug Logging Pattern

Example flow:
1. Resume Sprint 8 Story 1 (Fresh Start)
2. Execute Story 1: Strengthen Editor Agent (Story Execution)
3. New bug: Editor still has 40% fail rate (Bug Logging)
```

---

## Pattern Metrics

**Sprint 7 Validation Data**:

| Pattern | Uses | Success Rate | Avg Response Quality |
|---------|------|--------------|---------------------|
| Bug Logging | 3 | 100% | Complete documentation |
| Process Improvement | 2 | 100% | Autonomous execution |
| Story Execution | 3 | 100% | All acceptance criteria met |
| Blocker Escalation | 1 | 100% | Clear decision made |
| Requirement Traceability | 1 | 100% | Correct classification |
| Sprint Orchestration | 0 | N/A | Not used in Sprint 7 |
| Fresh Start | 2 | 100% | Seamless context restore |

**Overall Effectiveness**: 11/12 uses successful (92%)

---

## Anti-Patterns

### 1. Vague Bug Reports

❌ **Bad**:
```
There's a problem with the charts.
```

✅ **Good** (use Bug Logging Pattern):
```
New bug: Chart labels overlap X-axis zone
Current state: Inline labels placed at y<20 overlap year labels
Impact: MEDIUM - Visual QA catches 50% of violations
Expected: All labels must be in chart zone (y>20) per CHART_DESIGN_SPEC.md

Create GitHub issue and log in defect tracker.
```

### 2. Open-Ended Blockers

❌ **Bad**:
```
Not sure what to do about this issue. What do you think?
```

✅ **Good** (use Blocker Escalation Pattern):
```
CRITICAL BLOCKER: Writer Agent regeneration increases token cost 40%
Options:
A. Accept cost, optimize elsewhere
B. Reduce regeneration triggers (may reduce quality)
C. Implement caching for common patterns

Recommend Option C based on sprint priorities...
```

### 3. Ambiguous Story Starts

❌ **Bad**:
```
Work on the quality gates story.
```

✅ **Good** (use Story Execution Pattern):
```
Execute Story 2: Enhance Visual QA Coverage
Read docs/EDITOR_AGENT_DIAGNOSIS.md for context
Tasks:
1. Implement ZoneBoundaryValidator class (90 min)
2. Integrate with run_visual_qa_agent() (60 min)
3. Test with known zone violations (30 min)

Report at each task completion
```

---

## Continuous Improvement

### Pattern Evolution

**Add new patterns when**:
- Same prompt structure used 3+ times successfully
- Pattern enables autonomous execution
- Template fills communication gap

**Deprecate patterns when**:
- Success rate <50% over 10 uses
- Context drift makes template obsolete
- Better pattern emerges

### Feedback Loop

1. **Try pattern** → Use template in real work
2. **Measure outcome** → Success rate, response quality
3. **Refine template** → Fix gaps, improve clarity
4. **Update library** → Document improvements

---

## Pattern Library Maintenance

**Review Frequency**: After each sprint
**Update Trigger**: 3+ uses of same prompt structure
**Owner**: Scrum Master
**Contributors**: All team members (submit patterns that work)

**Version History**:
- **v1.0** (2026-01-02): Initial library from Sprint 7 patterns
  - 7 patterns documented
  - 92% success rate across 12 uses
  - Sprint 7 Day 1-2 validation

---

## Related Documentation

- [SCRUM_MASTER_PROTOCOL.md](SCRUM_MASTER_PROTOCOL.md) - Process discipline rules
- [DEFECT_PREVENTION.md](DEFECT_PREVENTION.md) - Bug prevention patterns
- [GOVERNANCE_GUIDE.md](GOVERNANCE_GUIDE.md) - Interactive approval gates
- [REQUIREMENTS_REGISTRY.md](REQUIREMENTS_REGISTRY.md) - Requirement traceability

---

## Quick Reference Card

```
BUG:        New bug: [X]. Current: [Y]. Impact: [Z]. Expected: [W]. Create issue + log.
PROCESS:    PROCESS IMPROVEMENT: [gap]. Root: [cause]. Actions: [1,2,3]. Execute + report.
STORY:      Execute Story N: [title]. Read [brief]. Tasks: [1,2,3]. Report at [checkpoint].
BLOCKER:    CRITICAL BLOCKER: [X]. Options: A/B/C. Recommend [Y]. Request approval.
TRACEABILITY: Does REQ-XXX exist? If NO → Enhancement. If YES → Bug + link.
ORCHESTRATE: Track 1 [agent/work], Track 2 [agent/work]. Monitor [interval]. Report.
RESUME:     Resume [X]. Read [context]. Status: [Y]. Proceed with: [Z].
```

---

**END OF PATTERN LIBRARY**
