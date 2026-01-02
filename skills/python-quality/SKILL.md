# Python Quality Engineering Standards for Economist-Agents

## Overview
This skill defines Python coding standards for the economist-agents multi-agent AI content generation system. These standards ensure code quality, maintainability, and reliability across the 3-stage pipeline: Topic Scout → Editorial Board → Content Generation.

## Core Principles

All code you write MUST be fully optimized.

"Fully optimized" includes:
* Maximizing algorithmic big-O efficiency for memory and runtime
* Using parallelization where appropriate for multi-agent workflows
* Following proper style conventions for Python (PEP 8, type hints)
* No extra code beyond what is absolutely necessary to solve the problem
* No technical debt

If the code is not fully optimized before completion, you will be fined $100. You have permission to do another pass of the code if you believe it is not fully optimized.

## Project Context

**3-Stage Pipeline:**
1. **Topic Scout** (`scripts/topic_scout.py`): Discovers trending QE topics using LLM
2. **Editorial Board** (`scripts/editorial_board.py`): 6 persona agents vote on topics
3. **Content Generation** (`scripts/economist_agent.py`): Research → Graphics → Writing → Editing

All agents use OpenAI or Anthropic APIs. Scripts must handle API errors gracefully.

## Preferred Tools

* Use `uv` for Python package management and to create a `.venv` if not present
* Use `orjson` for JSON loading/dumping (agent outputs, governance logs)
* When reporting errors to console, use `logger.error` instead of `print`
* For chart generation:
  + Use `matplotlib` with consistent style (see `docs/CHART_DESIGN_SPEC.md`)
  + Save charts as PNG to `output/charts/`
* For API calls:
  + Use `anthropic` library for Claude
  + Use `openai` library for GPT-4
  + Implement retry logic with exponential backoff
* For data science (if needed):
  + Use `polars` instead of `pandas` for data frame manipulation
  + Never ingest more than 10 rows at a time to avoid memory issues

## Code Style and Formatting

* **MUST** use meaningful, descriptive variable and function names
* **MUST** follow PEP 8 style guidelines
* **MUST** use 4 spaces for indentation (never tabs)
* **NEVER** use emoji or unicode that emulates emoji (e.g. ✓, ✗)
* Use snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
* Limit line length to 88 characters (ruff formatter standard)

## Documentation

* **MUST** include docstrings for all agent functions and classes
* **MUST** document function parameters, return values, and exceptions raised
* Keep comments up-to-date with code changes
* Include examples in docstrings for complex agent workflows

**Example docstring for agent functions:**

```python
def invoke_agent(
    agent_name: str,
    prompt: str,
    model: str = "gpt-4o",
    max_tokens: int = 4000
) -> dict[str, Any]:
    """Invoke an LLM agent with retry logic.

    Args:
        agent_name: Name of the agent (e.g., "researcher", "writer")
        prompt: The prompt to send to the agent
        model: OpenAI or Anthropic model to use
        max_tokens: Maximum tokens in response

    Returns:
        Dictionary with 'content', 'usage', 'model' keys

    Raises:
        APIError: If API call fails after retries
        ValueError: If model is not supported

    Example:
        >>> result = invoke_agent("researcher", "Find QE trends", "gpt-4o")
        >>> print(result['content'])
    """
```

## Type Hints

* **MUST** use type hints for all function signatures
* **NEVER** use `Any` type unless absolutely necessary
* **MUST** run mypy and resolve all type errors
* Use `dict[str, Any]` for JSON-like structures (agent outputs)
* Use `Optional[T]` or `T | None` for nullable types
* Use `list[T]` instead of `List[T]` (Python 3.11+)

**Example type hints:**

```python
from typing import Any
import logging

logger = logging.getLogger(__name__)

def parse_agent_output(raw_output: str) -> dict[str, Any]:
    """Parse agent JSON output."""
    import orjson
    try:
        return orjson.loads(raw_output)
    except orjson.JSONDecodeError as e:
        logger.error(f"Failed to parse agent output: {e}")
        raise

def validate_topics(topics: list[dict[str, Any]]) -> bool:
    """Validate topic structure."""
    required_keys = {"title", "description", "score"}
    return all(required_keys.issubset(topic.keys()) for topic in topics)
```

## Error Handling

* **NEVER** silently swallow exceptions without logging
* **MUST** never use bare `except:` clauses
* **MUST** catch specific exceptions (APIError, JSONDecodeError, etc.)
* **MUST** use context managers for file operations
* Provide meaningful error messages that help debug agent failures

**Example error handling for API calls:**

