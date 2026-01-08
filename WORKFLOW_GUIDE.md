# Full Blog Post Workflow Guide

## Quick Start

Generate a complete blog post with all validation stages:

```bash
# Basic usage (uses queued topic)
./run_full_workflow.sh

# Specify custom topic
TOPIC="The Future of AI Testing" ./run_full_workflow.sh

# Full configuration
TOPIC="Performance Testing at Scale" \
TALKING_POINTS="cost optimization, cloud infrastructure, metrics" \
CATEGORY="performance-engineering" \
BLOG_DIR="../economist-blog-v5" \
./run_full_workflow.sh
```

## What This Script Does

The workflow orchestrates **three (optionally four) critical stages**:

### Stage 0: Topic Discovery (Optional) 🔭
**Agent:** Topic Scout Agent (`scripts/topic_scout.py`)
**Trigger:** When `AUTO_DISCOVER=true` and no `TOPIC` specified

Autonomous topic discovery scanning the QE landscape:
1. **Trend Research** → Monitors vendors, conferences, communities, job postings, VC activity
2. **Topic Evaluation** → Scores topics on 5 criteria (total 25 points):
   - Timeliness (recent relevance)
   - Data Availability (verifiable sources)
   - Contrarian Potential (unique angle)
   - Audience Fit (senior QE leaders)
   - Economist Style Fit (data-driven narrative)
3. **Queue Update** → Saves 5 ranked topics to `content_queue.json`
4. **Export** → Sets `TOPIC` and `TALKING_POINTS` for Stage 1

**Output:** `content_queue.json` with ranked topics, top topic exported as `TOPIC`
**Duration:** ~30-60 seconds (2 LLM calls)

### Stage 1: Blog Post Generation 🎯
**Agent:** Scrum Master (`scripts/economist_agent.py`)

Coordinates the complete content pipeline:
1. **Research Agent** → Gathers data, verifies sources (86.3% verification rate)
2. **Writer Agent** → Generates 800-1200 word article (60% first-pass validation)
3. **Editor Agent** → 5-gate quality validation (95.2% pass rate)
4. **Graphics Agent** → Creates Economist-style charts
5. **Visual QA Agent** → Two-stage chart validation
6. **Publication Validator** → Final 8-check quality gate

**Output:** Article in `output/YYYY-MM-DD-article-title.md` with charts in `output/charts/`

### Stage 2: Deployment Validation 📋
**Agent:** Blog QA Agent (`scripts/blog_qa_agent.py`)

Jekyll-specific deployment checks:
- ✅ YAML front matter validation (layout, title, date)
- ✅ Layout file existence
- ✅ Jekyll plugin configuration (jekyll-seo-tag, etc.)
- ✅ Broken link detection
- ✅ AI disclosure compliance
- ✅ Performance hints (font preload)
- **🧠 Self-Learning:** Remembers patterns from each run

**Output:** Validation report + learned patterns in `skills/blog_qa_skills.json`

### Stage 3: End-to-End Validation ✅
**Agent:** Quality Enforcer (`pytest scripts/test_agent_integration.py`)

Integration test suite (9 tests):
- ✅ `test_happy_path_end_to_end` - Complete- leave empty to use queued topic from content_queue.json |
| `TALKING_POINTS` | "" | Key points to cover (comma-separated) |
| `CATEGORY` | quality-engineering | Article category |
| `OUTPUT_DIR` | output | Where to save generated article |
| `BLOG_DIR` | ../economist-blog-v5 | Jekyll blog directory for validation |
| `AUTO_DISCOVER` | false | Set to `true` to run Topic Scout Agent for automatic topic discovery
- ✅ `test_agent_data_flow` - Research → Writer handoff
- ✅ `test_error_handling_graceful_degradation` - Failure handling
- ✅ `test_bug_016_pattern_prevented` - Defect prevention (chart embedding)
- Option 1: Automatic topic discovery (recommended):**
```bash
AUTO_DISCOVER=true ./run_full_workflow.sh
```

**Option 2: Use pre-queued topic (manual discovery):**
```bash
# First, run Topic Scout separately to populate queue
python3 scripts/topic_scout.py

# Then run workflow - it uses top-scored topic from content_queue.json
./run_full_workflow.sh
```

**Option 3: Specify your own
### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TOPIC` | (queued) | Article topic/title |
| `TALKING_POINTS` | "" | Key points to cover (comma-separated) |
| `CATEGORY` | quality-engineering | Article category |
| `OUTPUT_DIR` | output | Where to save generated article |
| `BLOG_DIR` | ../economist-blog-v5 | Jekyll blog directory for validation |
| `ANTHROPIC_API_KEY` | (required) | Claude API key for LLM calls |

### Example Configurations

**Minimal (queued topic):**
```bash
./run_full_workflow.sh
```

**Custom topic:**
```bash
TOPIC="Test Automation Economics" ./run_full_workflow.sh
```

**Full control:**
```bash
TOPIC="Shift-Left Testing Strategies" \
TALKING_POINTS="DevOps integration, early bug detection, cost savings" \
CATEGORY="devops" \
OUTPUT_DIR="custom_output" \
BLOG_DIR="/path/to/blog" \
./run_full_workflow.sh
```

**Skip blog validation (no Jekyll blog):**
```bash
BLOG_DIR="" ./run_full_workflow.sh
```

## Quality Gates

The workflow enforces **multiple quality gates** to ensure publication-ready content:

| Gate | Enforcer | Criteria | Action on Failure |
|------|----------|----------|-------------------|
| **Self-Validation** | Writer Agent | 60% checks pass | Auto-regenerate |
| **5-Gate Review** | Editor Agent | 95.2% pass rate | Reject draft |
| **Chart Quality** | Visual QA | Zone boundaries, colors | Flag for review |
| **Publication** | Validator | 8 critical checks | Quarantine to `output/quarantine/` |
| **Deployment** | Blog QA Agent | Jekyll structure | Fail validation |
| **Integration** | Quality Enforcer | 9 tests pass | Block deployment |

## Output Structure

```
output/
├── 2026-01-04-article-title.md          # Generated article
├── 2026-01-04-article-title-review.md   # Editorial review
└── charts/
    └── article-title.png                # Generated chart

# If blog validation enabled:
../economist-blog-v5/
└── _posts/
    └── 2026-01-04-article-title.md      # Copied for validation

# If validation fails:
output/quarantine/
├── 2026-01-04-article-title.md
└── 2026-01-04-article-title-VALIDATION-FAILED.txt
```

## Success Criteria

The workflow succeeds when **all stages pass**:

1. ✅ **Article Generated**
   - 800-1200 words
   - British spelling throughout
   - Chart embedded (if chart_data provided)
   - YAML front matter correct
   - No [NEEDS SOURCE] or [UNVERIFIED] flags

2. ✅ **Deployment Valid**
   - YAML structure correct
   - Layout file exists
   - No broken links
   - No placeholder text
   - Jekyll plugins configured

3. ✅ **Tests Pass**
   - 9/9 integration tests green
   - Agent coordination working
   - Quality gates operational
   - Defect patterns prevented

## Troubleshooting

### "Blog post generation failed"
- **Check:** `ANTHROPIC_API_KEY` environment variable set
- **Check:** Internet connection (LLM API calls)
- **Check:** Virtual environment activated (`.venv/bin/activate`)

### "Blog QA validation failed"
- **Review:** Validation errors in output
- **Check:** Blog directory path correct (`BLOG_DIR`)
- **Check:** Jekyll `_posts/` directory exists
- **View:** Learned patterns with `--show-skills`

### "Integration tests failed"
- **Run:** Individual tests with `-k` flag: `pytest -k test_name`
- **Check:** Mock setup issues (common for LLM clients)
- **Review:** `TEST_RESULTS.md` for known issues

### "No article found in output"
- **Check:** Publication Validator quarantined article (see `output/quarantine/`)
- **Review:** Quarantine report: `*-VALIDATION-FAILED.txt`
- **Fix:** Address validation issues and regenerate

## Advanced Usage

### Run Individual Stages

**Stage 1 only (generate):**
```bash
python3 scripts/economist_agent.py
```

**Stage 2 only (validate deployment):**
```bash
python3 scripts/blog_qa_agent.py --blog-dir ../economist-blog-v5 --post output/article.md
```

**Stage 3 only (E2E tests):**
```bash
pytest scripts/test_agent_integration.py -v
```

### Interactive Mode

Enable human review gates between stages:
```bash
python3 scripts/economist_agent.py --interactive
```

### Custom Output Directory

Point to Jekyll blog for direct publishing:
```bash
OUTPUT_DIR="../economist-blog-v5/_posts" ./run_full_workflow.sh
```

### Batch Generation

Generate multiple articles from topic queue:
```bash
for i in {1..5}; do
    ./run_full_workflow.sh
done
```

## Metrics & Monitoring

The workflow tracks comprehensive quality metrics:

### Agent Performance
- **Research Agent:** 86.3% verification rate
- **Writer Agent:** 60% first-pass validation, 80% clean draft rate
- **Editor Agent:** 95.2% gate pass rate
- **Graphics Agent:** 88.9% Visual QA pass, 0.1 avg zone violations

### Quality Outcomes
- **Publication Success:** Articles passing all 8 validator checks
- **Defect Prevention:** 83% coverage (5/6 historical bugs preventable)
- **Test Effectiveness:** 9/9 integration tests validating production readiness

### Self-Learning
- **Blog QA Skills:** Patterns learned from each validation run
- **Defect Prevention:** Rules extracted from RCA of historical bugs

## Integration with CI/CD

### GitHub Actions

Add to `.github/workflows/generate-post.yml`:
```yaml
name: Generate Blog Post
on:
  workflow_dispatch:
    inputs:
      topic:
        description: 'Article topic'
        required: true

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: |
          TOPIC="${{ github.event.inputs.topic }}" \
          ANTHROPIC_API_KEY="${{ secrets.ANTHROPIC_API_KEY }}" \
          ./run_full_workflow.sh
      - uses: actions/upload-artifact@v3
        with:
          name: generated-post
          path: output/*.md
```

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Run Blog QA validation before allowing commits
python3 scripts/blog_qa_agent.py --blog-dir . --learn
```

## See Also

- [SCRUM_MASTER_PROTOCOL.md](docs/SCRUM_MASTER_PROTOCOL.md) - Process discipline
- [QUALITY_SYSTEM_SUMMARY.md](docs/QUALITY_SYSTEM_SUMMARY.md) - Quality gates overview
- [AGENT_QUALITY_STANDARDS.md](docs/AGENT_QUALITY_STANDARDS.md) - Self-validation patterns
- [TEST_RESULTS.md](TEST_RESULTS.md) - Integration test suite details
- [SPRINT_9_QUALITY_REPORT.md](docs/SPRINT_9_QUALITY_REPORT.md) - Quality metrics analysis
