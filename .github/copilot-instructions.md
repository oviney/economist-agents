# Economist Agents - AI Coding Instructions

## Project Purpose
Multi-agent content generation pipeline that produces publication-quality blog posts in The Economist's signature style. This is NOT a blog—it's a content factory with specialized AI agents for topic discovery, editorial voting, research, writing, editing, and chart generation.

## Architecture Overview

**3-Stage Pipeline:**
1. **Discovery** ([topic_scout.py](../scripts/topic_scout.py)) → Scans QE landscape, outputs ranked topics
2. **Editorial Board** ([editorial_board.py](../scripts/editorial_board.py)) → 6 persona agents vote on topics
3. **Content Generation** ([economist_agent.py](../scripts/economist_agent.py)) → Research → Write → Edit → Output markdown + charts

**Critical Data Flow:**
- Scout writes `content_queue.json` with scored topics
- Board writes `board_decision.json` with voting results
- Generator writes markdown files to `output/` or `_posts/` for Jekyll
- Charts saved as PNG to `assets/charts/` or `output/charts/`

## Code Organization Principles

### Prompts Are First-Class Code
Agent behavior is defined by large constant strings at the top of Python files (e.g., `RESEARCH_AGENT_PROMPT`, `WRITER_AGENT_PROMPT`). When modifying agent behavior, **edit these prompts first**—they are the source of truth, not comments.

