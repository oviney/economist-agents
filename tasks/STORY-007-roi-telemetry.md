# STORY-007: Implement ROI Telemetry Hook

**Story Points**: 3 (capped from 3.2, actual effort 9 hours)  
**Priority**: P2 (Observability & Measurement)  
**Epic**: EPIC-001 Production-Grade Agentic Evolution  
**Status**: READY  
**Sprint**: 13  

## User Story

As a **business stakeholder**, I need **automated ROI telemetry** so that **I can validate efficiency claims with actual token costs vs human-hour equivalents**.

## Business Value

- **Prove ROI**: Replace anecdotal "50x faster" claims with measurable data
- **Cost Optimization**: Identify expensive LLM calls for optimization
- **Business Justification**: Defend agentic investment with hard numbers
- **Capacity Planning**: Forecast token costs for scaled operations

**João Moura Principle**: "Measure everything. Token costs are your reality check. If you can't measure ROI, you can't prove value."

## Acceptance Criteria

- [ ] **AC1**: execution_roi.json logs token usage per agent with <10ms overhead per LLM call
- [ ] **AC2**: Cost calculation accuracy within ±1% of actual API charges (validated against OpenAI/Anthropic billing)
- [ ] **AC3**: ROI multiplier shows efficiency gain (>100x expected vs human baseline)
- [ ] **AC4**: Writer/Editor agents tracked with per-agent token breakdown (input tokens, output tokens, cost)
- [ ] **AC5**: Integration tests pass validating telemetry accuracy (3+ test cases)

## Task Breakdown (6 tasks, 9 hours total)

### Task 1: ROI Schema Design (1h, P0)
**Goal**: Design execution_roi.json schema aligned with agent_metrics.json pattern

**Subtasks**:
1. Review existing validation schemas:
   - `schemas/agent_metrics_schema.json`
   - `schemas/defect_tracker_schema.json`
   - `skills/agent_metrics.json` (current usage)

2. Design `schemas/execution_roi_schema.json`:
   ```json
   {
     "$schema": "http://json-schema.org/draft-07/schema#",
     "title": "Execution ROI Telemetry",
     "description": "Token costs vs human-hour equivalents for ROI validation",
     "type": "object",
     "properties": {
       "version": {"type": "string", "const": "1.0"},
       "created": {"type": "string", "format": "date-time"},
       "sessions": {
         "type": "array",
         "items": {
           "type": "object",
           "properties": {
             "session_id": {"type": "string"},
             "timestamp": {"type": "string", "format": "date-time"},
             "topic": {"type": "string"},
             "category": {"type": "string"},
             "agents": {
               "type": "array",
               "items": {
                 "type": "object",
                 "properties": {
                   "agent_name": {"type": "string", "enum": ["research", "writer", "editor", "graphics"]},
                   "llm_calls": {"type": "integer", "minimum": 0},
                   "input_tokens": {"type": "integer", "minimum": 0},
                   "output_tokens": {"type": "integer", "minimum": 0},
                   "total_tokens": {"type": "integer", "minimum": 0},
                   "cost_usd": {"type": "number", "minimum": 0},
                   "execution_time_seconds": {"type": "number", "minimum": 0}
                 },
                 "required": ["agent_name", "total_tokens", "cost_usd"]
               }
             },
             "total_cost_usd": {"type": "number", "minimum": 0},
             "total_tokens": {"type": "integer", "minimum": 0},
             "human_hours_equivalent": {"type": "number", "minimum": 0},
             "efficiency_multiplier": {"type": "number", "minimum": 1}
           },
           "required": ["session_id", "timestamp", "agents", "total_cost_usd", "efficiency_multiplier"]
         }
       },
       "summary": {
         "type": "object",
         "properties": {
           "total_sessions": {"type": "integer", "minimum": 0},
           "total_cost_usd": {"type": "number", "minimum": 0},
           "avg_cost_per_article": {"type": "number", "minimum": 0},
           "avg_efficiency_multiplier": {"type": "number", "minimum": 1},
           "last_updated": {"type": "string", "format": "date-time"}
         }
       }
     },
     "required": ["version", "sessions", "summary"]
   }
   ```

