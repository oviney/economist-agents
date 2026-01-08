# Role-Aware Skills Manager

## Overview

The SkillsManager has been refactored to support role-aware configuration, allowing each agent role to maintain its own separate skills database. This enables better organization and isolation of learned patterns across different agent types in the multi-agent system.

## Architecture

```
Multi-Agent System
├── PO Agent → skills/po_agent_skills.json
├── SM Agent → skills/sm_agent_skills.json
├── QE Agent → skills/qe_agent_skills.json
├── Blog QA Agent → skills/blog_qa_skills.json
└── Custom Agent → skills/custom_agent_skills.json
```

Each agent role maintains its own skills database, preventing pattern contamination and enabling role-specific learning.

## Initialization Modes

The SkillsManager supports three initialization modes with a clear priority hierarchy:

### 1. Role-Aware Initialization (Recommended)

```python
from scripts.skills_manager import SkillsManager

# Product Owner Agent
po_manager = SkillsManager(role_name="po_agent")
# → skills/po_agent_skills.json

# Blog QA Agent
qa_manager = SkillsManager(role_name="blog_qa")
# → skills/blog_qa_skills.json

# Scrum Master Agent
sm_manager = SkillsManager(role_name="sm_agent")
# → skills/sm_agent_skills.json
```

**When to use:** When you want automatic path construction based on agent role. This is the recommended approach for new code.

### 2. Explicit File Path

```python
# Custom location
manager = SkillsManager(skills_file="custom/path/skills.json")
# → custom/path/skills.json

# Relative path
manager = SkillsManager(skills_file="skills/blog_qa_skills.json")
# → skills/blog_qa_skills.json
```

**When to use:** When you need full control over the file location, or for testing with temporary files.

**Note:** If both `skills_file` and `role_name` are provided, `skills_file` takes priority.

### 3. Default Mode (Backward Compatible)

```python
# No parameters - defaults to blog_qa
manager = SkillsManager()
# → skills/blog_qa_skills.json
```

**When to use:** For backward compatibility with existing code. All existing code without parameters will continue to work unchanged.

## Priority Hierarchy

When both parameters are provided, the initialization follows this priority:

1. **skills_file** (highest priority) - Uses explicit path if provided
2. **role_name** - Constructs path if skills_file not provided  
3. **Default** (lowest priority) - Falls back to "blog_qa" if neither provided

```python
# skills_file overrides role_name
manager = SkillsManager(
    role_name="po_agent",
    skills_file="skills/custom_skills.json"
)
# → uses skills/custom_skills.json (skills_file wins)
```

## Role Name Extraction

When using explicit file paths, the role name is automatically extracted from the filename:

```python
manager = SkillsManager(skills_file="skills/po_agent_skills.json")
print(manager.role_name)  # "po_agent"

manager = SkillsManager(skills_file="skills/blog_qa_skills.json")
print(manager.role_name)  # "blog_qa"
```

Pattern: Removes `_skills` suffix and `.json` extension from filename.

## API Reference

### Constructor

```python
def __init__(
    self,
    role_name: str | None = None,
    skills_file: str | Path | None = None
) -> None:
    """Initialize the SkillsManager for a specific role.
    
    Args:
        role_name: Name of the agent role. If provided, automatically
            constructs path as skills/{role_name}_skills.json.
        skills_file: Optional explicit path to skills file. Overrides
            role_name if both are provided.
    
    Example:
        >>> # Role-aware initialization
        >>> manager = SkillsManager(role_name="po_agent")
        >>> # Explicit file path
        >>> manager = SkillsManager(skills_file="custom/path.json")
        >>> # Default (backward compatible)
        >>> manager = SkillsManager()
    """
```

### Public Methods

All methods remain unchanged from the original implementation:

- `get_patterns(category: str | None = None) -> list[dict[str, Any]]`
- `learn_pattern(category: str, pattern_id: str, pattern_data: dict[str, Any]) -> None`
- `record_run(issues_found: int, issues_fixed: int = 0) -> None`
- `save() -> None`
- `get_stats() -> dict[str, Any]`
- `suggest_improvements(validation_results: dict[str, Any]) -> list[str]`
- `export_report() -> str`

See module docstrings for detailed API documentation.

## Migration Guide

### Existing Code (No Changes Required)

All existing code continues to work without modification:

```python
# Old code - still works identically
manager = SkillsManager()
manager.learn_pattern(...)
manager.save()
```

### New Code (Role-Aware)

For new agent implementations, use role-aware initialization:

```python
# New PO Agent code
class ProductOwnerAgent:
    def __init__(self):
        self.skills = SkillsManager(role_name="po_agent")
    
    def validate_story(self, story):
        # Use role-specific patterns
        patterns = self.skills.get_patterns("story_validation")
        # ...
```

## Usage Examples

### Example 1: Product Owner Agent

```python
from scripts.skills_manager import SkillsManager

# Initialize for PO Agent
po_skills = SkillsManager(role_name="po_agent")

# Learn story validation patterns
po_skills.learn_pattern(
    "story_validation",
    "missing_acceptance_criteria",
    {
        "severity": "high",
        "pattern": "User story missing acceptance criteria",
        "check": "Verify story has 3-7 testable AC",
        "learned_from": "Sprint 8 backlog review"
    }
)

# Record validation run
po_skills.record_run(issues_found=5, issues_fixed=3)

# Save to skills/po_agent_skills.json
po_skills.save()

# Get statistics
stats = po_skills.get_stats()
print(f"Total runs: {stats['total_runs']}")
```

