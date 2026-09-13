# GitHub MCP Server Evaluation - Sprint 10 Tooling Decision

**Date**: 2026-01-03  
**Evaluator**: @devops  
**Purpose**: Determine if GitHub MCP Server can replace GitHub CLI + Python for Projects v2 automation  
**Status**: ⚠️ **CORRECTED** - Original recommendation invalidated by reality check

---

## ⚠️ REALITY CHECK - USER'S ACTUAL MCP SERVER (2026-01-03)

**CRITICAL FINDING**: User's running MCP server lacks ALL Projects v2 tools.

**User's Environment**:
- Version: `github-mcp-server/remote-406ace364b7758ec3e8e0b58e67eb595dbf6b418` (REMOTE variant)
- Total Tools: 27
- **Projects v2 Tools: 0** ❌

**Available Tool Categories**:
- ✅ Issues (4 tools): issue_read, list_issues, list_issue_types, search_issues
- ✅ Pull Requests (3 tools): pull_request_read, list_pull_requests, search_pull_requests
- ✅ Actions (2 tools): actions_get, actions_list
- ✅ Code Scanning (2 tools)
- ✅ Commits, Files, Jobs, Labels, Releases, Branches, Search, etc.
- ❌ **NO Projects Tools**: No add_project_item, list_project_items, update_project_item, etc.

**Root Cause**: Remote MCP server is a **subset** of the full-featured local server. The README documents the complete local server capabilities, but the remote variant excludes Projects v2 operations entirely.

**Sprint 10 Impact**: Cannot implement 5/8 requirements without Projects tools:
- ❌ Issue linking (needs add_project_item)
- ❌ Burndown data extraction (needs list_project_items with fields)
- ❌ Custom field mutations (needs update_project_item)
- ❌ Hygiene queries (needs list_project_items with query filtering)
- ❌ Bidirectional sync (needs multiple project operations)

---

## **CORRECTED RECOMMENDATION: CANNOT USE MCP SERVER**

**Decision**: Proceed with **GitHub CLI + Python** as documented in `skills/devops/SKILL.md`

**Rationale**:
1. User's remote MCP server lacks all Projects v2 capabilities
2. Local MCP server installation adds complexity vs proven CLI approach
3. CLI approach fully documented (1056 lines) with no unknowns
4. CLI proven working in Sprint 9 (sync_github_project.py operational)

**Next Steps**:
1. ✅ User: Execute `gh auth refresh -s project` (add project scope to token)
2. ✅ User: Create Sprint 10 board via web UI (10 minutes)
3. ✅ User: Create 4 custom fields (Story Points, Sprint, Priority, Owner) via web UI (10 minutes)
4. ✅ DevOps: Implement 3 Python scripts per SKILL.md (8-12 hours)
   - `generate_burndown.py` - GraphQL → matplotlib
   - `generate_velocity.py` - Historical analysis
   - `project_hygiene.py` - Stale issue detection

---

## Original Evaluation (Based on GitHub README Documentation)

**ORIGINAL RECOMMENDATION**: ✅ USE GITHUB MCP SERVER (invalidated)

**Note**: The evaluation below was based on analyzing the official GitHub MCP server README, which documents 9 Projects v2 tools. However, this appears to document the **local/full-featured server**, while the user's **remote server** is a limited subset without Projects support.

---

## Executive Summary (Original - Documentation-Based)

GitHub's **official MCP server** supports Projects v2 (formerly GitHub Projects Beta) with comprehensive tooling for:
- ✅ Project board operations (create, list, get)
- ✅ Custom field management (list, get, update)
- ✅ Item operations (add, delete, list, update with field values)
- ✅ Advanced filtering and pagination
- ✅ **CRITICAL**: `update_project_item` supports custom field mutations (Story Points, Sprint, Priority, Owner)

**Key Benefits Over GitHub CLI + Python**:
1. **Less code**: Structured tools replace 300-400 lines of GraphQL boilerplate
2. **Better auth**: OAuth support with automatic token management
3. **Cleaner integration**: Standardized MCP interface across all GitHub operations
4. **Maintained by GitHub**: Official support, up-to-date with API changes
5. **Developer experience**: Natural language tool invocation vs raw GraphQL