3. Define human-hour baseline:
   - Research: 2 hours (manual research + source verification)
   - Writing: 3 hours (first draft + revisions)
   - Editing: 1 hour (5-gate review + polish)
   - Graphics: 1 hour (chart design + export)
   - **Total**: 7 hours per article (human baseline)

4. Define pricing model:
   ```python
   # OpenAI GPT-4o pricing (as of 2024)
   GPT4O_INPUT = 0.005 / 1000  # $0.005 per 1K tokens
   GPT4O_OUTPUT = 0.015 / 1000  # $0.015 per 1K tokens
   
   # Anthropic Claude 3 Sonnet pricing
   CLAUDE_SONNET_INPUT = 0.003 / 1000
   CLAUDE_SONNET_OUTPUT = 0.015 / 1000
   
   # Human cost (US market)
   HUMAN_RATE_USD = 50  # $50/hour senior writer rate
   ```

**Definition of Done**:
- [ ] `schemas/execution_roi_schema.json` created (JSON Schema Draft-07)
- [ ] Schema validated: `ajv validate -s schemas/execution_roi_schema.json -d logs/execution_roi.json`
- [ ] Human baseline documented (7 hours/article)
- [ ] Pricing model documented (GPT-4o, Claude rates)
- [ ] Approved by Data Architect

**Acceptance Validation**:
Schema follows JSON Schema Draft-07, aligned with agent_metrics.json pattern, human baseline defined.

---

### Task 2: ROI Tracker Implementation (2.5h, P0)
**Goal**: Create middleware to capture LLM token usage automatically

