# Agent Configurations

This directory contains YAML configuration files for all agents in the economist-agents pipeline.

## Directory Structure

```
agents/
├── schema.json                    # JSON Schema (draft-07) for validating YAML files
├── README.md                      # This file
├── discovery/
│   └── topic_scout.yaml           # Topic Scout agent (Stage 1)
├── editorial_board/
│   ├── vp_engineering.yaml        # VP of Engineering persona (weight: 1.2)
│   ├── senior_qe_lead.yaml        # Senior QE Lead persona (weight: 1.0)
│   ├── data_skeptic.yaml          # Data Skeptic persona (weight: 1.1)
│   ├── career_climber.yaml        # Career Climber persona (weight: 0.8)
│   ├── economist_editor.yaml      # Economist Editor persona (weight: 1.3)
│   └── busy_reader.yaml           # Busy Reader persona (weight: 0.9)
└── content_generation/
    ├── researcher.yaml            # Research Analyst agent
    ├── writer.yaml                # Senior Writer agent
    ├── editor.yaml                # Chief Editor agent
    └── graphics.yaml              # Data Visualization Specialist agent
```

## YAML Schema

Every agent YAML file must conform to `agents/schema.json` (JSON Schema draft-07).

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Human-readable agent name |
| `role` | string | Short role title |
| `goal` | string | Primary goal the agent pursues |
| `backstory` | string | Background context shaping the persona |
| `system_message` | string | Full system prompt sent to the LLM |
| `metadata` | object | See sub-fields below |

### metadata sub-fields (all required)

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Semantic version of the config |
| `created` | string | ISO 8601 creation date (YYYY-MM-DD) |
| `author` | string | Owner/team |
| `category` | string | One of: `discovery`, `editorial_board`, `content_generation` |

### Optional fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tools` | array of strings | `[]` | Tool names available to the agent |
| `weight` | number | `1.0` | Voting weight (editorial board only) |
| `trend_system_message` | string | — | Secondary prompt (topic_scout only) |

## Example YAML

```yaml
name: "My Agent"
role: "Content Specialist"
goal: "Produce high-quality Economist-style content"
backstory: |
  A specialist who understands the Economist voice and applies rigorous standards.
system_message: |
  You are a content specialist. Your task is to {task}.
  Follow Economist style: British spelling, active voice, no listicles.
tools:
  - bash
  - file_search
metadata:
  version: "1.0"
  created: "2026-01-01"
  author: "your-github-username"
  category: "content_generation"
```

## Python Format Placeholders

Prompts may contain Python `.format()` placeholders such as:
- `{current_date}` — injected at runtime with today's date
- `{research_brief}` — injected with the research JSON
- `{draft}` — injected with the article draft (editor agent)
- `{chart_spec}` — injected with chart specification JSON

In YAML block scalars (`|`), curly braces **do not** need escaping.

## How the Agent Loader Works

`scripts/agent_loader.py` provides these functions:

```python
from agent_loader import load_agent, load_board_members, load_scout_prompts, load_content_agent

# Load any single agent YAML
config = load_agent("agents/content_generation/researcher.yaml")
print(config.system_message)   # Full prompt string
print(config.weight)           # 1.0 (default)

# Backward-compatible BOARD_MEMBERS dict
BOARD_MEMBERS = load_board_members()
# Returns: {"vp_engineering": {"name": ..., "weight": ..., "prompt": ...}, ...}

# Backward-compatible scout prompts
prompts = load_scout_prompts()
SCOUT_AGENT_PROMPT = prompts["scout"]
TREND_RESEARCH_PROMPT = prompts["trend"]

# Load a content-generation agent by name
config = load_content_agent("researcher")  # or writer, editor, graphics
```

Schema validation runs automatically when `jsonschema` is installed. If it is
absent, a warning is logged and loading continues (soft dependency).

## Adding a New Agent

1. Choose the correct category directory (`discovery`, `editorial_board`, or `content_generation`).
2. Create a new `<agent-name>.yaml` file using the schema above.
3. Validate it: `python scripts/agent_loader.py --validate`
4. Wire it into Python code using `load_agent()` or `load_content_agent()`.
5. Add a test to `tests/test_agent_loader.py`.

## Validation

The pre-commit hook `validate-agent-yaml` runs automatically on changes to any
`agents/**/*.yaml` file:

```bash
# Run manually
python scripts/agent_loader.py --validate

# Run via pre-commit
pre-commit run validate-agent-yaml --all-files
```
