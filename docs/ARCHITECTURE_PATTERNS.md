# Architectural Patterns (Learned)

This document is auto-generated from architecture review agent.
Last updated: 2025-12-31T23:49:59.116402


## Content Quality

### Ai Disclosure Compliance

**Pattern:** Posts with AI-generated content must have ai_assisted: true flag

**Quality Check:** Scan content for AI mentions without disclosure flag

*Severity: medium*


## Performance

### Font Preload Warnings

**Pattern:** Font preload resource hints causing warnings

**Quality Check:** Review preload strategy in layout templates

*Severity: low*


## Agent Architecture

### Prompts As Code

**Pattern:** Agent behavior defined by large prompt constants at top of files

**Rationale:** Makes agent logic explicit, versionable, and reviewable

**Quality Check:** When modifying agent behavior, edit prompt constants first

**Examples:**
- topic_scout.py: SCOUT_AGENT_PROMPT
- topic_scout.py: TREND_RESEARCH_PROMPT
- economist_agent.py: RESEARCH_AGENT_PROMPT

*Severity: architectural*

### Persona Based Voting

**Pattern:** Editorial board uses weighted persona agents for consensus

**Rationale:** Simulates diverse stakeholder perspectives with different priorities

**Implementation:** Each persona has explicit 'what makes you click/scroll past' criteria

**Quality Check:** New personas must define weight, perspective, and decision criteria

*Severity: architectural*

### Sequential Agent Orchestration

**Pattern:** Pipeline stages executed sequentially with data handoffs

**Rationale:** Each agent specializes in one task, outputs feed next agent

**Quality Check:** Ensure each agent validates its inputs and outputs structured data

*Severity: architectural*


## Data Flow

### Json Intermediate Format

**Pattern:** Pipeline stages communicate via JSON files on disk

**Rationale:** Enables inspection between stages, supports manual intervention

**Quality Check:** Validate JSON schema compatibility between producer/consumer

*Severity: architectural*

### Configurable Output Paths

**Pattern:** Output paths configurable via environment variables

**Rationale:** Supports multiple deployment targets (local, blog repo, CI/CD)

**Quality Check:** Provide sensible defaults when env vars not set

*Severity: architectural*


## Prompt Engineering

### Structured Output Specification

**Pattern:** Prompts explicitly define expected JSON output structure

**Rationale:** Reduces parsing errors and improves output consistency

**Implementation:** Include example JSON schema in system prompt

**Quality Check:** Every agent that returns structured data must specify format

*Severity: best_practice*

### Explicit Constraint Lists

**Pattern:** Style constraints explicitly listed as BANNED/FORBIDDEN

**Rationale:** Learned from manual editing cycles - codified editorial lessons

**Quality Check:** Update constraint lists based on editor agent rejections

**Examples:**
- BANNED OPENINGS
- BANNED PHRASES
- FORBIDDEN CLOSINGS

*Severity: best_practice*


## Error Handling

### Defensive Json Parsing

**Pattern:** Extract JSON from LLM responses with find/rfind before parsing

**Rationale:** LLMs may wrap JSON in markdown or explanatory text

**Implementation:** Find first '{' and last '}', parse substring

**Quality Check:** Always use try/except around json.loads()

*Severity: best_practice*

### Explicit Verification Flags

**Pattern:** Research agent flags unverifiable claims with [UNVERIFIED]

**Rationale:** Maintains credibility, prevents false claims in output

**Quality Check:** Never publish content with verification flags

*Severity: architectural*


## Dependencies

### Centralized Llm Client

**Pattern:** All agents use Anthropic Claude API via shared client

**Rationale:** Consistent model selection, easier rate limiting, unified error handling

**Quality Check:** Create client once, pass to agents - don't create per-request

*Severity: architectural*


## Testing Strategy

### Continuous Learning Validation

**Pattern:** Validation agents learn from each run using skills system

**Rationale:** Zero-config improvement, patterns persist across runs

**Implementation:** SkillsManager stores patterns in skills/*.json

**Quality Check:** Call skills_manager.learn_pattern() when new issues discovered

*Severity: architectural*

### Human Review Checkpoints

**Pattern:** Manual review gates between pipeline stages

**Rationale:** Prevents runaway automation, ensures quality

**Quality Check:** Never auto-publish - require explicit human approval

*Severity: architectural*