**Subtasks**:
1. Create `src/telemetry/roi_tracker.py`:
   ```python
   import json
   import time
   from datetime import datetime
   from pathlib import Path
   from typing import Dict, Any
   
   class ROITracker:
       """Tracks token usage and ROI metrics for content generation."""
       
       # Pricing per 1K tokens (as of 2024)
       PRICING = {
           'gpt-4o': {'input': 0.005, 'output': 0.015},
           'claude-3-sonnet': {'input': 0.003, 'output': 0.015},
       }
       
       # Human baseline (hours per agent task)
       HUMAN_BASELINE = {
           'research': 2.0,
           'writer': 3.0,
           'editor': 1.0,
           'graphics': 1.0,
       }
       HUMAN_RATE_USD = 50.0  # $50/hour
       
       def __init__(self, log_file: str = None):
           if log_file is None:
               log_file = Path(__file__).parent.parent.parent / 'logs' / 'execution_roi.json'
           self.log_file = Path(log_file)
           self.session = self._init_session()
       
       def _init_session(self) -> Dict[str, Any]:
           """Initialize a new session for tracking"""
           return {
               'session_id': f"session_{int(time.time())}",
               'timestamp': datetime.now().isoformat(),
               'topic': None,
               'category': None,
               'agents': [],
               'total_cost_usd': 0.0,
               'total_tokens': 0,
               'human_hours_equivalent': sum(self.HUMAN_BASELINE.values()),
               'efficiency_multiplier': 0.0,
           }
       
       def track_llm_call(self, agent_name: str, model: str, 
                          input_tokens: int, output_tokens: int, 
                          execution_time: float):
           """Record LLM call metrics"""
           # Calculate cost
           pricing = self.PRICING.get(model, {'input': 0.005, 'output': 0.015})
           cost = (input_tokens / 1000 * pricing['input'] + 
                   output_tokens / 1000 * pricing['output'])
           
           # Find or create agent entry
           agent_entry = next((a for a in self.session['agents'] 
                               if a['agent_name'] == agent_name), None)
           if not agent_entry:
               agent_entry = {
                   'agent_name': agent_name,
                   'llm_calls': 0,
                   'input_tokens': 0,
                   'output_tokens': 0,
                   'total_tokens': 0,
                   'cost_usd': 0.0,
                   'execution_time_seconds': 0.0,
               }
               self.session['agents'].append(agent_entry)
           
           # Update metrics
           agent_entry['llm_calls'] += 1
           agent_entry['input_tokens'] += input_tokens
           agent_entry['output_tokens'] += output_tokens
           agent_entry['total_tokens'] += (input_tokens + output_tokens)
           agent_entry['cost_usd'] += cost
           agent_entry['execution_time_seconds'] += execution_time
           
           # Update session totals
           self.session['total_cost_usd'] += cost
           self.session['total_tokens'] += (input_tokens + output_tokens)
       
       def calculate_roi(self) -> float:
           """Calculate efficiency multiplier (human cost / agent cost)"""
           human_cost = self.session['human_hours_equivalent'] * self.HUMAN_RATE_USD
           agent_cost = self.session['total_cost_usd']
           
           if agent_cost > 0:
               multiplier = human_cost / agent_cost
           else:
               multiplier = 0.0
           
           self.session['efficiency_multiplier'] = multiplier
           return multiplier
       
       def save_session(self):
           """Persist session to execution_roi.json"""
           self.calculate_roi()
           
           # Load existing data
           if self.log_file.exists():
               with open(self.log_file) as f:
                   data = json.load(f)
           else:
               data = {
                   'version': '1.0',
                   'created': datetime.now().isoformat(),
                   'sessions': [],
                   'summary': {
                       'total_sessions': 0,
                       'total_cost_usd': 0.0,
                       'avg_cost_per_article': 0.0,
                       'avg_efficiency_multiplier': 0.0,
                       'last_updated': None,
                   }
               }
           
           # Append session
           data['sessions'].append(self.session)
           
           # Update summary
           data['summary']['total_sessions'] = len(data['sessions'])
           data['summary']['total_cost_usd'] = sum(s['total_cost_usd'] for s in data['sessions'])
           data['summary']['avg_cost_per_article'] = (
               data['summary']['total_cost_usd'] / data['summary']['total_sessions']
           )
           data['summary']['avg_efficiency_multiplier'] = (
               sum(s['efficiency_multiplier'] for s in data['sessions']) / 
               data['summary']['total_sessions']
           )
           data['summary']['last_updated'] = datetime.now().isoformat()
           
           # Save
           self.log_file.parent.mkdir(parents=True, exist_ok=True)
           with open(self.log_file, 'w') as f:
               json.dump(data, f, indent=2)
   ```

2. Test locally:
   ```python
   tracker = ROITracker()
   tracker.session['topic'] = 'Test Article'
   tracker.track_llm_call('writer', 'gpt-4o', 1000, 500, 2.5)
   tracker.save_session()
   print(f"Efficiency: {tracker.calculate_roi():.2f}x")
   ```

**Definition of Done**:
- [ ] `src/telemetry/roi_tracker.py` created (200+ lines)
- [ ] ROITracker class with track_llm_call() and save_session()
- [ ] Pricing model implemented (GPT-4o, Claude Sonnet)
- [ ] ROI calculation validated: human_cost / agent_cost
- [ ] Local test passes with sample data

**Acceptance Validation**:
ROITracker middleware created, token tracking operational, ROI calculation accurate.

---

### Task 3: Instrument Agent Registry (2h, P0)
**Goal**: Hook ROI tracker into agent LLM calls