```python
import logging
from openai import OpenAI, APIError
from anthropic import Anthropic, APIError as AnthropicAPIError

logger = logging.getLogger(__name__)

def call_openai_agent(client: OpenAI, prompt: str) -> dict[str, Any]:
    """Call OpenAI agent with error handling."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000
        )
        return {
            "content": response.choices[0].message.content,
            "usage": response.usage.model_dump(),
            "model": response.model
        }
    except APIError as e:
        logger.error(f"OpenAI API call failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling OpenAI: {e}")
        raise
```

## Function Design

* **MUST** keep functions focused on a single responsibility
* **NEVER** use mutable objects (lists, dicts) as default argument values
* Limit function parameters to 5 or fewer
* Return early to reduce nesting
* Extract agent prompts into module-level constants

**Example:**

```python
# Module-level constants
TOPIC_SCOUT_PROMPT = """
You are a quality engineering trend analyst.
Analyze the current QE landscape and identify 5 emerging topics.
Return JSON with this schema:
{
  "topics": [
    {"title": "...", "description": "...", "relevance_score": 0-10}
  ]
}
"""

EDITORIAL_BOARD_PERSONAS = {
    "practitioner": "Senior QE practitioner with 15+ years experience...",
    "consultant": "QE consultant focusing on enterprise transformations...",
    # ... other personas
}

def discover_topics(client: OpenAI) -> dict[str, Any]:
    """Discover trending QE topics using LLM."""
    return call_openai_agent(client, TOPIC_SCOUT_PROMPT)
```

## Testing

* **MUST** write unit tests for all new functions and classes
* **MUST** mock API calls (OpenAI, Anthropic) in tests
* **MUST** use pytest as the testing framework
* **NEVER** run tests without first saving them to `tests/`
* **NEVER** delete test files after running
* Ensure `tests/outputs/` is present in `.gitignore`
* Follow Arrange-Act-Assert pattern

**Example test structure:**

```python
# tests/test_topic_scout.py
import pytest
from unittest.mock import Mock, patch
import orjson
from scripts.topic_scout import discover_topics

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    with patch('scripts.topic_scout.OpenAI') as mock:
        mock_instance = Mock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content='{"topics": []}'))
        ]
        mock_response.usage = Mock(total_tokens=100)
        mock_response.model = "gpt-4o"
        mock_instance.chat.completions.create.return_value = mock_response
        mock.return_value = mock_instance
        yield mock_instance

def test_discover_topics_returns_valid_json(mock_openai_client):
    """Test that discover_topics returns valid JSON structure."""
    # Arrange
    expected_keys = {"topics"}

    # Act
    result = discover_topics(client=mock_openai_client)

    # Assert
    assert isinstance(result, dict)
    assert expected_keys.issubset(result.keys())
    assert isinstance(result["topics"], list)

def test_discover_topics_handles_api_error(mock_openai_client, caplog):
    """Test that API errors are logged and re-raised."""
    # Arrange
    from openai import APIError
    mock_openai_client.chat.completions.create.side_effect = APIError("API down")

    # Act & Assert
    with pytest.raises(APIError):
        discover_topics(client=mock_openai_client)

    assert "OpenAI API call failed" in caplog.text
```

## Imports and Dependencies

* **MUST** avoid wildcard imports (`from module import *`)
* **MUST** document dependencies in `requirements.txt`
* Use `uv` for fast package management
* Organize imports: standard library, third-party, local imports
* Use `isort` to automate import formatting

**Example import structure:**

```python
# Standard library
import logging
import os
from pathlib import Path
from typing import Any

# Third-party
import orjson
from openai import OpenAI, APIError
from anthropic import Anthropic

# Local
from scripts.validation import validate_agent_output

logger = logging.getLogger(__name__)
```

## Python Best Practices

* **NEVER** use mutable default arguments
* **MUST** use context managers (`with` statement) for file/resource management
* **MUST** use `is` for comparing with `None`, `True`, `False`
* **MUST** use f-strings for string formatting
* Use list comprehensions and generator expressions
* Use `enumerate()` instead of manual counter variables

**Example:**

```python
# Good - context manager for file operations
def save_agent_output(output: dict[str, Any], filepath: Path) -> None:
    """Save agent output to JSON file."""
    with open(filepath, "wb") as f:
        f.write(orjson.dumps(output, option=orjson.OPT_INDENT_2))

# Bad - mutable default argument
def process_topics(topics: list = []):  # WRONG
    topics.append(...)

# Good - immutable default
def process_topics(topics: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Process topics with proper default handling."""
    if topics is None:
        topics = []
    # ... process
    return topics
```

## Security

* **NEVER** store API keys in code. Only store them in `.env`
  + Ensure `.env` is declared in `.gitignore`
  + **NEVER** print or log URLs to console if they contain an API key
* **MUST** use environment variables for sensitive configuration (OPENAI_API_KEY, ANTHROPIC_API_KEY)
* **NEVER** log sensitive information (API responses with PII, API keys)
* **NEVER** commit credentials or sensitive data

