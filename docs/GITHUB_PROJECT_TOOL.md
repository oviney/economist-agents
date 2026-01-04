# GitHub Project Tool - Integration Guide

## Overview

`GitHubProjectTool` is a CrewAI/LangChain compatible tool that wraps the GitHub CLI `gh project item-add` command. This tool is necessary because the standard GitHub MCP server does not yet support Project V2 mutations.

## Installation

### Prerequisites

1. **GitHub CLI (gh)** must be installed and authenticated:
   ```bash
   # Install gh (macOS)
   brew install gh
   
   # Authenticate
   gh auth login
   ```

2. **Python dependencies** are already included in the project (crewai, pydantic)

## Usage in agent_registry.py

### Basic Registration

```python
from scripts.tools.github_project_tool import GitHubProjectTool

# In your agent configuration
agent = Agent(
    role="Project Manager",
    goal="Manage GitHub projects",
    tools=[
        GitHubProjectTool(),
        # ... other tools
    ]
)
```

### Full Example

```python
#!/usr/bin/env python3
"""Example agent_registry.py integration."""

from crewai import Agent, Task, Crew
from scripts.tools.github_project_tool import GitHubProjectTool

# Create the tool instance
github_project_tool = GitHubProjectTool()

# Define an agent that uses the tool
project_manager = Agent(
    role="GitHub Project Manager",
    goal="Organize issues into project boards",
    backstory=(
        "You are an experienced project manager who keeps the team "
        "organized by tracking issues in GitHub Projects."
    ),
    tools=[github_project_tool],
    verbose=True,
)

# Create a task that uses the tool
organize_task = Task(
    description=(
        "Add issue #42 to project board 1 for the economist-agents repository. "
        "The owner is 'oviney'."
    ),
    expected_output="Confirmation that the issue was added to the project",
    agent=project_manager,
)

# Run the crew
crew = Crew(
    agents=[project_manager],
    tasks=[organize_task],
    verbose=True,
)

result = crew.kickoff()
print(result)
```

## Tool Parameters

### Required Parameters

- **issue_id** (int): The GitHub issue number (e.g., 42 for issue #42)
- **project_number** (int): The GitHub project number (visible in project URL)

### Optional Parameters (with defaults)

- **owner** (str): Repository owner username or org name (default: "oviney")
- **repo** (str): Repository name (default: "economist-agents")

## Example Tool Calls

### Default Repository (economist-agents)

```python
# Agent will call this internally
result = tool._run(
    issue_id=42,
    project_number=1
)
# Output: "Successfully added issue #42 to project 1"
```

### Custom Repository

```python
result = tool._run(
    issue_id=15,
    project_number=2,
    owner="myorg",
    repo="myproject"
)
# Output: "Successfully added issue #15 to project 2"
```

## Error Handling

The tool handles several error cases gracefully:

1. **GitHub CLI not installed**: Returns error message with installation link
2. **Command timeout**: 30-second timeout with clear error message
3. **Command failure**: Includes exit code and stderr details
4. **Authentication issues**: gh CLI error messages passed through

### Example Error Responses

```python
# If gh is not installed
"Error: GitHub CLI (gh) not found. Install it from: https://cli.github.com/"

# If issue doesn't exist
"Error: Failed to add issue #999 to project 1. Exit code: 1
Error details: could not resolve to an Issue"

# If project doesn't exist
"Error: Failed to add issue #42 to project 999. Exit code: 1
Error details: could not resolve to a ProjectV2"
```

## Testing

### Standalone Testing

```bash
# Run the tool's test function
python3 scripts/tools/github_project_tool.py
```

### Integration Testing

```python
from scripts.tools.github_project_tool import GitHubProjectTool

tool = GitHubProjectTool()

# Test with a real issue (requires gh authentication)
result = tool._run(issue_id=1, project_number=1)
print(result)
```

## Logging

The tool uses Python's logging module for operational visibility:

```python
import logging

# Enable debug logging to see tool operations
logging.basicConfig(level=logging.DEBUG)

# Tool will log:
# - INFO: Successful operations
# - ERROR: Failures with details
```

## Type Safety

The tool includes comprehensive type hints:

```python
def _run(
    self,
    issue_id: int,           # Must be >= 1
    project_number: int,     # Must be >= 1
    owner: str = "oviney",
    repo: str = "economist-agents",
) -> str:                    # Always returns a string (success or error)
    ...
```

## CrewAI Integration Details

The tool extends `BaseTool` from CrewAI and automatically:

1. **Generates schema** from `GitHubProjectToolInput` Pydantic model
2. **Validates inputs** using Pydantic's validation (e.g., `ge=1` for positive integers)
3. **Provides metadata** (name, description) for agent reasoning
4. **Handles serialization** for agent-to-agent communication

## Troubleshooting

### Issue: "gh: command not found"

**Solution**: Install GitHub CLI
```bash
brew install gh  # macOS
# or visit https://cli.github.com/
```

### Issue: "authentication required"

**Solution**: Authenticate with GitHub
```bash
gh auth login
```

### Issue: "could not resolve to an Issue"

**Possible causes**:
- Issue number doesn't exist
- Wrong owner/repo specified
- Private repo without access

**Solution**: Verify issue exists at `https://github.com/{owner}/{repo}/issues/{issue_id}`

### Issue: "could not resolve to a ProjectV2"

**Possible causes**:
- Project number doesn't exist for that owner
- Wrong owner specified
- Private project without access

**Solution**: Verify project exists and get correct number from project URL

## Future Enhancements

Potential improvements for future versions:

1. **Bulk operations**: Add multiple issues at once
2. **Field updates**: Set project fields (status, priority) when adding
3. **Validation**: Pre-flight check if issue/project exists
4. **Caching**: Remember recently used project numbers
5. **Async support**: Implement `_arun` for async agents

## Related Documentation

- [CrewAI Tools Documentation](https://docs.crewai.com/core-concepts/Tools/)
- [GitHub CLI Projects Reference](https://cli.github.com/manual/gh_project)
- [GitHub Projects V2 API](https://docs.github.com/en/graphql/reference/objects#projectv2)
