# CrewAI Fundamentals → Economist-Agents Mapping

## 1. Core CrewAI Concepts

### Agents
**Definition**: Specialized AI workers with defined roles, goals, and backstories. Each agent has expertise and responsibilities.

| CrewAI Concept | Your Economist-Agents Equivalent |
|----------------|----------------------------------|
| `role` | Your 6 persona agents (VP of Engineering, Senior QE Lead, Data Skeptic, Career Climber, Economist Editor, Busy Reader) |
| `goal` | Each persona's voting criteria and perspective |
| `backstory` | The persona's professional context that shapes their evaluation |
| `tools` | Your agents currently use direct API calls; CrewAI would formalize tool access |

**CrewAI Agent Definition Example:**
```python
from crewai import Agent

research_agent = Agent(
    role='Quality Engineering Researcher',
    goal='Gather accurate, current data on QE trends with verified sources',
    backstory='20-year veteran of enterprise QE consulting who demands rigorous sourcing',
    verbose=True,
    tools=[web_search_tool, data_analysis_tool]
)
```

### Tasks
**Definition**: Specific assignments with descriptions, expected outputs, and assigned agents.

| CrewAI Concept | Your Current Implementation |
|----------------|----------------------------|
| `description` | Your prompt instructions within each script |
| `expected_output` | Your JSON schemas and markdown templates |
| `agent` | Which stage/script handles the work |
| `context` | Output from previous stage (e.g., `content_queue.json` → `board_decision.json`) |

**CrewAI Task Definition Example:**
```python
from crewai import Task

research_task = Task(
    description='Research the topic "{topic}" gathering at least 5 verified data points',
    expected_output='JSON with data_points array, each containing source, fact, and verification_status',
    agent=research_agent,
    output_file='output/research_output.json'
)
```

### Crews
**Definition**: A collection of agents and tasks working together with a defined process type.

| Process Type | Description | Your Use Case |
|-------------|-------------|---------------|
| `sequential` | Tasks run one after another | Your 3-stage pipeline (Scout → Board → Generate) |
| `hierarchical` | Manager agent delegates to worker agents | Could apply to your editorial board voting |
| `parallel` | Tasks run simultaneously | 6 personas voting simultaneously |

---

## 2. Flows vs Crews: Which Fits Your Pipeline?

### Your Current Architecture
```
Stage 1: topic_scout.py    → content_queue.json
Stage 2: editorial_board.py → board_decision.json
Stage 3: economist_agent.py → Markdown + PNG
```

### Recommendation: **Flows Orchestrating Crews**

Your pipeline is a textbook case for the "High Complexity + High Precision" quadrant:
- You need **deterministic stage progression** (Flow)
- You need **collaborative agent behavior** within stages (Crews)

**Optimal Architecture:**
```python
from crewai.flow.flow import Flow, listen, start, router
from crewai import Crew, Agent, Task

class EconomistContentFlow(Flow):

    @start()
    def discover_topics(self):
        # Stage 1: Topic Scout (could be single agent or small crew)
        return topic_scout_crew.kickoff()

    @listen(discover_topics)
    def editorial_review(self, topics):
        # Stage 2: 6-persona voting crew
        return editorial_board_crew.kickoff(inputs={'topics': topics})

    @listen(editorial_review)
    def generate_content(self, selected_topic):
        # Stage 3: Research → Graphics → Writer → Editor crew
        return content_generation_crew.kickoff(inputs={'topic': selected_topic})

    @router(generate_content)
    def quality_gate(self, article):
        # Route based on quality score
        if article.quality_score >= 8:
            return 'publish'
        else:
            return 'revision'
```

---

## 3. Mapping Your Scripts to CrewAI Components

### Stage 1: Topic Scout → Single Agent or Small Crew

```python
# topic_scout.py equivalent
topic_scout_agent = Agent(
    role='QE Landscape Scout',
    goal='Identify trending, underserved topics in quality engineering',
    backstory='Industry analyst tracking QE trends across enterprise and startup ecosystems',
    tools=[web_search_tool, trend_analyzer_tool]
)

topic_discovery_task = Task(
    description='Scan QE landscape for 5-10 potential blog topics with market demand signals',
    expected_output='content_queue.json with topic objects containing title, angle, demand_score',
    agent=topic_scout_agent,
    output_file='output/content_queue.json'
)
```

### Stage 2: Editorial Board → Hierarchical Crew with 6 Personas

```python
# editorial_board.py equivalent
personas = [
    Agent(role='VP of Engineering', goal='Evaluate strategic value and executive appeal', ...),
    Agent(role='Senior QE Lead', goal='Assess technical depth and practical applicability', ...),
    Agent(role='Data Skeptic', goal='Challenge claims and demand evidence', ...),
    Agent(role='Career Climber', goal='Judge career advancement relevance', ...),
    Agent(role='Economist Editor', goal='Evaluate prose quality and narrative arc', ...),
    Agent(role='Busy Reader', goal='Assess skim-ability and time-to-value', ...),
]

# Each persona gets a voting task
voting_tasks = [
    Task(
        description=f'Score topics 1-10 on {persona.goal}',
        expected_output='JSON with scores and rationale',
        agent=persona
    ) for persona in personas
]

editorial_board_crew = Crew(
    agents=personas,
    tasks=voting_tasks,
    process=Process.parallel,  # All vote simultaneously
    verbose=True
)
```