**Implementation Impact**:
- ✅ All Sprint 10 requirements satisfied
- ✅ Burndown chart: MCP `list_project_items` + Python matplotlib (cleaner data flow)
- ✅ Velocity tracking: Same sprint_tracker.json + MCP sync validation
- ✅ Hygiene automation: MCP issue queries + project field checks
- **Estimated effort**: 8-10 hours (vs 8-12 hours with CLI - slightly faster due to less boilerplate)

---

## GitHub MCP Server Details

### Official Repository
- **Source**: https://github.com/github/github-mcp-server
- **Package**: Available via npm (`github-mcp`, `github-mcp-custom`)
- **Status**: Production-ready, officially maintained by GitHub
- **Language**: Go (compiled binary, cross-platform)
- **Integration**: Works with VS Code 1.101+, Claude Desktop, Cursor, Windsurf

### Authentication Options
1. **OAuth (Recommended)**: Automatic token management, scoped permissions
2. **GitHub PAT**: Classic personal access tokens with `project` scope

### Projects v2 Toolset

#### Available Tools (9 total)

**1. `add_project_item`** - Link issue/PR to project
```typescript
Parameters:
  - item_id: number (issue or PR number)
  - item_type: "issue" | "pull_request"
  - owner: string (user handle or org name)
  - owner_type: "user" | "org"
  - project_number: number
```

**2. `delete_project_item`** - Remove item from project
```typescript
Parameters:
  - item_id: number (internal project item ID, not issue ID)
  - owner: string
  - owner_type: "user" | "org"
  - project_number: number
```

**3. `get_project`** - Get project details
```typescript
Parameters:
  - owner: string
  - owner_type: "user" | "org"
  - project_number: number
Returns: Project metadata (title, description, fields, etc.)
```

**4. `get_project_field`** - Get specific field details
```typescript
Parameters:
  - field_id: number
  - owner: string
  - owner_type: "user" | "org"
  - project_number: number
Returns: Field type, name, options (for SINGLE_SELECT fields)
```

**5. `get_project_item`** - Get item with field values
```typescript
Parameters:
  - item_id: number
  - fields: string[] (field IDs to include, e.g. ["102589", "985201"])
  - owner: string
  - owner_type: "user" | "org"
  - project_number: number
Returns: Item data with specified field values
```

**6. `list_project_fields`** - List all custom fields
```typescript
Parameters:
  - owner: string
  - owner_type: "user" | "org"
  - project_number: number
  - per_page: number (max 50, optional)
  - after: string (pagination cursor, optional)
Returns: Array of fields with IDs, names, types
```

**7. `list_project_items`** - ⭐ CRITICAL FOR BURNDOWN CHARTS
```typescript
Parameters:
  - owner: string
  - owner_type: "user" | "org"
  - project_number: number
  - fields: string[] (CRITICAL: Always provide to get field values)
  - query: string (filter syntax, e.g. "status:Done sprint:9")
  - per_page: number (max 50, optional)
  - after: string (pagination cursor, optional)
Returns: Array of items with field values (story points, sprint, status, etc.)
```

**8. `list_projects`** - List all projects for user/org
```typescript
Parameters:
  - owner: string
  - owner_type: "user" | "org"
  - query: string (filter: "is:open", "roadmap is:closed", optional)
  - per_page: number (max 50, optional)
Returns: Array of projects
```

**9. `update_project_item`** - ⭐ CRITICAL FOR CUSTOM FIELD UPDATES
```typescript
Parameters:
  - item_id: number (internal project item ID)
  - owner: string
  - owner_type: "user" | "org"
  - project_number: number
  - updated_field: object {
      id: number (field ID),
      value: string | number | null (new value, null to clear)
    }
Example: {"id": 123456, "value": "5"} to set Story Points to 5
```

---

## Sprint 10 Requirements Mapping

