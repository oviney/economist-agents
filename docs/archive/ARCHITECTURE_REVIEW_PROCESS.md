# Architecture Review Process

This document explains how to perform architecture reviews using the self-learning skills system.

## Overview

The architecture review agent uses a **Claude-style skills approach** to:
1. Analyze codebase patterns automatically
2. Learn architectural decisions and document rationale
3. Persist knowledge across reviews
4. Export findings to human-readable documentation

## How It Works

### Self-Learning Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Architecture Review Cycle                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. ANALYZE                                                 │
│     ├─ Scan Python files for patterns                       │
│     ├─ Identify agent architecture (prompts, personas)      │
│     ├─ Map data flow (JSON files, env vars)                 │
│     ├─ Extract prompt engineering practices                 │
│     └─ Detect error handling & dependencies                 │
│                                                             │
│  2. LEARN                                                   │
│     ├─ Create pattern entries in skills DB                  │
│     ├─ Record rationale & implementation details            │
│     ├─ Add quality checks & examples                        │
│     └─ Persist to skills/blog_qa_skills.json                │
│                                                             │
│  3. DOCUMENT                                                │
│     ├─ Export to ARCHITECTURE_PATTERNS.md                   │
│     ├─ Generate human-readable report                       │
│     └─ Update pattern statistics                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Running Reviews

### Full Architecture Review

Analyzes all aspects of the codebase:

```bash
python3 scripts/architecture_review.py --full-review --export-docs
```

**What it analyzes:**
- Agent architecture patterns (prompts, personas, orchestration)
- Data flow between pipeline stages
- Prompt engineering practices
- Error handling strategies
- External dependencies
- Testing and validation approaches

**Output:**
- Console report with pattern counts
- Updated `skills/blog_qa_skills.json`
- Generated `docs/ARCHITECTURE_PATTERNS.md`

### View Learned Patterns

See what the system has learned:

```bash
python3 scripts/architecture_review.py --show-skills
```

**Shows:**
- All learned pattern categories
- Pattern severity levels
- Implementation details
- Quality checks
- Statistics (total runs, patterns learned)

### Focus on Specific Area

(Future capability - not yet implemented)

```bash
python3 scripts/architecture_review.py --focus agent-patterns
python3 scripts/architecture_review.py --focus data-flow
```

## Pattern Categories

### Agent Architecture
**Patterns learned:**
- `prompts_as_code`: System prompts as large constants
- `persona_based_voting`: Weighted consensus from diverse personas
- `sequential_agent_orchestration`: Pipeline with specialized agents

**Why it matters:** Understanding how agents are structured helps when adding new agents or modifying behavior.

### Data Flow
**Patterns learned:**
- `json_intermediate_format`: JSON files between pipeline stages
- `configurable_output_paths`: Environment variable configuration

**Why it matters:** Knowing data handoff points is critical for debugging and extending the pipeline.

### Prompt Engineering
**Patterns learned:**
- `structured_output_specification`: JSON schema in prompts
- `explicit_constraint_lists`: BANNED/FORBIDDEN lists

**Why it matters:** Prompt quality directly impacts output quality. These patterns codify what works.

### Error Handling
**Patterns learned:**
- `defensive_json_parsing`: Extract JSON from markdown-wrapped responses
- `explicit_verification_flags`: [UNVERIFIED] markers for unproven claims

**Why it matters:** Graceful degradation and credibility protection are architectural decisions.

### Dependencies
**Patterns learned:**
- `centralized_llm_client`: Single Anthropic client instance
- `headless_matplotlib_backend`: Agg backend for CI/CD

**Why it matters:** Dependency patterns affect deployment and testing strategies.

### Testing Strategy
**Patterns learned:**
- `continuous_learning_validation`: Skills-based improvement
- `human_review_checkpoints`: Manual gates between stages

**Why it matters:** Testing philosophy shapes the entire development workflow.

## When to Run Reviews

### Required Reviews
- **Before major refactoring**: Document current state
- **After new agent addition**: Learn patterns from new code
- **Pre-release**: Generate updated documentation
- **Onboarding**: Create knowledge base for new developers

### Optional Reviews
- After fixing architectural bugs (to prevent recurrence)
- When patterns feel unclear or inconsistent
- To validate architectural decisions before implementation

## Interpreting Results

### Pattern Severity Levels

**`architectural`**: Core design decisions
- These patterns define the system structure
- Changing them requires coordinated updates
- Examples: agent orchestration, data flow

**`best_practice`**: Recommended approaches
- These patterns improve code quality
- Can be adopted incrementally
- Examples: defensive parsing, structured outputs

**`critical`**: Must-fix issues
- Violations cause system failures
- Examples: missing verification flags

**`high/medium/low`**: Quality concerns
- Ranked by impact on system reliability
- Examples: SEO issues, performance warnings

