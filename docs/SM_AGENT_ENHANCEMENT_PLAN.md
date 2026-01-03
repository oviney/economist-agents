# Scrum Master Agent Enhancement Plan
**Sprint 8 Story 2: Autonomous Coordination (4 points)**

## Strategic Context

**Current State** (Sprint 7):
- Manual orchestration: Human SM coordinates all agent handoffs
- Serial workflow: Research → Writer → Editor → Graphics (manual routing)
- Time overhead: 33% (120 min coordination per 240 min agent execution)
- Bottleneck: Human becomes bottleneck at >3 parallel stories

**Target State** (Sprint 8+):
- Autonomous orchestration: SM Agent coordinates without human intervention
- Event-driven workflow: Agents signal completion, SM routes automatically
- Time overhead: <10% (SM Agent overhead minimal)
- Scalability: Support 5+ parallel stories via task queue

**Vision** (3-Sprint Transformation):
- Sprint 8: Foundation (PO + SM agents coordinate)
- Sprint 9: Consolidation (Developer + QE agents execute end-to-end)
- Sprint 10: Full autonomy (DevOps agent closes loop)

---

## Enhancement Architecture

### Current Capabilities (Sprint 7)
From `.github/agents/scrum-master.agent.md`:
- Sprint planning: Parse goals, validate DoR
- Sprint execution: Track progress, identify blockers
- Sprint close: Generate retrospective, calculate metrics
- GitHub integration: Sync issues, milestones, projects

**Limitation**: Requires human to assign tasks, verify handoffs, coordinate reviews

### New Capabilities (Sprint 8)

#### 1. Task Queue Management
**Purpose**: Autonomous task breakdown and assignment

**Components**:
```python
class TaskQueueManager:
    def parse_backlog(self, stories: list) -> list[Task]:
        """Convert stories from backlog.json → executable tasks"""

    def assign_to_agent(self, task: Task) -> str:
        """Determine which specialist agent should handle task"""

    def update_queue(self, task_id: str, status: str):
        """Update task status (pending → assigned → in_progress → complete)"""

    def get_next_task(self) -> Task:
        """Get highest priority unassigned task"""
```

**Data Structure** (`skills/task_queue.json`):
```json
{
  "sprint_id": 8,
  "tasks": [
    {
      "task_id": "TASK-042-1",
      "story_id": "STORY-042",
      "title": "Generate article with Economist voice",
      "assigned_to": "developer_agent",
      "status": "in_progress",
      "priority": "P0",
      "acceptance_criteria": ["AC1", "AC2"],
      "depends_on": ["TASK-042-0"],
      "created_at": "2026-01-02T10:00:00Z",
      "assigned_at": "2026-01-02T10:05:00Z",
      "completed_at": null
    }
  ]
}
```

#### 2. Agent Status Monitoring
**Purpose**: Track agent progress via status signals (event-driven)

**Components**:
```python
class AgentStatusMonitor:
    def poll_status_updates(self) -> list[StatusSignal]:
        """Read agent_status.json for new completion signals"""

    def determine_next_agent(self, completed_task: Task) -> str:
        """Workflow routing: Research → Writer → Editor → Graphics"""

    def detect_blockers(self) -> list[BlockedAgent]:
        """Identify agents waiting on dependencies or escalations"""

    def escalate_blocker(self, agent_id: str, reason: str):
        """Add to escalations.json for human PO review"""
```

**Data Structure** (`skills/agent_status.json`):
```json
{
  "agents": [
    {
      "agent_id": "developer_agent",
      "current_task": "TASK-042-1",
      "status": "complete",
      "output": {
        "path": "output/2026-01-02-article.md",
        "word_count": 810,
        "chart_embedded": true
      },
      "self_validation": {
        "passed": true,
        "checks": ["economist_voice", "chart_embedded", "word_count_800+"]
      },
      "completed_at": "2026-01-02T11:30:00Z",
      "next_agent": "qe_agent"
    }
  ]
}
```

#### 3. Quality Gate Automation
**Purpose**: Make DoR/DoD decisions without human intervention

**Components**:
```python
class QualityGateValidator:
    def validate_dor(self, story: dict) -> tuple[bool, list[str]]:
        """8-point DoR checklist validation"""

    def validate_dod(self, deliverable: dict) -> tuple[bool, list[str]]:
        """Definition of Done validation"""

    def make_gate_decision(self, validation_result: tuple) -> str:
        """Approve, Reject, or Escalate based on validation"""

    def send_back_for_fixes(self, task_id: str, issues: list):
        """Reassign to agent with fix requirements"""
```

**Gate Logic**:
```
DoR Validation:
  IF all 8 criteria met → APPROVE (assign to developer_agent)
  IF 1-2 criteria missing → ESCALATE (ask PO Agent to refine)
  IF >2 criteria missing → REJECT (block sprint start)

DoD Validation:
  IF all checks pass → APPROVE (mark story complete)
  IF critical check fails → REJECT (send back with specific fixes)
  IF edge case detected → ESCALATE (human PO decides)
```

