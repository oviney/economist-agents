# Economist-Agents

Multi-agent content pipeline that generates Economist-style articles with verified sources.

## Architecture

- **LLM**: Claude (Anthropic) is the primary LLM. OPENAI_API_KEY only needed for DALL-E images.
- **Research**: Deterministic web search (arXiv + Google Scholar via Serper). No LLM in the research path.
- **Writing**: Claude via CrewAI (Writer, Graphics, Editor agents in `src/crews/stage3_crew.py`).
- **Quality gates**: Deterministic post-processing in `src/crews/stage4_crew.py`, then `scripts/publication_validator.py`.
- **Orchestration**: `src/economist_agents/flow.py` — CrewAI Flow with @start/@listen/@router decorators.

## Directory Structure

```
agents/skills_configs/    # Agent YAML configs (research-analyst, content-writer, etc.)
data/skills_state/        # Runtime state JSON (sprint tracker, metrics, defect tracker)
skills/*/SKILL.md         # Domain skill definitions (python-quality, testing, devops, etc.)
src/crews/                # CrewAI crew implementations (stage3, stage4)
src/economist_agents/     # Flow orchestration, adapters
src/tools/                # CrewAI tool wrappers (research_tools.py)
scripts/                  # Standalone scripts (publication_validator, citation_verifier, etc.)
```

## Code Standards

Type hints mandatory. Docstrings required. Use `orjson` not `json`.
`logger` not `print()`. Mock APIs in tests. >80% coverage required.

See `skills/python-quality/SKILL.md` for complete standards.

## Quality Gates (enforced deterministically)

1. **Stat audit** (`stage3_crew.py`): strips sentences with stats not in the research brief
2. **Category normalization** (`stage4_crew.py`): Title Case → kebab-case
3. **Description truncation** (`stage4_crew.py`): caps at 160 chars
4. **Heading limit** (`stage4_crew.py`): merges sections when >4 headings
5. **Hedging removal** (`stage4_crew.py`): strips "One suspects", "it is worth noting", etc.
6. **Ending validation** (`publication_validator.py`): flags summary endings (HIGH severity)
7. **Chart auto-embed** (`stage4_crew.py`): inserts chart before References if missing
8. **British spelling** (`stage4_crew.py`): American → British replacements
9. **Publication validator** (`publication_validator.py`): frontmatter, categories, word count, placeholders

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Yes | Claude LLM for writing/editing agents |
| `OPENAI_API_KEY` | For images | DALL-E 3 featured image generation |
| `SERPER_API_KEY` | For research | Google Web + Scholar search via Serper |

## Key Skills

- `skills/economist-writing/SKILL.md` — The 10 writing rules
- `skills/python-quality/SKILL.md` — Code standards
- `skills/defect-prevention/SKILL.md` — Pattern → rule → test cycle
- `skills/agent-delegation/SKILL.md` — Agent assignment rules