**Example:**

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Good
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

# Bad - never do this
# api_key = "sk-proj-..."
# print(f"Using API key: {api_key}")
```

## Version Control

* **MUST** write clear, descriptive commit messages
* **NEVER** commit commented-out code; delete it
* **NEVER** commit debug print statements or breakpoints
* **NEVER** commit credentials or sensitive data
* **NEVER** commit generated content (markdown, charts) to this repo
  + Use separate blog repo for final outputs

## Tools

* **MUST** use Ruff for code formatting and linting
* **MUST** use mypy for static type checking
* Use `uv` for package management
* Use pytest for testing

## Agent-Specific Guidelines

### Topic Scout (`scripts/topic_scout.py`)
* Return JSON with schema validation
* Handle empty results gracefully
* Log discovered topics count
* Extract prompt to TOPIC_SCOUT_PROMPT constant
* Validate response structure before returning

**Example structure:**

```python
TOPIC_SCOUT_PROMPT = """..."""

def discover_topics(client: OpenAI) -> dict[str, Any]:
    """Discover trending topics."""
    raw_response = call_openai_agent(client, TOPIC_SCOUT_PROMPT)
    validated = validate_topics_schema(raw_response)
    logger.info(f"Discovered {len(validated['topics'])} topics")
    return validated
```

### Editorial Board (`scripts/editorial_board.py`)
* Ensure 6 persona agents vote independently
* Aggregate scores correctly (weighted voting)
* Save board decision to `output/governance/board_decision.json`
* Extract persona prompts to PERSONA_PROMPTS constant dict
* Validate vote ranges (0-10)

**Example structure:**

```python
PERSONA_PROMPTS = {
    "practitioner": "You are a senior QE practitioner...",
    "consultant": "You are a QE consultant...",
    # ... 6 personas total
}

def collect_votes(
    client: OpenAI,
    topic: dict[str, Any]
) -> dict[str, int]:
    """Collect votes from all 6 personas."""
    votes = {}
    for persona_name, persona_prompt in PERSONA_PROMPTS.items():
        vote = invoke_persona(client, persona_name, persona_prompt, topic)
        votes[persona_name] = validate_vote_score(vote)
    return votes

def aggregate_scores(votes: dict[str, int]) -> float:
    """Aggregate persona votes with weighting."""
    weights = {"practitioner": 2.0, "consultant": 1.5, ...}
    weighted_sum = sum(votes[p] * weights.get(p, 1.0) for p in votes)
    total_weight = sum(weights.get(p, 1.0) for p in votes)
    return weighted_sum / total_weight
```

### Economist Agent (`scripts/economist_agent.py`)
* Implement governance checkpoints if `--interactive` flag
* Save all agent outputs as JSON to `output/governance/SESSION_ID/`
* Generate governance report summarizing session
* Extract stage prompts to constants
* Handle errors at each stage gracefully

**Example structure:**

```python
RESEARCH_PROMPT = """You are a research agent..."""
WRITER_PROMPT = """You are a writer agent..."""
EDITOR_PROMPT = """You are an editor agent..."""

def run_research_stage(
    client: OpenAI,
    topic: dict[str, Any],
    session_dir: Path
) -> dict[str, Any]:
    """Run research stage with governance."""
    research_output = call_openai_agent(client, RESEARCH_PROMPT)

    # Save to governance
    save_agent_output(
        research_output,
        session_dir / "research_agent.json"
    )

    return research_output

def generate_article(
    topic: dict[str, Any],
    interactive: bool = False
) -> Path:
    """Generate article through 4-stage pipeline."""
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = Path(f"output/governance/{session_id}")
    session_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: Research
    research = run_research_stage(client, topic, session_dir)
    if interactive and not approve_stage("research"):
        return None

    # Stage 2-4: Graphics, Writing, Editing
    # ... similar pattern

    return article_path
```

### Chart Generator (`scripts/generate_chart.py`)
* Follow `docs/CHART_DESIGN_SPEC.md` style guide
* Validate data before plotting
* Save charts with descriptive filenames
* Handle matplotlib errors gracefully

## Before Committing

* All tests pass (`pytest`)
* Type checking passes (`mypy scripts/`)
* Code formatter and linter pass (`ruff check . && ruff format .`)
* All functions have docstrings and type hints
* No commented-out code or debug statements
* No hardcoded credentials
* Agent outputs validated (JSON structure, schema)

**Quality check commands:**

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type check
mypy scripts/

# Run tests
pytest tests/ -v --cov=scripts --cov-report=term-missing

# All-in-one
make quality
```

---

**Remember:** Prioritize clarity and maintainability over cleverness. Multi-agent systems are complex enough without clever code.