#### 4. Escalation Management
**Purpose**: Route edge cases to human PO with context

**Components**:
```python
class EscalationManager:
    def create_escalation(self, issue: dict) -> str:
        """Generate escalation with question for human PO"""

    def check_for_resolution(self, escalation_id: str) -> bool:
        """Check if human PO has responded"""

    def apply_resolution(self, escalation_id: str):
        """Update task queue with human PO decision"""
```

**Escalation Types**:
1. **Ambiguous AC**: Acceptance criteria not testable
2. **DoR Gap**: Story missing required information
3. **DoD Failure**: Critical quality check failed
4. **Dependency Blocker**: External dependency unavailable
5. **Resource Constraint**: Agent capacity exceeded

**Data Structure** (`skills/escalations.json`):
```json
{
  "escalations": [
    {
      "escalation_id": "ESC-042",
      "story_id": "STORY-042",
      "task_id": "TASK-042-1",
      "type": "ambiguous_ac",
      "question": "AC states 'high quality' - define measurable criteria?",
      "context": {
        "story_title": "Enhance chart validation",
        "problematic_ac": "Charts must be high quality",
        "similar_stories": ["STORY-020: Used 95% gate pass rate"]
      },
      "recommendation": "Suggest: 'Quality: 95%+ Visual QA pass rate'",
      "raised_by": "sm_agent",
      "raised_at": "2026-01-02T12:00:00Z",
      "requires_human_decision": true,
      "resolved": false,
      "resolution": null
    }
  ]
}
```

---

## Orchestration Loop Design

### Main Loop (Autonomous Sprint Execution)
```python
class ScrumMasterAgent:
    def run_sprint(self, sprint_id: int):
        """Main orchestration loop"""

        # 1. Initialize sprint
        self.validate_dor_for_all_stories()
        self.create_task_queue()

        # 2. Orchestration loop
        while self.sprint_active():
            # Check for completed tasks
            completed_tasks = self.monitor.poll_status_updates()
            for task in completed_tasks:
                self.handle_task_completion(task)

            # Check for blocked agents
            blocked = self.monitor.detect_blockers()
            for agent in blocked:
                self.handle_blocker(agent)

            # Check quality gates
            tasks_awaiting_approval = self.queue.get_awaiting_approval()
            for task in tasks_awaiting_approval:
                self.validate_and_decide(task)

            # Check escalations
            unresolved = self.escalation_manager.get_unresolved()
            if unresolved:
                self.notify_human_po(unresolved)

            # Wait for next event
            time.sleep(30)  # Poll every 30 seconds

        # 3. Sprint close
        self.generate_retrospective()
        self.update_metrics()

    def handle_task_completion(self, task: Task):
        """Route to next agent or mark complete"""

        # Validate output
        if not task.self_validation_passed:
            self.send_back_for_fixes(task)
            return

        # Determine next step
        next_agent = self.determine_next_agent(task)

        if next_agent:
            # Assign to next agent in workflow
            next_task = self.queue.create_handoff_task(task, next_agent)
            self.queue.assign_to_agent(next_task, next_agent)
        else:
            # Final task in workflow
            if self.validate_dod(task):
                self.mark_story_complete(task.story_id)
            else:
                self.escalate_dod_failure(task)
```

### Workflow Routing
```python
WORKFLOW_SEQUENCE = {
    "research_agent": "writer_agent",
    "writer_agent": "editor_agent",
    "editor_agent": "graphics_agent",
    "graphics_agent": "qe_agent",
    "qe_agent": None  # End of workflow
}

def determine_next_agent(self, completed_task: Task) -> str:
    """Get next agent in sequential workflow"""
    return WORKFLOW_SEQUENCE.get(completed_task.assigned_to)
```

---

## Integration with PO Agent

### Handoff Protocol
**Phase 1: Backlog Refinement** (PO Agent → SM Agent)
1. PO Agent generates stories → writes to `skills/backlog.json`
2. SM Agent reads backlog → validates DoR for each story
3. If DoR gaps detected → SM escalates to PO Agent for refinement
4. PO Agent refines → updates backlog
5. SM Agent re-validates → approves for sprint

**Phase 2: Sprint Execution** (SM Agent orchestrates)
1. SM Agent creates task queue from approved backlog
2. SM Agent assigns tasks to specialist agents
3. Agents execute → signal completion
4. SM Agent routes between agents
5. SM Agent validates DoD → marks stories complete

**Phase 3: Human Validation** (SM Agent → Human PO)
1. SM Agent presents completed stories
2. Human PO reviews deliverables
3. Human PO approves or requests changes
4. If changes needed → SM Agent creates new tasks

---

## Human Touch Points

**Preserved Touch Points** (High Value):
1. **Backlog Prioritization**: Human PO approves story priority order
2. **Acceptance Criteria Validation**: Human PO reviews PO Agent-generated AC
3. **Escalation Resolution**: Human PO decides on edge cases
4. **Deliverable Validation**: Human PO approves final outputs

