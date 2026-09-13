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

## Spec-First TDD (Test-Driven Development)

**CRITICAL**: All new scripts MUST follow spec-first TDD workflow.

### Workflow

1. **Write Specification First**
   ```python
   """
   Module: github_project_tool.py
   
   Purpose: Interact with GitHub Projects API v2
   
   Functions:
   - list_project_items(project_id: str) -> list[dict]
     Returns all items in a project
   
   - add_item_to_project(project_id: str, issue_url: str) -> dict
     Adds GitHub issue to project board
   
   - update_item_status(item_id: str, status: str) -> dict
     Updates item status (Todo, In Progress, Done)
   """
   ```

2. **Write Tests (Before Implementation)**
   ```python
   def test_list_project_items():
       """Test listing project items."""
       mock_client = Mock()
       mock_client.graphql.return_value = {"data": {"items": []}}
       
       result = list_project_items(mock_client, "PROJECT_123")
       assert result == []
       mock_client.graphql.assert_called_once()
   ```

3. **Implement to Pass Tests**
   ```python
   def list_project_items(client, project_id: str) -> list[dict]:
       """List all items in GitHub project."""
       query = """
       query($projectId: ID!) {
           node(id: $projectId) {
               ... on ProjectV2 {
                   items(first: 100) { nodes { id } }
               }
           }
       }
       """
       response = client.graphql(query, variables={"projectId": project_id})
       return response.get("data", {}).get("items", [])
   ```

4. **Validate with pytest**
   ```bash
   pytest tests/test_github_project_tool.py -v
   ```

### Benefits

- ✅ Forces clear design before coding
- ✅ Prevents scope creep (spec is contract)
- ✅ Tests catch regressions immediately
- ✅ Documentation generated from spec
- ✅ Parallel development (spec enables team work)

### When to Skip TDD

**Never skip for:**
- API integrations (GitHub, Anthropic, etc.)
- Data transformations (JSON, CSV parsing)
- Agent orchestration logic

**Can skip for:**
- One-time scripts (< 50 lines)
- Exploratory prototypes (mark as experimental)

## Custom Copilot Agents

Use specialized agents for this codebase:
- `@quality-enforcer` - Fix ruff/mypy violations
- `@test-writer` - Create tests with >80% coverage
- `@refactor-specialist` - Add type hints and docstrings
