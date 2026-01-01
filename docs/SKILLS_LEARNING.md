# Self-Learning Blog QA Agent

The Blog QA Agent uses a **Claude-style skills approach** to learn and improve with each validation run.

## How Skills Work

### 1. Skills Database
Located in `skills/blog_qa_skills.json`, this file stores:
- **Learned patterns**: Common issues detected across runs
- **Validation statistics**: Run count, issues found/fixed
- **Pattern metadata**: Severity, detection methods, origin

### 2. Learning Process
Every time the agent runs:
1. **Applies** existing patterns to detect known issues
2. **Records** new patterns when novel issues are found
3. **Updates** statistics and metadata
4. **Persists** learned knowledge for future runs

### 3. Pattern Categories

**SEO Validation**
- Missing page titles
- Placeholder URLs (YOUR-, REPLACE-)
- Meta tag issues

**Content Quality**
- AI disclosure compliance
- YAML front matter validation
- Editorial standards

**Link Validation**
- Broken internal links
- Dead asset references
- Relative path issues

**Performance**
- Resource loading warnings
- Font preload optimization
- Bundle size concerns

## Usage

### Run with Learning (Default)
```bash
python3 scripts/blog_qa_agent.py --blog-dir /path/to/blog
```

### View Learned Skills
```bash
python3 scripts/blog_qa_agent.py --blog-dir /path/to/blog --show-skills
```

### Run Without Learning
```bash
python3 scripts/blog_qa_agent.py --blog-dir /path/to/blog --learn=false
```

### Validate Single Post
```bash
python3 scripts/blog_qa_agent.py --blog-dir /path/to/blog --post _posts/2025-12-31-article.md
```

## Skills Output Example

```
=== Blog QA Skills Report ===
Last Updated: 2025-12-31

Validation Statistics:
  Total Runs: 4
  Issues Found: 5
  Issues Fixed: 3
  Last Run: 2025-12-31T00:00:00Z

Learned Skills:

  SEO Validation:
    - missing_page_title (critical)
    - placeholder_urls (high)
  
  Content Quality:
    - ai_disclosure_compliance (medium)
```

## Integration

### Pre-commit Hook
The agent runs automatically before each commit with learning enabled, building up pattern knowledge over time.

### GitHub Actions
CI/CD pipeline uses learned patterns to catch issues before deployment.

### Local Development
Run frequently during content creation to:
- Apply latest learned patterns
- Catch issues early
- Improve detection accuracy

## How It Improves

**Run 1**: Detects 3 missing AI disclosure flags
- ✅ Learns: "Check for AI mentions without disclosure"

**Run 2**: Finds placeholder LinkedIn URL
- ✅ Learns: "Scan for YOUR-PROFILE patterns"

**Run 3**: Catches empty page title
- ✅ Learns: "Validate title tag rendering"

**Run 4+**: All previous patterns applied automatically
- 🎯 Faster detection
- 🎯 More comprehensive checks
- 🎯 Better consistency

## Benefits

1. **Continuous Improvement**: Gets smarter with each run
2. **Zero Configuration**: Learns automatically from real issues
3. **Shareable Knowledge**: Skills file can be committed to git
4. **Audit Trail**: Track what patterns were learned when
5. **Performance**: Avoids repeating expensive checks

## Future Enhancements

- [ ] Export skills to human-readable markdown
- [ ] Suggest code fixes based on learned patterns
- [ ] Rank patterns by effectiveness
- [ ] Auto-disable low-value checks
- [ ] Integration with Anthropic API for advanced pattern synthesis

---

This approach mirrors how Claude learns from conversations - building up context and improving responses over time.
