# ADR-002: Implement Agent Registry Pattern

**Status:** Proposed
**Date:** 2026-01-01
**Deciders:** Ouray Viney (Agentic AI Architect)
**Dependencies:** ADR-001 (Agent Configuration Extraction)

## Context

After extracting agent definitions to YAML (ADR-001), we need a systematic way to:

1. **Discover agents:** List available agents by category/capability
2. **Instantiate agents:** Create agent instances with proper dependencies
3. **Swap providers:** Use different LLM providers (OpenAI, Anthropic) per agent
4. **Test agents:** Inject mock agents for unit testing
5. **Version agents:** Load specific agent versions

Currently, each script directly instantiates agents with hardcoded provider logic. This creates coupling and makes testing difficult.

## Decision

We will implement an **Agent Registry** using the Factory and Repository patterns:

```python
# scripts/agent_registry.py

from pathlib import Path
from typing import Dict, List, Optional, Protocol
import yaml
from dataclasses import dataclass

@dataclass
class AgentConfig:
    """Loaded agent configuration"""
    name: str
    role: str
    goal: str
    backstory: str
    system_message: str
    tools: List[str]
    metadata: Dict[str, str]
    scoring_criteria: Optional[Dict[str, str]] = None

class LLMProvider(Protocol):
    """Interface for LLM providers"""
    def create_client(self, model: str):
        ...

class AgentRegistry:
    """Central registry for agent discovery and creation"""

    def __init__(self, config_dir: Path, llm_factory: LLMProvider):
        self.config_dir = config_dir
        self.llm_factory = llm_factory
        self._agents: Dict[str, AgentConfig] = {}
        self._load_agents()

    def _load_agents(self):
        """Load all YAML files from config directory"""
        for yaml_file in self.config_dir.rglob("*.yaml"):
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
                agent_config = AgentConfig(**config)
                self._agents[agent_config.name] = agent_config

    def get_agent(self, name: str, model: str = "gpt-4o") -> Agent:
        """Factory method: Create agent instance"""
        if name not in self._agents:
            raise ValueError(f"Agent '{name}' not found in registry")

        config = self._agents[name]
        llm_client = self.llm_factory.create_client(model)

        return Agent(
            role=config.role,
            goal=config.goal,
            backstory=config.backstory,
            system_message=config.system_message,
            llm_client=llm_client,
            tools=self._load_tools(config.tools)
        )

    def list_agents(self, category: str = None) -> List[str]:
        """Discover available agents"""
        if category:
            return [
                name for name, cfg in self._agents.items()
                if cfg.metadata.get('category') == category
            ]
        return list(self._agents.keys())

    def get_config(self, name: str) -> AgentConfig:
        """Get raw configuration for inspection/testing"""
        return self._agents[name]

    def _load_tools(self, tool_names: List[str]) -> List[Tool]:
        """Load tool instances by name"""
        # Implementation depends on MCP integration (ADR-004)
        return []

# Usage in scripts
registry = AgentRegistry(
    config_dir=Path("agents/"),
    llm_factory=OpenAIProvider()
)

# Get specific agent
vp_eng = registry.get_agent("vp_engineering", model="gpt-4o")

# List agents by category
board_agents = [
    registry.get_agent(name)
    for name in registry.list_agents(category="editorial_board")
]
```

## Architecture