### Example 2: Blog QA Agent

```python
# Initialize for Blog QA
qa_skills = SkillsManager(role_name="blog_qa")

# Learn SEO patterns
qa_skills.learn_pattern(
    "seo_validation",
    "missing_meta_description",
    {
        "severity": "medium",
        "pattern": "Blog post missing meta description",
        "check": "Verify front matter has description field",
        "learned_from": "SEO audit"
    }
)

# Get SEO patterns only
seo_patterns = qa_skills.get_patterns("seo_validation")

# Save to skills/blog_qa_skills.json
qa_skills.save()
```

### Example 3: Multiple Agents in One Application

```python
# Different skills databases for different agents
po_skills = SkillsManager(role_name="po_agent")
qa_skills = SkillsManager(role_name="blog_qa")
sm_skills = SkillsManager(role_name="sm_agent")

# Each maintains independent patterns
po_skills.learn_pattern("story_validation", "missing_ac", {...})
qa_skills.learn_pattern("seo_validation", "missing_title", {...})
sm_skills.learn_pattern("sprint_validation", "incomplete_dor", {...})

# All save to different files
po_skills.save()  # → skills/po_agent_skills.json
qa_skills.save()  # → skills/blog_qa_skills.json
sm_skills.save()  # → skills/sm_agent_skills.json
```

## File Structure

Each agent's skills file follows the same structure:

```json
{
  "version": "1.0",
  "last_updated": "2026-01-04T12:34:56.789Z",
  "skills": {
    "category_name": {
      "description": "Category description",
      "patterns": [
        {
          "id": "pattern_id",
          "severity": "high",
          "pattern": "Description of pattern",
          "check": "How to check for this pattern",
          "learned_from": "Context where learned",
          "learned_on": "2026-01-04T12:34:56.789Z",
          "last_seen": "2026-01-04T12:34:56.789Z"
        }
      ]
    }
  },
  "validation_stats": {
    "total_runs": 10,
    "issues_found": 25,
    "issues_fixed": 20,
    "last_run": "2026-01-04T12:34:56.789Z"
  }
}
```

## Testing

The refactored code includes comprehensive type hints and has been validated with mypy:

```bash
# Type checking
mypy scripts/skills_manager.py --ignore-missing-imports

# Functional tests
python3 examples/skills_manager_usage.py
```

All tests pass successfully, confirming:
- Role-aware initialization works correctly
- Explicit file paths are handled properly
- Default backward compatibility is maintained
- Type hints are correct and complete

## Benefits

1. **Isolation**: Each agent maintains separate skills databases
2. **Organization**: Clear mapping between agent roles and skills files
3. **Scalability**: Easy to add new agent roles without conflicts
4. **Backward Compatible**: Existing code works without changes
5. **Type Safe**: Comprehensive type hints validated by mypy
6. **Well Documented**: Google-style docstrings throughout

## Performance

The refactoring uses `orjson` for improved JSON performance:
- **Reading**: ~2x faster than standard `json` library
- **Writing**: ~3x faster with `OPT_INDENT_2` option
- **Memory**: More efficient for large skills databases

## Logging

All operations are logged for debugging and audit purposes:

```python
import logging
logger = logging.getLogger(__name__)

# Example log output
INFO:skills_manager:Initializing SkillsManager for role: po_agent
INFO:skills_manager:Skills file path: /path/to/skills/po_agent_skills.json
INFO:skills_manager:Saved skills to /path/to/skills/po_agent_skills.json
```

## Best Practices

1. **Always specify role_name** for new code
2. **Use consistent role naming** (lowercase with underscores)
3. **Call save() after learning patterns** to persist immediately
4. **Use get_patterns(category)** to filter patterns efficiently
5. **Record validation runs** for statistics tracking

## Troubleshooting

### Issue: ModuleNotFoundError: No module named 'orjson'

**Solution:** Activate virtual environment and install dependencies:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Issue: ModuleNotFoundError: No module named 'scripts'

**Problem:** When running example scripts from `examples/` directory, Python cannot find the scripts module.

**Solution:** The examples need to add the parent directory to Python's path. This is included in `examples/skills_manager_usage.py`:
```python
import sys
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.skills_manager import SkillsManager
```

**Alternative solutions:**
- Run as module: `python -m examples.skills_manager_usage`
- Set PYTHONPATH: `PYTHONPATH=. python examples/skills_manager_usage.py`
- Install project: `pip install -e .` (requires setup.py)

### Issue: FileNotFoundError when saving

**Solution:** The SkillsManager automatically creates parent directories. Ensure write permissions:
```bash
chmod -R u+w skills/
```

### Issue: Role name not extracted correctly

**Solution:** Role name is extracted from filename by removing `_skills.json`. Ensure your filename follows the pattern `{role_name}_skills.json`.

## Future Enhancements

Potential future improvements:
- [ ] Skills sharing/export between agents
- [ ] Pattern effectiveness scoring
- [ ] Automatic pattern pruning for low-value patterns
- [ ] Cross-agent pattern recommendations
- [ ] Skills database versioning and migration

## Version History

- **v2.0** (2026-01-04): Role-aware refactoring with orjson and type hints
- **v1.0** (2025-12-31): Initial implementation for blog_qa agent

## See Also

- [CLAUDE.md](../CLAUDE.md) - Python coding standards
- [skills/python-quality/SKILL.md](../skills/python-quality/SKILL.md) - Quality standards
- [examples/skills_manager_usage.py](../examples/skills_manager_usage.py) - Usage examples