**Subtasks**:
1. Modify `scripts/agent_registry.py`:
   ```python
   from src.telemetry.roi_tracker import ROITracker
   
   class AgentRegistry:
       def __init__(self):
           self.roi_tracker = ROITracker()
       
       def execute_agent(self, agent_name, llm_call_fn, *args, **kwargs):
           """Wrapper for agent execution with ROI tracking"""
           start_time = time.time()
           
           # Execute LLM call
           result = llm_call_fn(*args, **kwargs)
           
           # Track metrics
           execution_time = time.time() - start_time
           self.roi_tracker.track_llm_call(
               agent_name=agent_name,
               model=kwargs.get('model', 'gpt-4o'),
               input_tokens=result.get('usage', {}).get('prompt_tokens', 0),
               output_tokens=result.get('usage', {}).get('completion_tokens', 0),
               execution_time=execution_time
           )
           
           return result
   ```

2. Update agent calls in `src/crews/stage3_crew.py`:
   - Wrap crew.kickoff() with ROI tracker
   - Extract token usage from CrewAI response
   - Pass model name (gpt-4o or claude-3-sonnet)

3. Update agent calls in `src/crews/stage4_crew.py`:
   - Same ROI tracking pattern
   - Separate editor vs final-editor tracking

4. Test integration:
   ```bash
   python3 scripts/economist_agent.py --topic "Test ROI Tracking"
   cat logs/execution_roi.json  # Verify session logged
   ```

**Definition of Done**:
- [ ] `scripts/agent_registry.py` modified (50+ lines changed)
- [ ] Stage3Crew and Stage4Crew instrumented
- [ ] Token usage extracted from CrewAI responses
- [ ] Integration test passes: session logged to execution_roi.json
- [ ] Overhead measured: <10ms per LLM call

**Acceptance Validation**:
Writer/Editor agents tracked, per-agent token breakdown accurate, overhead <10ms.

---

### Task 4: Validation Tests (1.5h, P0)
**Goal**: Comprehensive tests for ROI telemetry accuracy

**Subtasks**:
1. Create `tests/test_roi_telemetry.py`:
   ```python
   import pytest
   from src.telemetry.roi_tracker import ROITracker
   
   def test_cost_calculation():
       """Test token cost calculation accuracy"""
       tracker = ROITracker()
       
       # GPT-4o: 1000 input + 500 output tokens
       tracker.track_llm_call('writer', 'gpt-4o', 1000, 500, 2.5)
       
       # Expected: (1000/1000 * 0.005) + (500/1000 * 0.015) = 0.005 + 0.0075 = 0.0125
       assert abs(tracker.session['total_cost_usd'] - 0.0125) < 0.0001
   
   def test_roi_multiplier():
       """Test efficiency multiplier calculation"""
       tracker = ROITracker()
       
       # Simulate article generation
       tracker.track_llm_call('research', 'gpt-4o', 2000, 1000, 5.0)
       tracker.track_llm_call('writer', 'gpt-4o', 3000, 2000, 10.0)
       tracker.track_llm_call('editor', 'gpt-4o', 1500, 800, 3.0)
       
       # Calculate ROI
       multiplier = tracker.calculate_roi()
       
       # Human: 7 hours * $50 = $350
       # Agent: ~$0.10 (rough estimate)
       # Expected: >100x efficiency
       assert multiplier > 100
   
   def test_session_persistence():
       """Test execution_roi.json persistence"""
       tracker = ROITracker(log_file='tests/fixtures/test_roi.json')
       tracker.session['topic'] = 'Test Article'
       tracker.track_llm_call('writer', 'gpt-4o', 1000, 500, 2.5)
       tracker.save_session()
       
       # Verify file created
       assert Path('tests/fixtures/test_roi.json').exists()
       
       # Verify summary updated
       with open('tests/fixtures/test_roi.json') as f:
           data = json.load(f)
       assert data['summary']['total_sessions'] == 1
   ```

2. Add benchmark validation:
   - Compare logged costs against OpenAI/Anthropic billing
   - Target: ±1% accuracy

3. Add overhead tests:
   - Measure track_llm_call() execution time
   - Target: <10ms per call

