Archived article_fixer.py - not needed with strengthened prompts

## GitHub Sync Scripts (Archived 2026-01-03, Sprint 9)

**Reason**: Migrated to GitHub MCP Server for standardized tooling

**Legacy Scripts** (moved to `scripts/archived/legacy_sync/`):
- `github_sprint_sync.py` - Replaced by GitHub MCP `create_issue`, `update_issue` tools
- `sync_github_project.py` - Replaced by GitHub MCP `create_issue` + Projects V2 integration  
- `github_issue_validator.py` - Replaced by GitHub MCP's built-in validation

**Migration**: See `scripts/archived/legacy_sync/README.md` for detailed migration guide and `.github/agents/scrum-master-v3.agent.md` for MCP-based workflows