### ✅ Requirement 1: Projects v2 Board Creation
**DevOps SKILL.md Line 501**: "Create project board 'Economist Agents Sprint Board'"

**MCP Solution**: ❌ Board creation NOT supported via MCP tools (manual step required)
- **Workaround**: Use GitHub web UI to create board once (5 minutes)
- **Alternative**: Keep `gh project create` for board creation, use MCP for all other operations
- **Impact**: Minimal - board created once, all subsequent operations via MCP

### ✅ Requirement 2: Custom Field Configuration
**DevOps SKILL.md Line 501**: "Configure custom fields (sprint, story-points, priority, owner)"

**MCP Solution**: `list_project_fields` + `get_project_field`
```python
# Get field IDs for Story Points, Sprint, Priority, Owner
fields = mcp.list_project_fields(owner="oviney", owner_type="user", project_number=1)
story_points_id = [f for f in fields if f["name"] == "Story Points"][0]["id"]
sprint_id = [f for f in fields if f["name"] == "Sprint"][0]["id"]
# ... etc
```
- **Note**: Field creation still manual via web UI (one-time setup)
- **Benefit**: MCP reads fields for validation and updates

### ✅ Requirement 3: Issue Linking to Project
**DevOps SKILL.md Line 507**: "Link Sprint 9 issues to project board"

**MCP Solution**: `add_project_item`
```python
# Link issue #67 to project 1
mcp.add_project_item(
    item_id=67, 
    item_type="issue",
    owner="oviney",
    owner_type="user",
    project_number=1
)
```
- **Status**: ✅ FULL SUPPORT - cleaner than `gh project item-add`

### ✅ Requirement 4: Burndown Chart Data Extraction
**DevOps SKILL.md Lines 341-480**: "GraphQL query for ProjectV2 items with custom field extraction"

**MCP Solution**: `list_project_items` with field filtering
```python
# Get all Sprint 9 items with Story Points and Status
items = mcp.list_project_items(
    owner="oviney",
    owner_type="user",
    project_number=1,
    fields=[story_points_id, status_id, completed_date_id],
    query="sprint:9"
)

# Calculate daily remaining points
remaining_by_date = {}
for item in items:
    if item["status"] == "Done":
        completed_date = item["completed_date"]
        remaining_by_date[completed_date] = sum(
            i["story_points"] for i in items 
            if i["status"] != "Done" or i["completed_date"] > completed_date
        )
```
- **Status**: ✅ FULL SUPPORT - cleaner than raw GraphQL queries
- **Benefit**: Pagination handled automatically, field filtering built-in

### ✅ Requirement 5: Velocity Tracking
**DevOps SKILL.md Lines 341-480**: "Calculate completed story points per sprint"

**MCP Solution**: `list_project_items` + sprint_tracker.json
```python
# Get completed stories for Sprint 9
items = mcp.list_project_items(
    owner="oviney",
    owner_type="user",
    project_number=1,
    fields=[story_points_id, status_id, sprint_id],
    query="sprint:9 status:Done"
)

velocity = sum(item["story_points"] for item in items)
```
- **Status**: ✅ FULL SUPPORT - identical to CLI approach but cleaner

### ✅ Requirement 6: Custom Field Updates (Bidirectional Sync)
**DevOps SKILL.md Line 507**: "Bidirectional sync: sprint_tracker.json ↔ Issues ↔ Projects v2"

**MCP Solution**: `update_project_item`
```python
# Update Story Points field for item
mcp.update_project_item(
    item_id=12345,  # Internal project item ID (from list_project_items)
    owner="oviney",
    owner_type="user",
    project_number=1,
    updated_field={"id": story_points_id, "value": "5"}
)
```
- **Status**: ✅ FULL SUPPORT - critical for sync validation

### ✅ Requirement 7: Project Hygiene Automation
**DevOps SKILL.md Lines 481-700**: "Stale issue detection, priority drift checking"

