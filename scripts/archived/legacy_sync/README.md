# Legacy GitHub Sync Scripts (Archived)

**Archived Date**: 2026-01-03 (Sprint 9)

**Reason**: Replaced by GitHub MCP Server integration

## Archived Scripts

### github_sprint_sync.py
- **Purpose**: Synchronized sprint tracker with GitHub Issues
- **Replaced by**: GitHub MCP Server `create_issue`, `update_issue`, `list_issues` tools
- **Migration**: See `.github/agents/scrum-master-v3.agent.md` for MCP-based workflows

### sync_github_project.py  
- **Purpose**: Synced backlog items to GitHub Projects V2
- **Replaced by**: GitHub MCP Server `create_issue` + custom Projects V2 integration
- **Migration**: MCP server handles issue creation, Projects V2 API handles project management

### github_issue_validator.py
- **Purpose**: Validated GitHub issue creation before syncing
- **Replaced by**: GitHub MCP Server's built-in validation and error handling
- **Migration**: MCP tools provide automatic validation and detailed error messages

## Why MCP?

The GitHub MCP Server provides:
- **Standardized Interface**: Consistent tool interface across all GitHub operations
- **Better Error Handling**: Detailed error messages and automatic retries
- **Real-time Sync**: Direct API access without intermediate JSON files
- **Reduced Maintenance**: No custom sync logic to maintain
- **Multi-Agent Support**: All agents can use the same GitHub tools

## Migration Guide

**Old Pattern** (Legacy Scripts):
```python
# Write to sprint_tracker.json
tracker.update_story(story_id, status="complete")

# Run sync script
subprocess.run(["python3", "scripts/github_sprint_sync.py"])
```

**New Pattern** (GitHub MCP):
```python
# Direct GitHub API call via MCP
github_mcp.create_issue(
    title=story["title"],
    body=story["description"],
    labels=["sprint-9", "story"]
)
```

See Sprint 9 Story 6 documentation for complete migration examples.