```
┌─────────────────────────────────────────────┐
│           AgentRegistry                      │
│  ┌────────────────────────────────────────┐ │
│  │  Discovery Layer                       │ │
│  │  - List agents by category             │ │
│  │  - Search by capability                │ │
│  │  - Version resolution                  │ │
│  └────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────┐ │
│  │  Factory Layer                         │ │
│  │  - Create agent instances              │ │
│  │  - Inject LLM clients                  │ │
│  │  - Load tools                          │ │
│  └────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────┐ │
│  │  Configuration Layer                   │ │
│  │  - Parse YAML files                    │ │
│  │  - Validate schemas                    │ │
│  │  - Cache loaded configs                │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

## Consequences

### Positive

1. **Dependency Injection:** Easy to test with mock agents
2. **Provider Abstraction:** Swap OpenAI ↔ Anthropic per agent
3. **Discovery:** Programmatically list available agents
4. **Single Responsibility:** Agent creation logic in one place
5. **Lazy Loading:** Only load agents when needed
6. **Type Safety:** Strong typing with `AgentConfig` dataclass

### Negative

1. **Abstraction Overhead:** Extra layer between config and usage
2. **Learning Curve:** Team needs to understand registry pattern
3. **Debugging Complexity:** One more place to look when things fail

### Neutral

1. **Testability:** Much easier to unit test with registry
2. **Caching:** Can add caching later if performance becomes issue

## Implementation Plan

### Week 1: Core Registry
- [ ] Create `scripts/agent_registry.py` with base class
- [ ] Implement `_load_agents()` and `get_agent()`
- [ ] Add unit tests with fixture YAML files
- [ ] Document usage in docstrings

### Week 2: Provider Abstraction
- [ ] Create `LLMProvider` protocol
- [ ] Implement `OpenAIProvider` and `AnthropicProvider`
- [ ] Add provider selection logic
- [ ] Test provider swapping

### Week 3: Integration
- [ ] Refactor `editorial_board.py` to use registry
- [ ] Refactor `economist_agent.py` to use registry
- [ ] Update all scripts to use registry
- [ ] Remove old agent instantiation code

### Week 4: Advanced Features
- [ ] Add `list_agents()` with category filtering
- [ ] Add agent version resolution (if YAML has version field)
- [ ] Add registry configuration validation
- [ ] Performance testing with all agents

## Testing Strategy

```python
# tests/test_agent_registry.py

def test_load_agents_from_yaml(tmp_path):
    """Registry loads all YAML files"""
    (tmp_path / "test_agent.yaml").write_text("""
    name: test_agent
    role: Tester
    goal: Test things
    backstory: I test
    system_message: You are a test
    tools: []
    metadata:
      category: testing
    """)

    registry = AgentRegistry(tmp_path, MockLLMProvider())
    assert "test_agent" in registry.list_agents()

def test_get_agent_creates_instance(mock_llm_factory):
    """Factory method creates proper agent instance"""
    registry = AgentRegistry(Path("agents/"), mock_llm_factory)
    agent = registry.get_agent("vp_engineering")

    assert agent.role == "VP of Engineering perspective on QE"
    assert agent.llm_client is not None

def test_list_agents_filters_by_category():
    """Can filter agents by category"""
    registry = AgentRegistry(Path("agents/"), MockLLMProvider())
    board_agents = registry.list_agents(category="editorial_board")

    assert len(board_agents) == 6
    assert "vp_engineering" in board_agents
```

## Alternatives Considered

### 1. Global Singleton Registry
**Pros:** Simple access from anywhere
**Cons:** Hard to test, hidden dependencies
**Verdict:** Rejected - prefer explicit dependency injection

### 2. Service Locator Pattern
**Pros:** Widely known pattern
**Cons:** Anti-pattern in modern Python, hard to test
**Verdict:** Rejected - dependency injection clearer

### 3. Direct YAML Loading in Each Script
**Pros:** Simple, no abstraction
**Cons:** Duplicate loading logic, no discovery, hard to test
**Verdict:** Rejected - doesn't solve core problems

### 4. Use CrewAI's Built-in Agent Loading
**Pros:** Framework-native approach
**Cons:** Framework lock-in before we're ready
**Verdict:** Deferred - keep option open for ADR-003

## Success Metrics

- [ ] All scripts migrated to use registry
- [ ] Zero direct agent instantiation in scripts (except registry)
- [ ] 100% unit test coverage of registry
- [ ] Can swap LLM provider with 1-line config change
- [ ] Agent loading time < 50ms per agent
- [ ] Zero YAML parsing errors in production

## Migration Path

### Before (Current State)
```python
# scripts/editorial_board.py
vp_eng_prompt = """You are VP of Engineering..."""
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
vp_eng_response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "system", "content": vp_eng_prompt}, ...]
)
```

### After (With Registry)
```python
# scripts/editorial_board.py
registry = AgentRegistry(Path("agents/"), OpenAIProvider())
vp_eng = registry.get_agent("vp_engineering", model="gpt-4o")
vp_eng_response = vp_eng.respond(topic_data)
```

## References

- Factory Pattern: https://refactoring.guru/design-patterns/factory-method
- Repository Pattern: https://martinfowler.com/eaaCatalog/repository.html
- Dependency Injection in Python: https://python-dependency-injector.ets-labs.org/
- Related ADRs: ADR-001, ADR-003, ADR-004

## Notes

The registry should be framework-agnostic. If we migrate to CrewAI (ADR-003), the registry can wrap CrewAI's agent creation while maintaining our API surface.