### Stage 3: Content Generation → Sequential Crew

```python
# economist_agent.py equivalent
research_agent = Agent(role='Research Agent', goal='Gather verified data', ...)
graphics_agent = Agent(role='Graphics Agent', goal='Create Economist-style charts', ...)
writer_agent = Agent(role='Writer Agent', goal='Draft article in Economist voice', ...)
editor_agent = Agent(role='Editor Agent', goal='Enforce style guide and quality gates', ...)

content_generation_crew = Crew(
    agents=[research_agent, graphics_agent, writer_agent, editor_agent],
    tasks=[research_task, graphics_task, writing_task, editing_task],
    process=Process.sequential,  # Research → Graphics → Write → Edit
    verbose=True
)
```

---

## 4. Key CrewAI Features Relevant to Your Use Case

### A. YAML Configuration (Recommended Approach)
CrewAI encourages separating agent/task definitions from code:

```yaml
# config/agents.yaml
topic_scout:
  role: QE Landscape Scout
  goal: Identify trending quality engineering topics
  backstory: Industry analyst with 15 years tracking enterprise QE

vp_engineering:
  role: VP of Engineering Persona
  goal: Evaluate strategic alignment and executive messaging
  backstory: Former CTO who values ROI-focused content
```

```yaml
# config/tasks.yaml
discover_topics:
  description: Scan QE landscape for 5-10 potential topics
  expected_output: JSON array with topic objects
  agent: topic_scout
  output_file: output/content_queue.json
```

### B. Tools Integration
Your current agents could benefit from CrewAI's tool system:

```python
from crewai_tools import SerperDevTool, FileWriterTool

web_search = SerperDevTool()  # Replaces your manual API calls
file_writer = FileWriterTool()  # Structured file output

research_agent = Agent(
    role='Research Agent',
    tools=[web_search, file_writer],
    ...
)
```

### C. Structured Outputs (Pydantic)
Enforce schema compliance—critical for your quality gates:

```python
from pydantic import BaseModel
from typing import List

class DataPoint(BaseModel):
    source: str
    fact: str
    verification_status: str

class ResearchOutput(BaseModel):
    topic: str
    data_points: List[DataPoint]
    sources_count: int

research_task = Task(
    ...,
    output_pydantic=ResearchOutput  # Guarantees schema compliance
)
```

### D. Context Chaining
Pass outputs between tasks automatically:

```python
editing_task = Task(
    description='Apply Economist style guide to the article',
    expected_output='Final polished markdown',
    agent=editor_agent,
    context=[writing_task]  # Receives writer output automatically
)
```

---

## 5. Migration Path: Current → CrewAI

### Phase 1: Minimal Viable Migration
1. Keep your existing Python scripts
2. Wrap them in CrewAI Agent/Task structure
3. Use CrewAI's `Crew.kickoff()` instead of direct function calls

### Phase 2: Add CrewAI Features
1. Replace manual API calls with CrewAI tools
2. Add Pydantic output validation
3. Implement `@listen` and `@router` for flow control

### Phase 3: Full CrewAI Architecture
1. Move to YAML configuration
2. Use CrewAI's state management
3. Add observability/tracing

---

## 6. Project Structure for CrewAI Migration

```
economist-agents/
├── src/
│   └── economist_agents/
│       ├── config/
│       │   ├── agents.yaml       # All agent definitions
│       │   └── tasks.yaml        # All task definitions
│       ├── tools/
│       │   ├── chart_generator.py   # Custom tool for Economist-style charts
│       │   └── source_verifier.py   # Custom tool for fact-checking
│       ├── crews/
│       │   ├── topic_scout_crew.py
│       │   ├── editorial_board_crew.py
│       │   └── content_generation_crew.py
│       ├── flow.py               # Main Flow orchestrating crews
│       └── main.py               # Entry point
├── output/
├── .env
└── pyproject.toml
```

---

## 7. Quick Start Commands

```bash
# Install CrewAI
pip install crewai crewai-tools

# Create new project structure
crewai create flow economist-agents-v2

# Run the flow
cd economist-agents-v2
crewai run
```

---

## 8. Key Differences: Your Code vs CrewAI

| Aspect | Your Current Approach | CrewAI Approach |
|--------|----------------------|-----------------|
| Agent definition | Prompts embedded in Python | YAML config + Agent class |
| Inter-stage communication | JSON files on disk | Context objects, state management |
| Error handling | Try/except in scripts | Built-in retry, validation |
| Observability | `generation.log` | Built-in tracing, metrics |
| Parallel execution | Not implemented | `Process.parallel` |
| Human-in-loop | `--interactive` flag | Flow router with approval steps |

---

## Summary

Your economist-agents architecture is already well-structured for a CrewAI migration. The key insight is:

1. **Use Flows** for your 3-stage pipeline (deterministic progression)
2. **Use Crews** within each stage (agent collaboration)
3. **Leverage YAML config** to keep persona definitions maintainable
4. **Add Pydantic outputs** to enforce your existing JSON schemas

The migration would formalize what you've already built while adding reliability features (retries, validation, observability) that CrewAI provides out of the box.