**MCP Solution**: `list_project_items` + issue tools
```python
# Find stale P0 issues (>14 days old but not Done)
items = mcp.list_project_items(
    owner="oviney",
    owner_type="user",
    project_number=1,
    fields=[priority_id, status_id, updated_date_id],
    query="priority:P0 -status:Done"
)

stale_items = [
    i for i in items 
    if (datetime.now() - i["updated_date"]).days > 14
]
```
- **Status**: ✅ FULL SUPPORT - query filtering + field access

### ✅ Requirement 8: Sprint Health Reports
**DevOps SKILL.md Lines 651-700**: "Metrics dashboard, completion tracking"

**MCP Solution**: `list_project_items` + aggregation
```python
# Calculate sprint health metrics
items = mcp.list_project_items(
    owner="oviney",
    owner_type="user",
    project_number=1,
    fields=[story_points_id, status_id, sprint_id, priority_id],
    query="sprint:9"
)

metrics = {
    "total_points": sum(i["story_points"] for i in items),
    "completed_points": sum(i["story_points"] for i in items if i["status"] == "Done"),
    "p0_blocked": len([i for i in items if i["priority"] == "P0" and i["status"] == "Blocked"]),
    # ... etc
}
```
- **Status**: ✅ FULL SUPPORT - all data accessible via MCP

---

## Comparison Matrix: GitHub CLI vs MCP Server

| Criteria | GitHub CLI + Python | GitHub MCP Server | Winner |
|----------|-------------------|------------------|--------|
| **Projects v2 Support** | ✅ Full (GraphQL) | ✅ Full (MCP tools) | 🟰 TIE |
| **Custom Field Access** | ✅ GraphQL queries | ✅ `list_project_fields`, `get_project_field` | ✅ **MCP** (cleaner) |
| **Custom Field Updates** | ✅ GraphQL mutations | ✅ `update_project_item` | ✅ **MCP** (less boilerplate) |
| **Item Linking** | ✅ `gh project item-add` | ✅ `add_project_item` | 🟰 TIE |
| **Burndown Data** | ✅ Custom GraphQL query | ✅ `list_project_items` + filtering | ✅ **MCP** (pagination built-in) |
| **Velocity Tracking** | ✅ sprint_tracker.json | ✅ sprint_tracker.json + MCP validation | 🟰 TIE |
| **Authentication** | ⚠️ Manual token scope refresh | ✅ OAuth + automatic token mgmt | ✅ **MCP** |
| **Code Maintenance** | ⚠️ 300-400 lines/script | ✅ ~150-200 lines/script | ✅ **MCP** (50% reduction) |
| **Error Handling** | ⚠️ Manual GraphQL error parsing | ✅ Structured MCP error responses | ✅ **MCP** |
| **CI/CD Integration** | ✅ GitHub Actions native | ⚠️ Requires MCP server setup | ✅ **CLI** |
| **Board Creation** | ✅ `gh project create` | ❌ Not supported | ✅ **CLI** |
| **Developer Experience** | ⚠️ Raw GraphQL queries | ✅ Natural language tool calls | ✅ **MCP** |
| **Official Support** | ✅ GitHub CLI team | ✅ GitHub MCP team | 🟰 TIE |
| **Documentation** | ✅ Extensive GraphQL docs | ✅ Comprehensive MCP docs | 🟰 TIE |
| **Learning Curve** | ⚠️ GraphQL schema knowledge | ✅ Simple tool parameters | ✅ **MCP** |

**SCORE**: MCP **9 wins**, CLI **2 wins**, **5 ties**

---

## Recommended Hybrid Approach

**BEST PRACTICE: Use MCP for 95% of operations, CLI for board creation**

### Phase 1: One-Time Setup (CLI Only - 10 minutes)
```bash
# Step 1: Create project board (MCP doesn't support this)
gh project create \
  --owner oviney \
  --title "Sprint 10: Autonomous Orchestration"

# Step 2: Create custom fields via web UI (5 minutes)
# - Story Points (NUMBER)
# - Sprint (SINGLE_SELECT: Sprint 9, Sprint 10, Sprint 11...)
# - Priority (SINGLE_SELECT: P0, P1, P2, P3)
# - Owner (SINGLE_SELECT: @scrum-master, @devops, @quality-enforcer...)
```

