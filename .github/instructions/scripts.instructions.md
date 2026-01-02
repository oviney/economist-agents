---
applyTo: "scripts/**/*.py"
---

# Python Agent Scripts

Working on AI agent implementation scripts in the economist-agents system.

See `skills/python-quality/SKILL.md` for complete Python standards.

## Key Requirements

### Type Hints (Mandatory)
All functions must have type hints:
```python
def run_research_agent(client: Client, topic: str, talking_points: str = "") -> dict:
    """Research agent with comprehensive type hints."""
    pass
```

### Docstrings (Google Style)
```python
def generate_economist_post(topic: str, category: str = "quality-engineering") -> dict:
    """Generate Economist-style blog post.
    
    Args:
        topic: Article topic
        category: Content category (default: "quality-engineering")
        
    Returns:
        Dictionary with article_path, chart_path, metrics
        
    Raises:
        ValueError: If topic is invalid
        APIError: If LLM API call fails
    """
```

### JSON Handling
Use `orjson` instead of `json`:
```python
import orjson

# Writing
with open("data.json", "wb") as f:
    f.write(orjson.dumps(data))

# Reading
with open("data.json", "rb") as f:
    data = orjson.loads(f.read())
```

### Error Handling
Use specific exceptions for API calls:
```python
from anthropic import APIError, RateLimitError

try:
    response = client.messages.create(...)
except RateLimitError:
    logger.error("Rate limit exceeded, retrying...")
    time.sleep(60)
except APIError as e:
    logger.error(f"API error: {e}")
    raise
```

### Logging vs Print
Use structured logging:
```python
import logging
logger = logging.getLogger(__name__)

# ❌ Don't use print for errors
print(f"Error: {e}")

# ✅ Use logger
logger.error(f"Failed to process: {e}")
logger.info(f"Generated article: {path}")
```

### Prompt Constants
Extract prompts to module-level constants:
```python
RESEARCH_AGENT_PROMPT = """You are a Research Analyst...
CRITICAL RULES:
1. Every statistic MUST have a named source
2. Flag unverifiable claims as [UNVERIFIED]
"""

def run_research_agent(client, topic):
    response = call_llm(client, RESEARCH_AGENT_PROMPT, topic)
```

### Testing
Mock all external APIs:
```python
from unittest.mock import Mock, patch

def test_research_agent():
    mock_client = Mock()
    mock_client.messages.create.return_value = Mock(
        content=[Mock(text='{"data": "test"}')]
    )
    
    result = run_research_agent(mock_client, "Testing")
    assert result["data"] == "test"
```

## Custom Copilot Agents

Use specialized agents for this codebase:
- `@quality-enforcer` - Fix ruff/mypy violations
- `@test-writer` - Create tests with >80% coverage
- `@refactor-specialist` - Add type hints and docstrings