Example from [economist_agent.py](../scripts/economist_agent.py#L28-L65):
```python
RESEARCH_AGENT_PROMPT = """You are a Research Analyst...
CRITICAL RULES:
1. Every statistic MUST have a named source
2. If you cannot verify a claim, mark it as [UNVERIFIED]
...
```

### Persona-Driven Editorial Board
Board members in [editorial_board.py](../scripts/editorial_board.py#L48-L145) are defined with:
- Explicit perspective and priorities
- "What makes you click" criteria
- "What makes you scroll past" filters
- Voting weights (e.g., VP Engineering has 1.2x weight)

When adding personas, follow this structure exactly. Voting logic is weighted consensus, not simple averaging.

### Chart Generation Constraints
[generate_chart.py](../scripts/generate_chart.py) and [CHART_DESIGN_SPEC.md](../docs/CHART_DESIGN_SPEC.md) define strict visual rules:
- **Zone separation**: No overlaps between title, chart, x-axis, source zones
- **Inline labels**: Must be in clear space, NOT on data lines
- **Colors**: `#17648d` (navy), `#843844` (burgundy), `#f1f0e9` (background)
- **No vertical gridlines**, only horizontal
- **Font**: DejaVu Sans throughout

Never violate zone boundaries—labels below y=20 in data coordinates risk X-axis intrusion.

## Economist Voice Enforcement

The Writer agent has **explicit banned patterns** (see [economist_agent.py](../scripts/economist_agent.py#L94-L137)):

**Forbidden openings:** "In today's world...", "It's no secret that...", "In recent years..."
**Banned phrases:** "game-changer", "paradigm shift", "leverage" (as verb), "at the end of the day"
**Forbidden closings:** "Only time will tell...", "In conclusion..."
**Tone violations:** Exclamation points, rhetorical questions as headers, listicle structure

When writing prompts or editing agent behavior, preserve these constraints. British spelling (organisation, favour, analyse) is mandatory.

## Skills Learning System

[blog_qa_agent.py](../scripts/blog_qa_agent.py) + [skills_manager.py](../scripts/skills_manager.py) implement continuous improvement:
- Validation errors are stored as "learned patterns" in `skills/blog_qa_skills.json`
- `SkillsManager.learn_pattern()` records issue category, severity, check, and example
- Future runs use accumulated patterns for smarter validation

When adding validation rules, use `skills_manager.learn_pattern()` to persist the knowledge.

## Developer Workflow

### Environment Setup
```bash
export ANTHROPIC_API_KEY='sk-ant-...'
pip install anthropic matplotlib numpy python-slugify pyyaml
```

### Running Pipeline
```bash
# Stage 1: Discover topics
python3 scripts/topic_scout.py

# Stage 2: Editorial voting (review content_queue.json first)
python3 scripts/editorial_board.py

# Stage 3: Generate article (review board_decision.json first)
python3 scripts/economist_agent.py

# Standalone chart testing
python3 scripts/generate_chart.py
```

### Integration with Jekyll Blogs
Set `OUTPUT_DIR` environment variable to point to `_posts/`:
```bash
export OUTPUT_DIR="/path/to/blog/_posts"
python3 scripts/economist_agent.py
```

Alternatively, configure in code (see [economist_agent.py](../scripts/economist_agent.py) line ~450-470 for output path logic).

## Common Patterns & Anti-Patterns

### ✅ DO
- Use structured JSON output from research agent for data verification
- Include `source_line` in chart_data for provenance
- Test charts standalone before integrating into article flow
- Use `slugify()` for Jekyll-compatible filenames (spaces → hyphens)
- Return complete markdown with YAML frontmatter from writer agent

### ❌ DON'T
- Mix British and American spelling within a single article
- Place chart labels below y=20 in data coordinates
- Use unverified statistics (research agent must flag these)
- Generate titles longer than 6 words without exceptional justification
- Create legends instead of inline labels for charts

## Testing & Validation

**Chart visual tests:** Run `scripts/generate_chart.py` and manually inspect:
1. Zone boundaries (use ruler tool to verify)
2. Label clearance from data lines
3. Color contrast on `#f1f0e9` background

**Article quality gates** (enforced by editor agent):
- Hemingway readability score < 10
- British spelling throughout
- No `[UNVERIFIED]` claims in final output
- Chart referenced naturally ("As the chart shows...")

**Blog QA checks** (see [blog_qa_agent.py](../scripts/blog_qa_agent.py)):
- YAML frontmatter validation (title, date, layout fields)
- Jekyll layout file existence
- Broken internal link detection
- AI disclosure flag if content mentions AI

## External Dependencies

- **Anthropic Claude API**: All agent reasoning via `anthropic.Anthropic()` client
- **matplotlib**: Chart generation (requires `TkAgg` or `Agg` backend)
- **Jekyll**: Implied consumer of markdown output (YAML frontmatter must be valid)
- **python-slugify**: URL-safe filenames for posts and charts

## File Naming Conventions

**Generated posts:** `YYYY-MM-DD-article-title.md` (Jekyll date-slug format)
**Charts:** `article-title.png` (matches post slug, no date prefix)
**Data files:** `content_queue.json`, `board_decision.json` (singular, snake_case)
**Skills:** `blog_qa_skills.json` (versioned JSON with timestamps)

## Key Gotchas

1. **Chart labels in X-axis zone:** Most common chart bug. Labels must stay above y=20 in data space.
2. **Unweighted voting:** Editorial board uses persona weights—don't sum scores naively.
3. **Missing source attribution:** Research agent outputs structured sources—writer must use them.
4. **Jekyll date mismatch:** Filename date and frontmatter `date:` must match exactly.
5. **Layout files:** Blog QA validates layout existence—create `_layouts/post.html` if missing.

## When Modifying Agents

1. **Identify which agent:** Scout (discovery) vs Board (voting) vs Generator (writing)
2. **Edit the system prompt:** Agent behavior is prompt-defined, not code logic
3. **Update banned patterns:** If adding style rules, mirror them in editor prompt
4. **Test data flow:** Ensure JSON outputs are consumed correctly by downstream agents
5. **Preserve governance checkpoints:** Manual review gates are intentional—don't automate them away

## Architecture Review & Learning System

This project uses a **Claude-style skills approach** for continuous improvement:

**Self-Learning Validation:**
- `blog_qa_agent.py` learns from each blog validation run
- `architecture_review.py` learns from codebase analysis
- Patterns stored in `skills/blog_qa_skills.json`
- Skills persist across runs for zero-config improvement

**Running Architecture Review:**
```bash
# Full review - learns 12+ architectural patterns
python3 scripts/architecture_review.py --full-review --export-docs

# View learned patterns
python3 scripts/architecture_review.py --show-skills

# Generates docs/ARCHITECTURE_PATTERNS.md automatically
```

**Pattern Categories Learned:**
- `agent_architecture`: Prompts-as-code, persona voting, orchestration
- `data_flow`: JSON intermediates, configurable outputs
- `prompt_engineering`: Structured outputs, constraint lists
- `error_handling`: Defensive parsing, verification flags
- `dependencies`: LLM client patterns, headless rendering
- `testing_strategy`: Human checkpoints, continuous learning

**When to Re-Run Review:**
- After significant refactoring
- Before onboarding new team members
- After adding new agents or pipeline stages
- To document emerging patterns

The architecture review agent automatically updates its knowledge base and exports markdown documentation.

## Defect Tracking & Quality Metrics

[defect_tracker.py](../scripts/defect_tracker.py) implements comprehensive bug tracking with Root Cause Analysis (v2.0):

**Enhanced Schema:**
- **Root Cause**: `root_cause` (enum), `root_cause_notes`, `introduced_in_commit`, `introduced_date`
- **Time Metrics**: `time_to_detect_days`, `time_to_resolve_days` (auto-calculated)
- **Test Gaps**: `missed_by_test_type`, `test_gap_description`, `prevention_test_added`, `prevention_test_file`
- **Prevention**: `prevention_strategy[]`, `prevention_actions[]`

**Key Methods:**
- `log_bug()` - Log new bug with optional RCA data
- `update_bug_rca()` - Backfill RCA data for existing bugs
- `fix_bug()` - Mark fixed and auto-calculate TTR
- `generate_report()` - Enhanced report with root causes, TTD, test gaps

**Critical Questions We Can Answer:**
1. Top 3 root causes (validation_gap, prompt_engineering, etc.)
2. Average TTD for critical bugs (target: <7 days, current: 5.5 days)
3. Which test types have gaps (visual_qa: 50%, integration_test: 50%)
4. Prevention test coverage (50% of bugs have regression tests)
5. Quality trends (defect escape rate: 50% baseline, target: <20%)

**Usage:**
```python
tracker = DefectTracker()
tracker.log_bug("BUG-021", "high", "production", "Description",
                root_cause="validation_gap",
                missed_by_test_type="integration_test")
tracker.fix_bug("BUG-021", "abc1234", prevention_test_added=True)
```

Run `python3 scripts/defect_tracker.py` to see full report with RCA insights.

## Scrum Master Process Discipline

**CRITICAL**: The Scrum Master persona MUST follow explicit process discipline to prevent execution without planning.

**Protocol Reference**: [SCRUM_MASTER_PROTOCOL.md](../docs/SCRUM_MASTER_PROTOCOL.md) (full 350-line protocol)

### NEVER Start Work Without (Hard Stops):

**Definition of Ready Checklist** - ALL must be complete:
```
□ Story written with clear goal
□ Acceptance criteria defined
□ Three Amigos review (Dev, QA, Product perspectives)
□ Task breakdown with effort estimates
□ Risks documented
□ Definition of Done agreed
□ User approval obtained (explicit "approved" or "proceed")
```

**If ANY checkbox empty → STOP. Cannot proceed.**

### BANNED BEHAVIORS (Process Violations):

❌ **"Executing now..."** - without showing plan first
❌ **"Team executing..."** - without user approval
❌ **"Let me start by..."** - without task breakdown
❌ **"Quick fix..."** - still needs planning (no exceptions)
❌ **"Just need to..."** - "just" is a red flag
❌ **"This is simple..."** - simple work still needs DoD

### ALWAYS Say Instead:

✅ **"Let me plan this out first..."**
✅ **"Here's my task breakdown: Task 1 (X min), Task 2 (Y min)..."**
✅ **"Definition of Done: [specific criteria]"**
✅ **"Risks I've identified: [list]"**
✅ **"Is this plan approved?"** (explicit question, wait for clear answer)

### Execution Sequence (Mandatory):

1. **Requirements** (5-10 min) - What, Why, Who, When, Done
2. **Story** (10-15 min) - User story + acceptance criteria + story points
3. **Three Amigos** (10-15 min) - Dev, QA, Product perspectives
4. **Task Breakdown** (15-20 min) - Subtasks, estimates, DoD, risks
5. **User Approval** (GATE) - Ask explicitly: "Is this plan approved?"
6. **Execution** (ONLY after approval) - Follow plan, report progress
7. **Retrospective** - What went well, what needs improvement

### Pattern Violations Tracked:

**Historical Issues** (3 violations in one session):
- Violation 1: Started Story 7 without planning (caught by user)
- Violation 2: Said "team executing" on doc automation (caught by user)
- Violation 3: Jumped to protocol creation (caught by user)

**Root Cause**: Implicit process knowledge vs explicit constraints
**Fix**: Codified as NEVER/ALWAYS rules (similar to Writer Agent BANNED_PHRASES)
**Test**: Protocol would have prevented all 3 violations (100% effectiveness)

### Quality Over Speed

**Scrum Master has DUTY to stop work if**:
- Plan incomplete or unclear
- Acceptance criteria missing
- Risks not documented
- DoD not defined
- User approval not explicit

**Even if user says "go ahead"** - Scrum Master must present proper plan first.

See [SCRUM_MASTER_PROTOCOL.md](../docs/SCRUM_MASTER_PROTOCOL.md) for complete workflow, SAFe elements, metrics tracking, and validation checklists.

## Learned Anti-Patterns

*Auto-generated from skills/*.json and docs/ARCHITECTURE_PATTERNS.md on 2026-01-05*

### Defect Prevention Patterns

#### Code Logic

**BUG-021** (medium) - build_process
- **Issue**: README.md badges show stale values - not updated by build process
- **Missed By**: manual_test
- **Prevention**:
  - Created scripts/update_readme_badges.py for automatic updates
  - Will add to pre-commit hook for validation
  - Add CI check to verify badges are current

**BUG-022** (medium) - documentation
- **Issue**: SPRINT.md shows Sprint 2-3 content but Sprint 5 is complete
- **Missed By**: manual_test

#### Integration Error

**BUG-020** (critical) - git_workflow
- **Issue**: GitHub integration broken - issues not auto-closing
- **Missed By**: integration_test
- **Prevention**:
  - Created .git/hooks/commit-msg to validate GitHub close syntax
  - Hook blocks commits with invalid format (bullet lists, missing issue numbers)
  - Sprint 6 Story 1: Final validation and documentation complete

#### Prompt Engineering

**BUG-016** (critical) - writer_agent
- **Issue**: Charts generated but never embedded in articles
- **Missed By**: integration_test
- **Prevention**:
  - Enhanced Writer Agent prompt with explicit chart embedding requirements
  - Added Publication Validator Check #7: Chart Embedding
  - Added agent_reviewer.py validation for Writer Agent outputs

**BUG-028** (critical) - writer_agent
- **Issue**: Writer Agent YAML frontmatter missing opening '---' delimiter
- **Missed By**: integration_test
- **Prevention**:
  - Update Writer Agent prompt to enforce '---' as first line
  - Add Publication Validator check for YAML delimiter presence
  - Production validated: Workflow 20719290473 confirmed fix

#### Requirements Gap

**BUG-017** (medium) - writer_agent
- **Issue**: Duplicate chart display (featured image + embed)
- **Missed By**: visual_qa
- **Prevention**:
  - Removed 'image:' field from YAML frontmatter specification
  - Documented chart embedding pattern: use markdown only, not frontmatter
  - Updated Writer Agent to use single chart embedding method

#### Validation Gap

**BUG-015** (high) - jekyll_layout
- **Issue**: Missing category tag on article page
- **Missed By**: visual_qa
- **Prevention**:
  - Added blog_qa_agent.py Jekyll layout validation
  - Created pre-commit hook for blog structure checks

**BUG-023** (high) - documentation
- **Issue**: README.md badges show stale data - breaks documentation trust
- **Missed By**: manual_test
- **Prevention**:
  - Created separate badge generator scripts (generate_sprint_badge.py, generate_tests_badge.py, generate_coverage_badge.py)
  - Created dedicated validate_badges.py for pre-commit hook
  - Converted all dynamic badges to shields.io endpoint format with JSON files
  - Updated pre-commit hook to validate badge accuracy on every commit

### Content Quality Patterns

#### Agent Architecture

**prompts_as_code** (architectural)
- **Pattern**: Agent behavior defined by large prompt constants at top of files
- **Check**: When modifying agent behavior, edit prompt constants first

**persona_based_voting** (architectural)
- **Pattern**: Editorial board uses weighted persona agents for consensus
- **Check**: New personas must define weight, perspective, and decision criteria

**sequential_agent_orchestration** (architectural)
- **Pattern**: Pipeline stages executed sequentially with data handoffs
- **Check**: Ensure each agent validates its inputs and outputs structured data

#### Chart Integration

**chart_not_embedded** (critical)
- **Pattern**: Chart generated but not embedded in article
- **Check**: agent_reviewer.py checks for ![...](chart_path) in article

**chart_not_referenced** (medium)
- **Pattern**: Chart embedded but not referenced in text
- **Check**: agent_reviewer.py scans for 'As the chart shows' or similar

**duplicate_chart_display** (medium)
- **Pattern**: Chart appears twice (featured image + embedded)
- **Check**: Scan for both 'image:' field and markdown embed

#### Content Quality

**ai_disclosure_compliance** (medium)
- **Pattern**: Posts with AI-generated content must have ai_assisted: true flag
- **Check**: Scan content for AI mentions without disclosure flag

**banned_openings** (critical)
- **Pattern**: Article starts with banned throat-clearing phrases
- **Check**: Scan first paragraph for patterns like 'In today\'s world', 'It\'s no secret'
- **Auto-fix**: Remove opening sentences with banned patterns

**banned_closings** (critical)
- **Pattern**: Article ends with summary or weak closing
- **Check**: Scan last 3 paragraphs for 'In conclusion', 'remains to be seen', summaries
- **Auto-fix**: Replace with definitive prediction or implication

**verification_flags_present** (critical)
- **Pattern**: Article contains [NEEDS SOURCE] or [UNVERIFIED] markers
- **Check**: Grep for verification flags in article body
- **Auto-fix**: Delete unsourced claims or add proper attribution

#### Data Flow

**json_intermediate_format** (architectural)
- **Pattern**: Pipeline stages communicate via JSON files on disk
- **Check**: Validate JSON schema compatibility between producer/consumer

**configurable_output_paths** (architectural)
- **Pattern**: Output paths configurable via environment variables
- **Check**: Provide sensible defaults when env vars not set

#### Dependencies

**centralized_llm_client** (architectural)
- **Pattern**: All agents use Anthropic Claude API via shared client
- **Check**: Create client once, pass to agents - don't create per-request

#### Error Handling

**defensive_json_parsing** (best_practice)
- **Pattern**: Extract JSON from LLM responses with find/rfind before parsing
- **Check**: Always use try/except around json.loads()

**explicit_verification_flags** (architectural)
- **Pattern**: Research agent flags unverifiable claims with [UNVERIFIED]
- **Check**: Never publish content with verification flags

#### Front Matter Validation

**missing_categories_field** (critical)
- **Pattern**: Front matter missing 'categories' field
- **Check**: schema_validator.py enforces required field

**missing_layout_field** (critical)
- **Pattern**: Front matter missing 'layout' field causes page rendering failure
- **Check**: schema_validator.py enforces required field

**generic_titles** (high)
- **Pattern**: Titles use generic patterns like 'Myth vs Reality', 'Ultimate Guide'
- **Check**: schema_validator.py regex patterns detect generic titles

**wrong_date_in_frontmatter** (high)
- **Pattern**: Date in front matter doesn't match today's date
- **Check**: schema_validator.py compares date to expected_date

#### Link Validation

**dead_internal_links** (high)
- **Pattern**: Internal links pointing to non-existent pages
- **Check**: Verify all internal links resolve to actual files

#### Performance

**font_preload_warnings** (low)
- **Pattern**: Font preload resource hints causing warnings
- **Check**: Review preload strategy in layout templates

#### Prompt Engineering

**structured_output_specification** (best_practice)
- **Pattern**: Prompts explicitly define expected JSON output structure
- **Check**: Every agent that returns structured data must specify format

**explicit_constraint_lists** (best_practice)
- **Pattern**: Style constraints explicitly listed as BANNED/FORBIDDEN
- **Check**: Update constraint lists based on editor agent rejections

#### Seo Validation

**missing_page_title** (critical)
- **Pattern**: Empty or missing <title> tag
- **Check**: Verify page layout includes title metadata rendering

**placeholder_urls** (high)
- **Pattern**: URLs containing 'YOUR-', 'REPLACE-', 'PLACEHOLDER'
- **Check**: Scan for template placeholder text in links

#### Sprint Discipline

**work_without_planning** (critical)
- **Pattern**: Starting implementation without sprint story
- **Check**: Before any implementation: (1) Is there an active sprint? (2) Is this work part of a sprint story? (3) Are story points estimated?

**scope_creep_mid_sprint** (high)
- **Pattern**: Adding new stories during active sprint without re-planning
- **Check**: Before adding work: (1) Will this prevent sprint goal completion? (2) Can it wait until next sprint?

**missing_progress_tracking** (medium)
- **Pattern**: Not updating SPRINT.md task checkboxes daily
- **Check**: At end of each work session: (1) Update task checkboxes (2) Add blockers if stuck (3) Update sprint status

**skipped_retrospective** (high)
- **Pattern**: Completing sprint without retrospective
- **Check**: At sprint end: (1) What went well? (2) What could improve? (3) Action items for next sprint?

**work_without_acceptance_criteria** (high)
- **Pattern**: Starting story without clear definition of done
- **Check**: Before implementation: (1) Are acceptance criteria defined? (2) How will we know it's complete? (3) What tests prove it works?

**unestimated_work** (medium)
- **Pattern**: Working on story without story point estimation
- **Check**: Before starting story: (1) Estimated story points? (2) Fits in sprint capacity?

#### Sprint Report Quality

**missing_artifact_links** (high)
- **Pattern**: File mentioned in report but no GitHub link provided
- **Check**: Scan for file paths without accompanying [text](https://github.com/...) links

**broken_commit_references** (high)
- **Pattern**: Commit SHA mentioned but not linked
- **Check**: All commit SHAs must be clickable links to GitHub commits

**unlinked_issues** (medium)
- **Pattern**: Issue numbers mentioned without links
- **Check**: All #XX references must link to GitHub issues

#### Testing Strategy

**continuous_learning_validation** (architectural)
- **Pattern**: Validation agents learn from each run using skills system
- **Check**: Call skills_manager.learn_pattern() when new issues discovered

**human_review_checkpoints** (architectural)
- **Pattern**: Manual review gates between pipeline stages
- **Check**: Never auto-publish - require explicit human approval

### Architectural Patterns

#### Agent Architecture

**Font Preload Warnings** (low)
- **Pattern**: Font preload resource hints causing warnings
- **Check**: Review preload strategy in layout templates

**Prompts As Code** (architectural)
- **Pattern**: Agent behavior defined by large prompt constants at top of files
- **Rationale**: Makes agent logic explicit, versionable, and reviewable
- **Check**: When modifying agent behavior, edit prompt constants first

**Persona Based Voting** (architectural)
- **Pattern**: Editorial board uses weighted persona agents for consensus
- **Rationale**: Simulates diverse stakeholder perspectives with different priorities
- **Check**: New personas must define weight, perspective, and decision criteria

#### Data Flow

**Sequential Agent Orchestration** (architectural)
- **Pattern**: Pipeline stages executed sequentially with data handoffs
- **Rationale**: Each agent specializes in one task, outputs feed next agent
- **Check**: Ensure each agent validates its inputs and outputs structured data

**Json Intermediate Format** (architectural)
- **Pattern**: Pipeline stages communicate via JSON files on disk
- **Rationale**: Enables inspection between stages, supports manual intervention
- **Check**: Validate JSON schema compatibility between producer/consumer

#### Dependencies

**Explicit Verification Flags** (architectural)
- **Pattern**: Research agent flags unverifiable claims with [UNVERIFIED]
- **Rationale**: Maintains credibility, prevents false claims in output
- **Check**: Never publish content with verification flags

#### Error Handling

**Explicit Constraint Lists** (best_practice)
- **Pattern**: Style constraints explicitly listed as BANNED/FORBIDDEN
- **Rationale**: Learned from manual editing cycles - codified editorial lessons
- **Check**: Update constraint lists based on editor agent rejections

**Defensive Json Parsing** (best_practice)
- **Pattern**: Extract JSON from LLM responses with find/rfind before parsing
- **Rationale**: LLMs may wrap JSON in markdown or explanatory text
- **Check**: Always use try/except around json.loads()

#### Performance

**Ai Disclosure Compliance** (medium)
- **Pattern**: Posts with AI-generated content must have ai_assisted: true flag
- **Check**: Scan content for AI mentions without disclosure flag

#### Prompt Engineering

**Configurable Output Paths** (architectural)
- **Pattern**: Output paths configurable via environment variables
- **Rationale**: Supports multiple deployment targets (local, blog repo, CI/CD)
- **Check**: Provide sensible defaults when env vars not set

**Structured Output Specification** (best_practice)
- **Pattern**: Prompts explicitly define expected JSON output structure
- **Rationale**: Reduces parsing errors and improves output consistency
- **Check**: Every agent that returns structured data must specify format

#### Testing Strategy

**Centralized Llm Client** (architectural)
- **Pattern**: All agents use Anthropic Claude API via shared client
- **Rationale**: Consistent model selection, easier rate limiting, unified error handling
- **Check**: Create client once, pass to agents - don't create per-request

**Continuous Learning Validation** (architectural)
- **Pattern**: Validation agents learn from each run using skills system
- **Rationale**: Zero-config improvement, patterns persist across runs
- **Check**: Call skills_manager.learn_pattern() when new issues discovered

**Human Review Checkpoints** (architectural)
- **Pattern**: Manual review gates between pipeline stages
- **Rationale**: Prevents runaway automation, ensures quality
- **Check**: Never auto-publish - require explicit human approval

## Learned Anti-Patterns

*Auto-generated from skills/*.json and docs/ARCHITECTURE_PATTERNS.md on 2026-01-06*

### Defect Prevention Patterns

#### Code Logic

**BUG-021** (medium) - build_process
- **Issue**: README.md badges show stale values - not updated by build process
- **Missed By**: manual_test
- **Prevention**:
  - Created scripts/update_readme_badges.py for automatic updates
  - Will add to pre-commit hook for validation
  - Add CI check to verify badges are current

**BUG-022** (medium) - documentation
- **Issue**: SPRINT.md shows Sprint 2-3 content but Sprint 5 is complete
- **Missed By**: manual_test

#### Integration Error

**BUG-020** (critical) - git_workflow
- **Issue**: GitHub integration broken - issues not auto-closing
- **Missed By**: integration_test
- **Prevention**:
  - Created .git/hooks/commit-msg to validate GitHub close syntax
  - Hook blocks commits with invalid format (bullet lists, missing issue numbers)
  - Sprint 6 Story 1: Final validation and documentation complete

#### Prompt Engineering

**BUG-016** (critical) - writer_agent
- **Issue**: Charts generated but never embedded in articles
- **Missed By**: integration_test
- **Prevention**:
  - Enhanced Writer Agent prompt with explicit chart embedding requirements
  - Added Publication Validator Check #7: Chart Embedding
  - Added agent_reviewer.py validation for Writer Agent outputs

**BUG-028** (critical) - writer_agent
- **Issue**: Writer Agent YAML frontmatter missing opening '---' delimiter
- **Missed By**: integration_test
- **Prevention**:
  - Update Writer Agent prompt to enforce '---' as first line
  - Add Publication Validator check for YAML delimiter presence
  - Production validated: Workflow 20719290473 confirmed fix

#### Requirements Gap

**BUG-017** (medium) - writer_agent
- **Issue**: Duplicate chart display (featured image + embed)
- **Missed By**: visual_qa
- **Prevention**:
  - Removed 'image:' field from YAML frontmatter specification
  - Documented chart embedding pattern: use markdown only, not frontmatter
  - Updated Writer Agent to use single chart embedding method

#### Validation Gap

**BUG-015** (high) - jekyll_layout
- **Issue**: Missing category tag on article page
- **Missed By**: visual_qa
- **Prevention**:
  - Added blog_qa_agent.py Jekyll layout validation
  - Created pre-commit hook for blog structure checks

**BUG-023** (high) - documentation
- **Issue**: README.md badges show stale data - breaks documentation trust
- **Missed By**: manual_test
- **Prevention**:
  - Created separate badge generator scripts (generate_sprint_badge.py, generate_tests_badge.py, generate_coverage_badge.py)
  - Created dedicated validate_badges.py for pre-commit hook
  - Converted all dynamic badges to shields.io endpoint format with JSON files
  - Updated pre-commit hook to validate badge accuracy on every commit

### Content Quality Patterns

#### Agent Architecture

**prompts_as_code** (architectural)
- **Pattern**: Agent behavior defined by large prompt constants at top of files
- **Check**: When modifying agent behavior, edit prompt constants first

**persona_based_voting** (architectural)
- **Pattern**: Editorial board uses weighted persona agents for consensus
- **Check**: New personas must define weight, perspective, and decision criteria

**sequential_agent_orchestration** (architectural)
- **Pattern**: Pipeline stages executed sequentially with data handoffs
- **Check**: Ensure each agent validates its inputs and outputs structured data

#### Chart Integration

**chart_not_embedded** (critical)
- **Pattern**: Chart generated but not embedded in article
- **Check**: agent_reviewer.py checks for ![...](chart_path) in article

**chart_not_referenced** (medium)
- **Pattern**: Chart embedded but not referenced in text
- **Check**: agent_reviewer.py scans for 'As the chart shows' or similar

**duplicate_chart_display** (medium)
- **Pattern**: Chart appears twice (featured image + embedded)
- **Check**: Scan for both 'image:' field and markdown embed

#### Content Quality

**ai_disclosure_compliance** (medium)
- **Pattern**: Posts with AI-generated content must have ai_assisted: true flag
- **Check**: Scan content for AI mentions without disclosure flag

**banned_openings** (critical)
- **Pattern**: Article starts with banned throat-clearing phrases
- **Check**: Scan first paragraph for patterns like 'In today\'s world', 'It\'s no secret'
- **Auto-fix**: Remove opening sentences with banned patterns

**banned_closings** (critical)
- **Pattern**: Article ends with summary or weak closing
- **Check**: Scan last 3 paragraphs for 'In conclusion', 'remains to be seen', summaries
- **Auto-fix**: Replace with definitive prediction or implication

**verification_flags_present** (critical)
- **Pattern**: Article contains [NEEDS SOURCE] or [UNVERIFIED] markers
- **Check**: Grep for verification flags in article body
- **Auto-fix**: Delete unsourced claims or add proper attribution

#### Data Flow

**json_intermediate_format** (architectural)
- **Pattern**: Pipeline stages communicate via JSON files on disk
- **Check**: Validate JSON schema compatibility between producer/consumer

**configurable_output_paths** (architectural)
- **Pattern**: Output paths configurable via environment variables
- **Check**: Provide sensible defaults when env vars not set

#### Dependencies

**centralized_llm_client** (architectural)
- **Pattern**: All agents use Anthropic Claude API via shared client
- **Check**: Create client once, pass to agents - don't create per-request

#### Error Handling

**defensive_json_parsing** (best_practice)
- **Pattern**: Extract JSON from LLM responses with find/rfind before parsing
- **Check**: Always use try/except around json.loads()

**explicit_verification_flags** (architectural)
- **Pattern**: Research agent flags unverifiable claims with [UNVERIFIED]
- **Check**: Never publish content with verification flags

#### Front Matter Validation

**missing_categories_field** (critical)
- **Pattern**: Front matter missing 'categories' field
- **Check**: schema_validator.py enforces required field

**missing_layout_field** (critical)
- **Pattern**: Front matter missing 'layout' field causes page rendering failure
- **Check**: schema_validator.py enforces required field

**generic_titles** (high)
- **Pattern**: Titles use generic patterns like 'Myth vs Reality', 'Ultimate Guide'
- **Check**: schema_validator.py regex patterns detect generic titles

**wrong_date_in_frontmatter** (high)
- **Pattern**: Date in front matter doesn't match today's date
- **Check**: schema_validator.py compares date to expected_date

#### Link Validation

**dead_internal_links** (high)
- **Pattern**: Internal links pointing to non-existent pages
- **Check**: Verify all internal links resolve to actual files

#### Performance

**font_preload_warnings** (low)
- **Pattern**: Font preload resource hints causing warnings
- **Check**: Review preload strategy in layout templates

#### Prompt Engineering

**structured_output_specification** (best_practice)
- **Pattern**: Prompts explicitly define expected JSON output structure
- **Check**: Every agent that returns structured data must specify format

**explicit_constraint_lists** (best_practice)
- **Pattern**: Style constraints explicitly listed as BANNED/FORBIDDEN
- **Check**: Update constraint lists based on editor agent rejections

#### Seo Validation

**missing_page_title** (critical)
- **Pattern**: Empty or missing <title> tag
- **Check**: Verify page layout includes title metadata rendering

**placeholder_urls** (high)
- **Pattern**: URLs containing 'YOUR-', 'REPLACE-', 'PLACEHOLDER'
- **Check**: Scan for template placeholder text in links

#### Sprint Discipline

**work_without_planning** (critical)
- **Pattern**: Starting implementation without sprint story
- **Check**: Before any implementation: (1) Is there an active sprint? (2) Is this work part of a sprint story? (3) Are story points estimated?

**scope_creep_mid_sprint** (high)
- **Pattern**: Adding new stories during active sprint without re-planning
- **Check**: Before adding work: (1) Will this prevent sprint goal completion? (2) Can it wait until next sprint?

**missing_progress_tracking** (medium)
- **Pattern**: Not updating SPRINT.md task checkboxes daily
- **Check**: At end of each work session: (1) Update task checkboxes (2) Add blockers if stuck (3) Update sprint status

**skipped_retrospective** (high)
- **Pattern**: Completing sprint without retrospective
- **Check**: At sprint end: (1) What went well? (2) What could improve? (3) Action items for next sprint?

**work_without_acceptance_criteria** (high)
- **Pattern**: Starting story without clear definition of done
- **Check**: Before implementation: (1) Are acceptance criteria defined? (2) How will we know it's complete? (3) What tests prove it works?

**unestimated_work** (medium)
- **Pattern**: Working on story without story point estimation
- **Check**: Before starting story: (1) Estimated story points? (2) Fits in sprint capacity?

#### Sprint Report Quality

**missing_artifact_links** (high)
- **Pattern**: File mentioned in report but no GitHub link provided
- **Check**: Scan for file paths without accompanying [text](https://github.com/...) links

**broken_commit_references** (high)
- **Pattern**: Commit SHA mentioned but not linked
- **Check**: All commit SHAs must be clickable links to GitHub commits

**unlinked_issues** (medium)
- **Pattern**: Issue numbers mentioned without links
- **Check**: All #XX references must link to GitHub issues

#### Testing Strategy

**continuous_learning_validation** (architectural)
- **Pattern**: Validation agents learn from each run using skills system
- **Check**: Call skills_manager.learn_pattern() when new issues discovered

**human_review_checkpoints** (architectural)
- **Pattern**: Manual review gates between pipeline stages
- **Check**: Never auto-publish - require explicit human approval

### Architectural Patterns

#### Agent Architecture

**Font Preload Warnings** (low)
- **Pattern**: Font preload resource hints causing warnings
- **Check**: Review preload strategy in layout templates

**Prompts As Code** (architectural)
- **Pattern**: Agent behavior defined by large prompt constants at top of files
- **Rationale**: Makes agent logic explicit, versionable, and reviewable
- **Check**: When modifying agent behavior, edit prompt constants first

**Persona Based Voting** (architectural)
- **Pattern**: Editorial board uses weighted persona agents for consensus
- **Rationale**: Simulates diverse stakeholder perspectives with different priorities
- **Check**: New personas must define weight, perspective, and decision criteria

#### Data Flow

**Sequential Agent Orchestration** (architectural)
- **Pattern**: Pipeline stages executed sequentially with data handoffs
- **Rationale**: Each agent specializes in one task, outputs feed next agent
- **Check**: Ensure each agent validates its inputs and outputs structured data

**Json Intermediate Format** (architectural)
- **Pattern**: Pipeline stages communicate via JSON files on disk
- **Rationale**: Enables inspection between stages, supports manual intervention
- **Check**: Validate JSON schema compatibility between producer/consumer

#### Dependencies

**Explicit Verification Flags** (architectural)
- **Pattern**: Research agent flags unverifiable claims with [UNVERIFIED]
- **Rationale**: Maintains credibility, prevents false claims in output
- **Check**: Never publish content with verification flags

#### Error Handling

**Explicit Constraint Lists** (best_practice)
- **Pattern**: Style constraints explicitly listed as BANNED/FORBIDDEN
- **Rationale**: Learned from manual editing cycles - codified editorial lessons
- **Check**: Update constraint lists based on editor agent rejections

**Defensive Json Parsing** (best_practice)
- **Pattern**: Extract JSON from LLM responses with find/rfind before parsing
- **Rationale**: LLMs may wrap JSON in markdown or explanatory text
- **Check**: Always use try/except around json.loads()

#### Performance

**Ai Disclosure Compliance** (medium)
- **Pattern**: Posts with AI-generated content must have ai_assisted: true flag
- **Check**: Scan content for AI mentions without disclosure flag

#### Prompt Engineering

**Configurable Output Paths** (architectural)
- **Pattern**: Output paths configurable via environment variables
- **Rationale**: Supports multiple deployment targets (local, blog repo, CI/CD)
- **Check**: Provide sensible defaults when env vars not set

**Structured Output Specification** (best_practice)
- **Pattern**: Prompts explicitly define expected JSON output structure
- **Rationale**: Reduces parsing errors and improves output consistency
- **Check**: Every agent that returns structured data must specify format

#### Testing Strategy

**Centralized Llm Client** (architectural)
- **Pattern**: All agents use Anthropic Claude API via shared client
- **Rationale**: Consistent model selection, easier rate limiting, unified error handling
- **Check**: Create client once, pass to agents - don't create per-request

**Continuous Learning Validation** (architectural)
- **Pattern**: Validation agents learn from each run using skills system
- **Rationale**: Zero-config improvement, patterns persist across runs
- **Check**: Call skills_manager.learn_pattern() when new issues discovered

**Human Review Checkpoints** (architectural)
- **Pattern**: Manual review gates between pipeline stages
- **Rationale**: Prevents runaway automation, ensures quality
- **Check**: Never auto-publish - require explicit human approval


## Additional Resources

- [SCRUM_MASTER_PROTOCOL.md](../docs/SCRUM_MASTER_PROTOCOL.md): Process discipline and Agile best practices
- [ARCHITECTURE_PATTERNS.md](../docs/ARCHITECTURE_PATTERNS.md): Auto-generated from architecture review
- [CHART_DESIGN_SPEC.md](../docs/CHART_DESIGN_SPEC.md): Visual design rules with examples
- [JEKYLL_EXPERTISE.md](../docs/JEKYLL_EXPERTISE.md): Jekyll integration patterns
- [SKILLS_LEARNING.md](../docs/SKILLS_LEARNING.md): Skills manager documentation
- [CHANGELOG.md](../docs/CHANGELOG.md): Version history and migration notes