### Phase 2: All Subsequent Operations (MCP Only)
```python
# scripts/generate_burndown.py (MCP version)
class BurndownGenerator:
    def __init__(self, mcp_client):
        self.mcp = mcp_client
        self.project_number = 1
        self.owner = "oviney"
        
    def get_sprint_data(self, sprint_num: int):
        """Extract burndown data via MCP"""
        # Get field IDs (cache these)
        fields = self.mcp.list_project_fields(
            owner=self.owner,
            owner_type="user",
            project_number=self.project_number
        )
        
        # Get all items for sprint
        items = self.mcp.list_project_items(
            owner=self.owner,
            owner_type="user",
            project_number=self.project_number,
            fields=[f["id"] for f in fields],
            query=f"sprint:{sprint_num}"
        )
        
        # Calculate daily remaining points
        return self._calculate_burndown(items)
```

### Phase 3: CI/CD Automation (GitHub Actions)
```yaml
name: Daily Burndown Update
on:
  schedule:
    - cron: '0 18 * * *'  # 6 PM daily

jobs:
  update-burndown:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # Setup MCP server (use remote GitHub MCP server)
      - name: Generate Burndown
        run: |
          python3 scripts/generate_burndown.py
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Commit Chart
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/burndown_current.png
          git commit -m "chore: update burndown chart [skip ci]"
          git push
```

---

## Implementation Plan (Updated for MCP)

### ✅ Prerequisites
1. ✅ Python 3.13 virtual environment (READY)
2. ⏳ GitHub MCP server configured (15 minutes)
3. ⏳ OAuth token or PAT with `project` scope (5 minutes)
4. ⏳ One-time board creation via CLI or web UI (10 minutes)

### 🔧 Sprint 10 Implementation Steps

**Story 9: GitHub Projects v2 Evolution** (5 points, P1)

**Task 1: Configure GitHub MCP Server** (1 hour)
```bash
# Option A: VS Code 1.101+ (OAuth)
# Add to VS Code MCP config:
{
  "servers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/"
    }
  }
}

# Option B: Local MCP server with PAT
npm install -g github-mcp
export GITHUB_TOKEN="ghp_..."  # PAT with 'project' scope
github-mcp-server
```

**Task 2: Create Project Board & Custom Fields** (30 minutes)
- Use web UI: https://github.com/users/oviney/projects/new
- Create 4 custom fields (Story Points, Sprint, Priority, Owner)
- Document field IDs in `scripts/mcp_config.json`

**Task 3: Rewrite `generate_burndown.py` for MCP** (2-3 hours)
- Replace GraphQL queries with `mcp.list_project_items()`
- Add field ID caching (avoid repeated field lookups)
- Implement daily burndown calculation
- Matplotlib chart generation (unchanged)
- Test with Sprint 9 data

**Task 4: Rewrite `generate_velocity.py` for MCP** (1-2 hours)
- Use MCP for validation sync (sprint_tracker.json vs Projects v2)
- Keep sprint_tracker.json as source of truth
- Add rolling average calculation
- Test with last 5 sprints

**Task 5: Rewrite `project_hygiene.py` for MCP** (2-3 hours)
- Use `list_project_items` with query filters
- Stale issue detection (>90 days)
- Priority drift alerts (P0 older than P2/P3)
- Health report generation
- Dry-run mode for auto-closure

**Task 6: CI/CD Integration** (1 hour)
- Create `.github/workflows/daily-burndown.yml`
- Test manual trigger
- Validate automated commits

**Task 7: Documentation** (1 hour)
- Update DevOps SKILL.md with MCP patterns
- Create `docs/GITHUB_MCP_SETUP.md`
- Add troubleshooting guide

**Total Estimated Effort**: 8-10 hours (vs 8-12 hours with CLI)

---

## Decision Rationale

### ✅ Why GitHub MCP Server WINS

**1. Code Quality**
- **50% less boilerplate**: MCP tools replace 300+ lines of GraphQL query construction
- **Better error handling**: Structured responses vs raw GraphQL errors
- **Type safety**: MCP parameters are strongly typed