### Reading the Skills JSON

```json
{
  "id": "prompts_as_code",
  "severity": "architectural",
  "pattern": "Agent behavior defined by large prompt constants",
  "rationale": "Makes agent logic explicit and versionable",
  "check": "Edit prompt constants when modifying behavior",
  "examples": ["economist_agent.py: RESEARCH_AGENT_PROMPT"],
  "learned_from": "Found 9 prompt constants across agent files"
}
```

**Key fields:**
- `id`: Unique pattern identifier
- `pattern`: What the system does
- `rationale`: Why it's designed this way
- `check`: How to verify compliance
- `examples`: Concrete instances in code

## Extending the Review Agent

### Adding New Analysis Functions

1. Add method to `ArchitectureReviewer` class:
   ```python
   def _analyze_new_area(self):
       """Learn patterns from new architectural aspect"""
       # Scan code
       # Detect patterns
       # Call self.skills_manager.learn_pattern(...)
   ```

2. Call from `analyze_all()`:
   ```python
   def analyze_all(self):
       # ... existing analyses
       self._analyze_new_area()
   ```

3. Run review to learn and persist patterns

### Adding Pattern Categories

Skills manager automatically creates categories on first use:

```python
self.skills_manager.learn_pattern(
    "new_category",  # Creates category if doesn't exist
    "pattern_id",
    {
        "severity": "architectural",
        "pattern": "What the pattern does",
        "rationale": "Why it exists",
        "check": "How to verify",
        "learned_from": "Source of knowledge"
    }
)
```

## Integration with AI Agents

### GitHub Copilot

The [.github/copilot-instructions.md](../.github/copilot-instructions.md) references:
- Learned architectural patterns
- Auto-generated ARCHITECTURE_PATTERNS.md
- Pattern categories and their significance

Copilot uses this knowledge when:
- Suggesting code changes
- Answering architecture questions
- Proposing refactorings

### Claude Projects

If using Claude with this codebase:
1. Include `docs/ARCHITECTURE_PATTERNS.md` in project knowledge
2. Reference `skills/blog_qa_skills.json` for pattern details
3. Ask Claude to "review proposed changes against learned patterns"

### Custom AI Workflows

The skills JSON format is AI-friendly:
- Structured data with clear fields
- Rationale explains "why" not just "what"
- Quality checks provide actionable guidance

Example: Ask an AI to "verify this PR complies with patterns in skills/blog_qa_skills.json"

## Continuous Improvement

### Pattern Evolution

As the codebase evolves:
1. Run architecture review after changes
2. New patterns are learned automatically
3. Existing patterns updated with new examples
4. Documentation regenerated with latest knowledge

### Metrics to Track

The skills system tracks:
- Total review runs
- Patterns learned per run
- Pattern updates (when existing patterns evolve)
- Documentation generation timestamps

View with:
```bash
python3 scripts/architecture_review.py --show-skills | grep "Total Runs"
```

### Quality Feedback Loop

```
Code → Review → Learn → Document → Onboard → Code (better)
                ↑                                      ↓
                └──────────── Feedback Loop ──────────┘
```

Each review makes the system smarter. Documentation improves. Future developers benefit from accumulated knowledge.

## Troubleshooting

### "No patterns learned"
- Check that Python files contain expected patterns
- Verify regex patterns in analyzer methods
- Run with verbose logging (add debug prints)

### "Skills file not updating"
- Ensure `skills/` directory exists and is writable
- Check `skills_manager.save()` is called
- Verify no JSON syntax errors in skills file

### "Generated docs missing patterns"
- Some patterns excluded by category filters
- Check `export_to_markdown()` category conditions
- Adjust filters to include desired categories

## Best Practices

1. **Run reviews regularly**: After significant changes
2. **Commit skills file**: Version control tracks pattern evolution
3. **Share documentation**: Point new developers to ARCHITECTURE_PATTERNS.md
4. **Validate assumptions**: If a pattern seems wrong, investigate and update
5. **Extend gradually**: Add new analyzers as new patterns emerge

## Future Enhancements

Potential improvements:
- [ ] Focused reviews (--focus flag implementation)
- [ ] Pattern effectiveness scoring
- [ ] Automatic anti-pattern detection
- [ ] Integration with git history for pattern drift analysis
- [ ] AI-generated pattern suggestions via Anthropic API
- [ ] Pattern validation tests (check code matches documented patterns)

## See Also

- [SKILLS_LEARNING.md](SKILLS_LEARNING.md): General skills system documentation
- [ARCHITECTURE_PATTERNS.md](ARCHITECTURE_PATTERNS.md): Current learned patterns
- [.github/copilot-instructions.md](../.github/copilot-instructions.md): AI agent guidance
