# Skills Library

The **Skills Library** is a collection of reusable agent definitions organised into
public (generic) and private (organisation-specific) directories.

---

## Directory Structure

```
agents/skills_configs/             # Agent YAML configs (formerly skills/public, skills/private)
├── README.md
├── research-analyst.yaml          # Research Analyst — verified data briefs
├── content-writer.yaml            # Content Writer — evidence-based articles
├── data-analyst.yaml              # Data Analyst — insight summaries and chart specs
└── editor-reviewer.yaml           # Editor Reviewer — structured quality review

skills/                            # Domain skill definitions (SKILL.md files)
├── README.md                      # This file
└── <domain>/                      # e.g., python-quality, testing, devops, observability
    └── SKILL.md

data/skills_state/                 # Runtime state JSON (metrics, trackers, history)
```

---

## Public Skills Library

`agents/skills_configs/` contains **generic, domain-agnostic agent templates** that any team
can adopt without modification, or customise to their specific context.

### Available Agents

| Agent | File | Use Cases |
|-------|------|-----------|
| **Research Analyst** | `research-analyst.yaml` | Article research, market intelligence, policy briefings |
| **Content Writer** | `content-writer.yaml` | Blog posts, technical writing, newsletters |
| **Data Analyst** | `data-analyst.yaml` | Dashboard summaries, data journalism, BI reports |
| **Editor Reviewer** | `editor-reviewer.yaml` | Editorial review, documentation QA, compliance checks |

### Agent YAML Schema

All agents follow the schema defined in `agents/schema.json`.

**Required fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Human-readable agent name |
| `role` | string | Short role title |
| `goal` | string | Primary goal the agent pursues |
| `backstory` | string | Background context shaping the persona |
| `system_message` | string | Full system prompt sent to the LLM |
| `metadata.version` | string | Semantic version (e.g., `"1.0"`) |
| `metadata.created` | string | ISO 8601 creation date (`YYYY-MM-DD`) |
| `metadata.author` | string | Author or team handle |
| `metadata.category` | string | One of: `discovery`, `editorial_board`, `content_generation` |

**Additional public-library fields** (recommended):

| Field | Type | Description |
|-------|------|-------------|
| `metadata.visibility` | string | `"public"` for library agents |
| `metadata.use_cases` | list | 2–4 bullet points describing when to use this agent |
| `metadata.customisation_notes` | string | Tips for adapting the agent to a specific domain |

### Quick Start

1. **Browse** the agents in `agents/skills_configs/` and pick the one closest to your need.
2. **Copy** the YAML file into your project's agent directory.
3. **Customise** using the `customisation_notes` in the `metadata` section as a guide.
4. **Validate** the YAML against `agents/schema.json`:
   ```bash
   python3 -c "
   import yaml, json, jsonschema
   schema = json.load(open('agents/schema.json'))
   agent  = yaml.safe_load(open('agents/skills_configs/research-analyst.yaml'))
   jsonschema.validate(agent, schema)
   print('Valid')
   "
   ```
5. **Use** the agent in your CrewAI pipeline or any LLM orchestration framework.

---

## Private Skills

Organisation-specific configurations live alongside the public agents under
`agents/skills_configs/`. See [`agents/skills_configs/README.md`](../agents/skills_configs/README.md) for details.

---

## Domain Skill Directories

Other directories under `skills/` contain operational skill documents (`SKILL.md`)
that define coding standards, testing patterns, and process guidelines for this
repository's AI coding agents.

| Directory | Purpose |
|-----------|---------|
| `python-quality/` | Python coding standards and type-hint conventions |
| `testing/` | Testing patterns, coverage standards, TDD workflows |
| `devops/` | CI/CD setup, deployment, and automation standards |
| `observability/` | Dashboard schemas and alert thresholds |
| `economist-writing/` | Economist editorial style and voice guidelines |
| `research-sourcing/` | Source freshness and diversity requirements |

---

## Contributing a New Public Agent

We welcome community contributions to the public skills library. To add a new agent:

1. **Read the contribution guidelines** in [`CONTRIBUTING.md`](../CONTRIBUTING.md),
   specifically the *Contributing to the Public Skills Library* section.
2. **Fork** the repository and create a branch:
   ```bash
   git checkout -b skills/add-my-agent-name
   ```
3. **Create** your agent YAML in `agents/skills_configs/<agent-name>.yaml`.
4. **Follow the schema** — ensure all required fields are present.
5. **Add `customisation_notes`** — tell others how to adapt the agent.
6. **Open a Pull Request** with the `skills-library` label.

See [`CONTRIBUTING.md`](../CONTRIBUTING.md) for the full review checklist.

---

## Versioning

Each agent YAML carries its own `metadata.version`.  
We follow [Semantic Versioning](https://semver.org/):

- **Patch** (`1.0.1`): Typo fixes, clarifications that don't change behaviour.
- **Minor** (`1.1.0`): New optional fields, improved prompts that are backward-compatible.
- **Major** (`2.0.0`): Breaking changes to output format or required inputs.

When updating an existing public agent, increment the version and document the change
in your PR description.

---

## Roadmap

| Phase | Goal | Status |
|-------|------|--------|
| Phase 1 | Launch with 4 generic agents | ✅ Complete |
| Phase 2 | Add 4 more specialised agents (summariser, fact-checker, interview analyst, social writer) | Planned |
| Phase 3 | Skills marketplace with tagging and search | Planned |
| Phase 4 | Community-maintained agent registry | Planned |

---

## Licence

All agent YAML files in `agents/skills_configs/` are released under the project's
[MIT Licence](../LICENSE) and are free to use, modify, and redistribute.
