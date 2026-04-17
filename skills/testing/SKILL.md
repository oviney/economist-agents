---
name: testing
description: Testing patterns for the economist-agents multi-agent system. Use when writing tests for agent code, when mocking API calls, when setting up test fixtures, when debugging coverage gaps.
---

# Testing

## Overview

All agent code must be testable. Mock all external API calls (OpenAI, Anthropic), test both success and failure paths, validate agent outputs against schemas, and maintain ≥80% coverage.

## When to Use

- Writing tests for any new or modified code
- Mocking LLM API calls in test fixtures
- Setting up shared fixtures in conftest.py
- Investigating coverage gaps or flaky tests

### When NOT to Use

- For Python coding standards — that's `python-quality`
- For CI/CD test pipeline configuration — that's `quality-gates`
- For article content quality checks — that's `article-evaluation`

## Core Process

### Test Structure (Arrange-Act-Assert)

```python
def test_function_name():
    # Arrange — set up test data and mocks
    mock_client = Mock()
    expected = {"key": "value"}

    # Act — call the function under test
    result = function_under_test(mock_client)

    # Assert — verify the results
    assert result == expected
```

### Mocking LLM APIs

**OpenAI:**
```python
@pytest.fixture
def mock_openai_client():
    with patch('openai.OpenAI') as mock:
        instance = Mock()
        response = Mock()
        response.choices = [Mock(message=Mock(content='{"result": "success"}'))]
        response.usage = Mock(total_tokens=100)
        response.model = "gpt-4o"
        instance.chat.completions.create.return_value = response
        mock.return_value = instance
        yield instance
```

**Anthropic:**
```python
@pytest.fixture
def mock_anthropic_client():
    with patch('anthropic.Anthropic') as mock:
        instance = Mock()
        response = Mock()
        response.content = [Mock(text='{"result": "success"}')]
        response.usage = Mock(input_tokens=100, output_tokens=50)
        instance.messages.create.return_value = response
        mock.return_value = instance
        yield instance
```

**Error handling:**
```python
def test_api_error_handling(mock_openai_client, caplog):
    mock_openai_client.chat.completions.create.side_effect = APIError("Rate limit")
    with pytest.raises(APIError):
        my_function(mock_openai_client)
    assert "API call failed" in caplog.text
```

### Test Categories (Minimum Per Module)

1. **Happy path** — function returns expected result on valid input
2. **Error handling** — function handles API errors, bad input gracefully
3. **Edge cases** — empty input, missing fields, malformed data
4. **Schema validation** — agent outputs match expected structure

### File and Environment Testing

```python
# Use tmp_path for file operations
def test_save_output(tmp_path):
    path = tmp_path / "output.json"
    save_output({"key": "value"}, path)
    assert path.exists()

# Use monkeypatch for env vars
def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError):
        initialize_client()
```

### Coverage

```bash
pytest --cov=scripts --cov-report=term-missing tests/
```

Minimum: 80%. Uncovered lines should only be `__main__` blocks and `sys.path` guards.

### Naming Conventions

- File: `tests/test_<module_name>.py`
- MCP servers: `tests/test_mcp_servers/test_<server_name>.py`
- Function: `test_<function>_<scenario>`
- Fixtures: shared setup in `tests/conftest.py`

## Common Rationalizations

| Rationalization | Reality |
|----------------|---------|
| "Mocking is too complex for this function" | If the function is hard to mock, it's doing too much — refactor it |
| "We'll add tests after the feature ships" | Tests after shipping means bugs ship first; write tests alongside code |
| "80% coverage is arbitrary" | It's a ratchet — uncovered code is untested code, and untested agent code fails silently |
| "Integration tests are enough" | Integration tests are slow and flaky; unit tests with mocks give fast, deterministic feedback |
| "This is just a script, it doesn't need tests" | Scripts become library code when agents compose them — test them like library code |

## Red Flags

- Tests that make real API calls (no mocking)
- Tests that depend on other tests (shared mutable state)
- Missing error-path tests (only happy path covered)
- `monkeypatch` not used for environment variables
- `tmp_path` not used for file operations (tests write to repo)
- Test names that don't describe the scenario (`test_1`, `test_basic`)
- Coverage below 80% with no plan to improve
- Flaky tests ignored instead of fixed

## Verification

- [ ] All new/modified code has corresponding tests — **evidence**: `git diff --name-only` shows test files for each source file
- [ ] API calls mocked in all tests — **evidence**: grep for `Mock` or `patch` in test files, no real API imports
- [ ] Both success and error paths tested — **evidence**: test names include `_success` and `_error`/`_failure` variants
- [ ] Coverage ≥80% — **evidence**: `pytest --cov` output
- [ ] Tests use `tmp_path` for file I/O — **evidence**: no hardcoded paths in test files
- [ ] Tests use `monkeypatch` for env vars — **evidence**: no `os.environ` direct manipulation
- [ ] All tests pass: `pytest tests/ -v` — **evidence**: zero failures