**Eliminated Touch Points** (Low Value, High Overhead):
1. ❌ Task breakdown (SM Agent automates)
2. ❌ Agent assignment (SM Agent routes)
3. ❌ Progress tracking (SM Agent monitors)
4. ❌ Handoff verification (SM Agent validates)
5. ❌ Quality gate decisions (SM Agent decides, escalates failures)

**Time Savings**:
- Before: 8h/sprint (manual coordination)
- After: 4h/sprint (approve priorities, resolve escalations, validate deliverables)
- **50% reduction in human SM time**

---

## Testing Strategy

### Unit Tests (`tests/test_sm_agent.py`)
```python
def test_parse_backlog_to_tasks():
    """Verify story → task decomposition"""

def test_assign_task_to_agent():
    """Verify agent routing logic"""

def test_validate_dor():
    """Verify 8-point DoR validation"""

def test_validate_dod():
    """Verify DoD checklist validation"""

def test_escalation_creation():
    """Verify edge case detection"""

def test_orchestration_loop():
    """Verify full sprint execution (mock agents)"""
```

### Integration Tests
```python
def test_sm_agent_with_po_agent():
    """End-to-end backlog refinement"""

def test_sm_agent_orchestration():
    """Full sprint with mock specialist agents"""

def test_escalation_workflow():
    """Edge case → escalation → resolution → continue"""
```

---

## Success Metrics

### Sprint 8 Story 2 Success Criteria
- [ ] Given prioritized backlog, When SM Agent starts sprint, Then creates task queue
- [ ] Given task complete, When agent signals done, Then SM assigns to next agent
- [ ] Given DoR validation, When criteria missing, Then blocks start and escalates
- [ ] Given DoD validation, When checks fail, Then sends back for fixes
- [ ] Given edge case, When detected, Then escalates with structured question
- [ ] Quality: >90% of task assignments automated
- [ ] Quality: Orchestration tests passing (5+ test cases)

### Sprint 8 Overall Success
- [ ] Human SM time: 50% reduction (8h → 4h per sprint)
- [ ] Task assignment automation: >90%
- [ ] Quality gate automation: >90%
- [ ] Escalation precision: >80% (genuine ambiguities)

---

## Implementation Notes

### File Structure
**New File**: `scripts/sm_agent.py` (600+ lines)
```python
class ScrumMasterAgent:
    """Autonomous sprint orchestrator"""

    def __init__(self):
        self.queue = TaskQueueManager()
        self.monitor = AgentStatusMonitor()
        self.gates = QualityGateValidator()
        self.escalations = EscalationManager()

    # Orchestration methods
    def run_sprint(self, sprint_id: int)
    def handle_task_completion(self, task: Task)
    def determine_next_agent(self, task: Task) -> str

    # Quality gates
    def validate_dor(self, story: dict) -> bool
    def validate_dod(self, task: Task) -> bool

    # Escalation management
    def escalate(self, issue: dict) -> str
    def check_escalations(self) -> list
```

**Enhanced File**: `.github/agents/scrum-master.agent.md`
- Add autonomous orchestration section
- Document task queue management
- Specify quality gate automation
- Update human touch points

### Dependencies
- LLM client (llm_client.py) for decision-making
- Sprint tracker (sprint_tracker.json) for state
- Agent status (agent_status.json) for signals
- Defect tracker (defect_tracker.json) for quality patterns

---

## Risk Mitigation

### Risk: Complex Coordination Logic
**Mitigation**: Start with simple sequential workflow (no branching)
**Test**: Mock agents for deterministic testing
**Fallback**: Manual SM coordination if >30% tasks fail handoff

### Risk: Quality Gate Bypass
**Mitigation**: SM Agent cannot override gates, only escalate
**Test**: Negative test cases (missing DoR, failing DoD)
**Fallback**: Increase human validation if quality drops >20%

### Risk: Escalation Overload
**Mitigation**: Auto-resolve known patterns before escalating
**Test**: Measure escalation precision (target >80% genuine)
**Fallback**: Refine escalation logic if false positive rate >30%

---

## Next Steps After Story 2 Complete

**Immediate** (Sprint 8 Story 3):
- Implement agent signal infrastructure
- Create sprint dashboard for monitoring
- Test end-to-end autonomous sprint

**Sprint 9**:
- Create Developer Agent (consolidate Research + Writer + Graphics)
- Create QE Agent (automated DoD validation)
- Test multi-agent coordination at scale

**Sprint 10**:
- Create DevOps Agent (deployment automation)
- Run full autonomous sprint test
- Measure velocity improvement (target 2x)

---

**Document Status**: ✅ COMPLETE - Ready for Implementation
**Created**: 2026-01-02 (Sprint 8 Pre-Work)
**Author**: Scrum Master Agent
**Next**: Implement when Story 1 (PO Agent) completes

**Pre-Work Complete** - SM Agent enhancement plan ready for Sprint 8 Story 2 execution.