**Definition of Done**:
- [ ] `tests/test_roi_telemetry.py` created (100+ lines)
- [ ] 3+ test cases passing (cost calculation, ROI multiplier, persistence)
- [ ] Accuracy validated: ±1% vs actual API charges
- [ ] Overhead validated: <10ms per LLM call
- [ ] Coverage >80%: `pytest --cov=src.telemetry.roi_tracker`

**Acceptance Validation**:
Integration tests pass (3+ cases), cost calculation accuracy ±1%, overhead <10ms.

---

### Task 5: Aggregation Queries (1.5h, P1)
**Goal**: Business intelligence queries for ROI dashboard

**Subtasks**:
1. Create `scripts/roi_analyzer.py`:
   ```python
   #!/usr/bin/env python3
   """ROI Analytics - Query and analyze execution_roi.json data"""
   
   import argparse
   import json
   from pathlib import Path
   
   def load_roi_data(log_file='logs/execution_roi.json'):
       with open(log_file) as f:
           return json.load(f)
   
   def query_avg_cost_per_article(data):
       """Calculate average cost per article"""
       return data['summary']['avg_cost_per_article']
   
   def query_efficiency_trend(data, limit=10):
       """Show efficiency multiplier trend (last N sessions)"""
       sessions = data['sessions'][-limit:]
       for s in sessions:
           print(f"{s['timestamp']}: {s['efficiency_multiplier']:.2f}x")
   
   def query_agent_breakdown(data, agent_name=None):
       """Show per-agent token usage and costs"""
       for session in data['sessions']:
           for agent in session['agents']:
               if agent_name is None or agent['agent_name'] == agent_name:
                   print(f"{agent['agent_name']}: {agent['total_tokens']} tokens, ${agent['cost_usd']:.4f}")
   
   def query_roi_validation(data):
       """Validate >100x efficiency claim"""
       avg_multiplier = data['summary']['avg_efficiency_multiplier']
       print(f"Average Efficiency: {avg_multiplier:.2f}x")
       print(f"ROI Claim Validated: {'YES' if avg_multiplier > 100 else 'NO'}")
   
   if __name__ == '__main__':
       parser = argparse.ArgumentParser(description='ROI Analytics')
       parser.add_argument('--avg-cost', action='store_true', help='Show average cost per article')
       parser.add_argument('--trend', type=int, default=10, help='Show efficiency trend (last N sessions)')
       parser.add_argument('--agent-breakdown', metavar='AGENT', help='Show per-agent costs')
       parser.add_argument('--validate-roi', action='store_true', help='Validate >100x efficiency')
       
       args = parser.parse_args()
       data = load_roi_data()
       
       if args.avg_cost:
           print(f"Average Cost: ${query_avg_cost_per_article(data):.4f}")
       elif args.trend:
           query_efficiency_trend(data, args.trend)
       elif args.agent_breakdown:
           query_agent_breakdown(data, args.agent_breakdown)
       elif args.validate_roi:
           query_roi_validation(data)
       else:
           parser.print_help()
   ```

2. Test queries:
   ```bash
   python3 scripts/roi_analyzer.py --avg-cost
   python3 scripts/roi_analyzer.py --trend 5
   python3 scripts/roi_analyzer.py --agent-breakdown writer
   python3 scripts/roi_analyzer.py --validate-roi
   ```

**Definition of Done**:
- [ ] `scripts/roi_analyzer.py` created (150+ lines)
- [ ] 4+ query functions implemented
- [ ] CLI interface operational
- [ ] Query performance <100ms per query
- [ ] Documentation in `--help` output

**Acceptance Validation**:
Aggregation queries operational, ROI multiplier shows >100x efficiency.

---

### Task 6: Documentation (0.5h, P2)
**Goal**: Update documentation with ROI telemetry usage

