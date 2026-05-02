# Economist-Agents

Multi-agent content pipeline that generates Economist-style articles with verified sources.

## Default Operating Mode

Every task follows the `skills/using-agent-skills` discovery flowchart before any code is written:

```
Task arrives
  ├── Vague idea?              → skills/idea-refine (clarify first)
  ├── New feature/change?      → skills/spec-driven-development (spec → human review → plan → human review → implement)
  ├── Have a spec, need tasks? → skills/planning-and-task-breakdown (dependency graph → human review)
  ├── Implementing?            → skills/incremental-implementation (thin slices, each tested + committed)
  ├── Deploying?               → skills/shipping-and-launch (pre-launch checklist, staged rollout)
  └── Bug / defect?            → log in defect_tracker → spec → fix → regression test
```

**No implementation starts without a spec. No sprint planning starts without a dependency-ordered task list.**
Both require human review (a "LGTM") before proceeding.

## Architecture

- **LLM**: Claude (Anthropic) is the primary LLM. OPENAI_API_KEY only needed for DALL-E images.
- **Research**: Deterministic web search (arXiv + Google Scholar via Serper). No LLM in the research path.
- **Writing**: Claude via Anthropic Agent SDK (`src/agent_sdk/stage3_runner.py`).
- **Quality gates**: Deterministic post-processing in `src/agent_sdk/stage4_runner.py`, then `scripts/publication_validator.py`.
- **Orchestration**: `src/economist_agents/flow.py` — sequential pipeline over `src.agent_sdk.pipeline.run_pipeline`.

## Directory Structure

```
agents/skills_configs/    # Agent YAML configs (research-analyst, content-writer, etc.)
data/skills_state/        # Runtime state JSON (sprint tracker, metrics, defect tracker)
skills/*/SKILL.md         # Domain skill definitions (24 skills — see Key Skills below)
src/agent_sdk/            # Anthropic Agent SDK runners (stage3, stage4, pipeline, _shared)
src/economist_agents/     # Flow orchestration, adapters
scripts/                  # Standalone scripts (publication_validator, citation_verifier, etc.)
```

## Code Standards

Type hints mandatory. Docstrings required. Use `orjson` not `json`.
`logger` not `print()`. Mock APIs in tests. >80% coverage required.

See `skills/python-quality/SKILL.md` for complete standards.

## Quality Gates (enforced deterministically)

1. **Stat audit** (`_shared.py`): strips sentences with stats not in the research brief
2. **Category normalization** (`_shared.py`): normalises to Title Case
3. **Description truncation** (`_shared.py`): caps at 160 chars
4. **Heading limit** (`_shared.py`): merges sections when >4 headings
5. **Hedging removal** (`_shared.py`): strips "One suspects", "it is worth noting", etc.
6. **Ending validation** (`publication_validator.py`): flags summary endings (HIGH severity)
7. **Chart auto-embed** (`_shared.py`): inserts chart before References if missing
8. **British spelling** (`_shared.py`): American → British replacements
9. **Publication validator** (`publication_validator.py`): frontmatter, categories, word count, author, image metadata, placeholders

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Yes | Claude LLM for writing/editing agents |
| `OPENAI_API_KEY` | For images | DALL-E 3 featured image generation |
| `SERPER_API_KEY` | For research | Google Web + Scholar search via Serper |

## Key Skills

### Workflow (addyosmani/agent-skills — governs all work)
- `skills/using-agent-skills/SKILL.md` — Meta-skill: maps task type to the right skill
- `skills/idea-refine/SKILL.md` — Clarify vague requests before speccing
- `skills/spec-driven-development/SKILL.md` — Spec → human review → plan → human review → implement
- `skills/planning-and-task-breakdown/SKILL.md` — Dependency graph before sprint planning
- `skills/incremental-implementation/SKILL.md` — Thin slices, each tested and committed
- `skills/shipping-and-launch/SKILL.md` — Pre-launch checklist, staged rollout, rollback

### Domain
- `skills/economist-writing/SKILL.md` — The 10 writing rules
- `skills/python-quality/SKILL.md` — Code standards
- `skills/defect-prevention/SKILL.md` — Pattern → rule → test cycle
- `skills/agent-delegation/SKILL.md` — Agent assignment rules
- `skills/architecture-patterns/SKILL.md` — CrewAI/AutoGen patterns, audit rubric
