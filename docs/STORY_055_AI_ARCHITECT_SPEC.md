# Spec: STORY-055 AI Architect Agent

## Objective
Add an AI Architect agent that can design, review, and validate multi-agent systems using documented patterns rather than ad hoc invention. The user is the development team maintaining economist-agents. Success means the agent is discoverable through the existing `.github/agents/*.agent.md` registry and its prompt explicitly covers architecture design, agent configuration review, workflow bottleneck analysis, trade-off recommendations, compliance scoring, security, performance, and reusable ADR-style documentation.

## Tech Stack
- Python 3.13
- Markdown agent definitions in `.github/agents/*.agent.md`
- `scripts.agent_registry.AgentRegistry` for discovery
- Pytest for behavioral verification

## Commands
- Test targeted: `.venv/bin/pytest tests/test_ai_architect_agent.py -q`
- Test registry: `.venv/bin/pytest tests/test_agent_registry_enhancement.py tests/test_llm_providers.py::TestAgentRegistryCoveragePaths -q`
- Lint targeted: `.venv/bin/ruff check .github/agents/architect.agent.md tests/test_ai_architect_agent.py scripts/agent_registry.py`

## Project Structure
- `.github/agents/architect.agent.md` - AI Architect agent definition
- `skills/agent-architecture/SKILL.md` - reusable architecture review patterns
- `tests/test_ai_architect_agent.py` - story acceptance tests
- `scripts/agent_registry.py` - registry metadata support if needed
- `data/skills_state/backlog.json` - STORY-055 status after verification

## Code Style
Tests should assert externally visible behavior and prompt requirements, not private implementation details:

```python
def test_architect_agent_is_discoverable() -> None:
    registry = AgentRegistry()
    config = registry.get_agent_config("architect")
    assert config.role == "Agentic AI Architect"
```

## Testing Strategy
Use focused pytest tests that fail before the agent exists. The tests cover registry discovery, required prompt content, frontmatter configuration, and referenced skill files. Full-suite execution is not required for this scoped agent-definition change, but targeted registry tests must pass.

## Boundaries
- Always: keep the agent registry pattern, cite current ADR-0006 Agent SDK architecture, and avoid live API calls in tests.
- Ask first: changing production orchestration, adding dependencies, or reintroducing CrewAI runtime code.
- Never: commit secrets, weaken existing agent registry validation, or remove existing agents.

## Success Criteria
- `architect` is listed by `AgentRegistry`.
- `AgentRegistry.get_agent_config("architect")` exposes role, goal, backstory, system message, tools, skills, reasoning flag, and knowledge sources.
- The prompt requires C4 or Mermaid diagrams, ADR-format decisions, CrewAI/AutoGen/Agent SDK pattern references, bottleneck analysis, trade-off recommendations, security review, performance review, and compliance score target above 85%.
- Referenced skills and knowledge-source files exist.
- Targeted tests and lint pass.

## Open Questions
- None blocking. The current production architecture is Agent SDK + MCP per ADR-0006, so CrewAI and AutoGen are reference patterns rather than runtime dependencies.