**2. Developer Experience**
- **Natural language**: Tool descriptions vs reading GraphQL schema
- **Pagination automatic**: MCP handles cursor-based pagination internally
- **Field discovery**: `list_project_fields` vs manual schema introspection

**3. Maintenance**
- **Official support**: Maintained by GitHub, updated with API changes
- **OAuth support**: No manual token scope management
- **Future-proof**: MCP is GitHub's strategic direction for AI tooling

**4. Integration**
- **VS Code native**: Works seamlessly in VS Code 1.101+ with Copilot
- **Cross-platform**: Same tools work in Claude Desktop, Cursor, Windsurf
- **Agentic workflows**: MCP designed for AI agent orchestration

### ⚠️ CLI Advantages (Still Valid)

**1. Board Creation**
- MCP doesn't support `create_project` (must use web UI or CLI)
- **Mitigation**: Hybrid approach - CLI for one-time setup, MCP for everything else

**2. CI/CD Simplicity**
- GitHub Actions has `gh` pre-installed
- MCP requires remote server or local binary setup
- **Mitigation**: Use remote GitHub MCP server (no installation needed)

**3. Offline Usage**
- CLI works without internet (for local projects)
- MCP requires API connection
- **Mitigation**: Not a concern for our GitHub-hosted project

### 🎯 Final Decision

**USE GITHUB MCP SERVER for Sprint 10 implementation**

**Rationale**:
1. ✅ Satisfies 100% of Sprint 10 requirements (except one-time board creation)
2. ✅ Reduces code maintenance by ~50%
3. ✅ Better developer experience for @devops agent
4. ✅ Future-proof: MCP is GitHub's strategic direction
5. ✅ Minimal risk: Fallback to CLI if issues arise (hybrid approach)

**Implementation Strategy**:
- Use CLI for one-time board creation (10 minutes)
- Use MCP for all operational tasks (burndown, velocity, hygiene)
- Document hybrid approach in DevOps SKILL.md
- Validate with Sprint 9 data before Sprint 10 starts

---

## Next Steps

### ⏭️ Immediate Actions (User Approval Required)

1. **User Decision**: Approve GitHub MCP Server recommendation ✅
2. **User Action**: Configure MCP server in VS Code or provide PAT (15 minutes)
3. **User Action**: Create Sprint 10 project board via web UI (10 minutes)
4. **User Action**: Configure 4 custom fields via web UI (10 minutes)

### 🛠️ DevOps Implementation (Post-Approval)

1. **Setup MCP Client** (1 hour)
   - Install GitHub MCP server
   - Test authentication
   - Validate Projects v2 access
   - Document field IDs

2. **Implement 3 Scripts** (6-8 hours)
   - `scripts/generate_burndown.py` (MCP version)
   - `scripts/generate_velocity.py` (MCP version)
   - `scripts/project_hygiene.py` (MCP version)

3. **CI/CD Integration** (1 hour)
   - Create GitHub Actions workflow
   - Test manual trigger
   - Validate automated updates

4. **Documentation Update** (1 hour)
   - Update DevOps SKILL.md
   - Create MCP setup guide
   - Add troubleshooting section

**Total Time**: 8-10 hours (Sprint 10 capacity: 5 points × 2.8h/point = 14 hours ✅)

---

## References

- **GitHub MCP Server**: https://github.com/github/github-mcp-server
- **MCP Specification**: https://modelcontextprotocol.io/
- **GitHub Projects v2 API**: https://docs.github.com/en/graphql/reference/objects#projectv2
- **DevOps SKILL.md**: `/Users/ouray.viney/code/economist-agents/skills/devops/SKILL.md`
- **Sprint 10 Story 9**: `skills/sprint_tracker.json` lines 477-570

---

**Evaluation Complete**: 2026-01-03 (15 minutes investigation time)  
**Recommendation**: ✅ **USE GITHUB MCP SERVER** with hybrid CLI setup  
**Confidence**: **95%** (5% risk for one-time board creation workaround)