**Subtasks**:
1. Update `README.md`:
   ```markdown
   ## ROI Telemetry
   
   Token costs and efficiency metrics logged to `logs/execution_roi.json`:
   
   - **Average Cost**: $0.10 per article
   - **Human Baseline**: 7 hours * $50/hour = $350
   - **Efficiency**: 350x faster, 3500x cheaper
   
   ### Analyze ROI Data
   
   ```bash
   python3 scripts/roi_analyzer.py --validate-roi
   python3 scripts/roi_analyzer.py --avg-cost
   python3 scripts/roi_analyzer.py --agent-breakdown writer
   ```
   ```

2. Create `docs/ROI_TELEMETRY.md`:
   - Schema documentation
   - Pricing model explanation
   - Human baseline justification
   - Query examples

**Definition of Done**:
- [ ] README.md updated with ROI telemetry section
- [ ] `docs/ROI_TELEMETRY.md` created (100+ lines)
- [ ] Usage examples tested and verified

**Acceptance Validation**:
Documentation complete, usage examples operational.

---

## Technical Specifications

### File Modifications
- **CREATE**: `schemas/execution_roi_schema.json` (150 lines)
- **CREATE**: `src/telemetry/roi_tracker.py` (200 lines)
- **CREATE**: `scripts/roi_analyzer.py` (150 lines)
- **CREATE**: `tests/test_roi_telemetry.py` (100 lines)
- **CREATE**: `docs/ROI_TELEMETRY.md` (100 lines)
- **MODIFY**: `scripts/agent_registry.py` (50 lines changed)
- **MODIFY**: `src/crews/stage3_crew.py` (20 lines changed)
- **MODIFY**: `src/crews/stage4_crew.py` (20 lines changed)
- **MODIFY**: `README.md` (20 lines added)

### Pricing Model (2024 rates)
```python
GPT4O = {'input': 0.005/1000, 'output': 0.015/1000}  # $0.005 / $0.015 per 1K
CLAUDE_SONNET = {'input': 0.003/1000, 'output': 0.015/1000}  # $0.003 / $0.015 per 1K
HUMAN_RATE = 50  # $50/hour senior writer
```

### Human Baseline (hours per task)
- Research: 2 hours
- Writing: 3 hours
- Editing: 1 hour
- Graphics: 1 hour
- **Total**: 7 hours/article = $350 human cost

### Integration Points
- **agent_registry.py**: Wrapper for LLM calls with ROI tracking
- **Stage3Crew**: Research + Writer + Graphics agents
- **Stage4Crew**: Reviewer + Editor agents
- **CrewAI**: Extract token usage from crew.kickoff() response

### Quality Gates
- [ ] All unit tests pass: `pytest tests/test_roi_telemetry.py -v`
- [ ] Cost calculation ±1% accurate vs API billing
- [ ] Overhead <10ms per LLM call
- [ ] ROI multiplier >100x (validates efficiency claim)
- [ ] Schema validation passes: `ajv validate`

### Risk Mitigation
1. **Overhead**: Async logging, <10ms target
2. **Pricing changes**: Configurable pricing model in code
3. **PII in logs**: No user data, only aggregate metrics
4. **Log rotation**: 30-day rotation, auto-cleanup old sessions

## Dependencies

**Blocks**:
- None (independent observability work)

**Blocked By**:
- None (parallel execution with STORY-005/006)

**Parallel Execution**:
- Can run fully in parallel with STORY-005 and STORY-006

## Validation Checklist

- [ ] Task 1: execution_roi.json schema designed and validated
- [ ] Task 2: ROITracker middleware implemented
- [ ] Task 3: Agent registry instrumented with ROI tracking
- [ ] Task 4: Integration tests passing (3+ cases, ±1% accuracy)
- [ ] Task 5: Aggregation queries operational
- [ ] Task 6: Documentation complete (README.md, ROI_TELEMETRY.md)
- [ ] All acceptance criteria met (5/5)
- [ ] Code review approved by Data Architect
- [ ] Business stakeholder sign-off on ROI validation

---

**Created**: 2026-01-04  
**Last Updated**: 2026-01-04  
**Assigned To**: @migration-engineer  
**Story Status**: READY  
