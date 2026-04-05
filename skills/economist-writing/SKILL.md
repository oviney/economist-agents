# Economist Writing Style Skill

## Purpose
Define the writing standard for every article produced by the content
pipeline.  This skill is the definitive reference for the Stage 3 Writer
Agent, the Stage 4 Editorial Reviewer, and the Article Evaluator.  Every
article must meet these standards before publication.

## Reference
Study The Economist's actual articles for voice, structure, and argument
style.  The gold standard is editorial prose that combines data-driven
reporting with sharp, opinionated analysis delivered in a confident,
conversational tone.

## The 10 Rules

### 1. Open with a striking, concrete claim
**Do:** "A system designed to predict the most likely next word in a
sentence can also write good computer code."
**Don't:** "The arrival of AI-powered test generation tools promised a
revolution."

The first sentence must make the reader stop.  Use a specific fact,
a surprising statistic, or a provocative assertion.  Never start with
abstract nouns ("The emergence of", "The arrival of", "The rise of").

**Banned opening patterns:**
- "In today's world"
- "It's no secret"
- "The arrival/emergence/rise of"
- "When it comes to"
- "Amidst"
- Any sentence starting with "The" followed by an abstract noun

### 2. Argue a thesis, not a topic
Every article must have a **specific, debatable argument** stated in the
first two paragraphs.  "AI tools overpromise" is a topic.  "AI test
generators are making maintenance worse, not better, because they
optimise for coverage metrics that don't correlate with code quality"
is a thesis.

Every subsequent section must advance this argument.  If a paragraph
doesn't serve the thesis, cut it.

### 3. Never use numbered or bulleted lists in prose
Lists belong in infographics, not editorial writing.  Each point must
be argued in its own paragraph with transitions that connect ideas.

**Banned in article body** (outside References section):
- Numbered lists (1., 2., 3.)
- Bulleted lists (-, *)
- "The following steps" / "Here are N ways"

### 4. Write with authority, not hedging
**Do:** "Companies are racing to de-weird AI."
**Don't:** "It would be misguided to dismiss" / "One might imagine"

**Banned hedging phrases:**
- "it would be misguided"
- "one might"
- "it is worth noting"
- "it should be noted"
- "it is important to"
- "it is not a minor footnote"
- "further complicating matters"
- "invites closer scrutiny"
- "in practical terms"

### 5. Name names — use real companies and people
Every article must include at least 2 named companies or individuals
with specific anecdotes.  "Organisations" and "professionals" are too
generic.  "Microsoft's testing team found..." is specific.  "A 2023
survey of professionals..." is vague.

**Banned generic attributions:**
- "organisations"  (use the company name)
- "professionals" (use the role: "engineers at Google")
- "studies show" (name the study)
- "experts say" (name the expert)
- "research indicates" (cite the specific paper)

### 6. Cut ruthlessly — no padding
Every sentence must earn its place.  Remove:
- Throat-clearing ("It goes without saying")
- Redundant attribution ("As mentioned earlier")
- Weak intensifiers ("very", "quite", "rather", "fairly")
- Sentences starting with "This" or "These" that merely restate the
  previous point

Target: zero wasted sentences.  If you can remove a sentence without
losing meaning, remove it.

### 7. End with a vivid prediction or provocation
**Do:** "You don't navigate strange territory by pretending your old
maps still work."
**Don't:** "Their success will rest on rigorous evaluation and
tempered expectations."

The ending must leave the reader thinking.  Use a metaphor, a
prediction, or a provocative question.  Never summarise.

**Banned closing patterns:**
- "will rest on" / "depends on" / "the key is"
- "In conclusion" / "To summarise"
- "Only time will tell"
- "remains to be seen"
- Any sentence that restates the thesis without adding new insight

### 8. Use 3-4 headings maximum
Let the argument breathe.  A heading every 94 words is a blog post,
not an essay.  Target one heading per 250-350 words.  Maximum 4
headings for a 1000-word article.

More importantly, headings should be **noun phrases that advance the
argument**, not questions or descriptions:
**Do:** "The maintenance trap"
**Don't:** "A Closer Look at the Disconnect"
**Don't:** "What Can Be Done?"

### 9. Integrate data, don't catalogue it
**Do:** "Half of automatically generated test scripts need manual
adjustment after minor refactoring, according to Microsoft Research."
**Don't:** "Microsoft Research, in its 2023 technical report, noted
that half of automatically generated test scripts necessitated manual
adjustment."

Never start a sentence with a source name followed by a reporting
verb (found, noted, highlighted, revealed, reported).  Make the claim
first, attribute second.

### 10. Title must be provocative and memorable
**Do:** "The IT department: Where AI goes to die"
**Don't:** "Why AI Test Generation Tools Overpromise on Maintenance Savings"

Use a colon to add a surprising twist.  Titles should make the reader
curious, not tell them the conclusion.

**Banned title patterns:**
- Starting with "Why" or "How"
- Starting with "The Impact of" or "The Role of"
- Longer than 10 words without a colon or twist
- Purely descriptive (tells you the topic, not the argument)

## Voice Reference

The Economist voice is:
- **Confident** — states opinions as observations, not suggestions
- **Witty** — dry humour, understated irony, unexpected metaphors
- **British** — organisation, analyse, colour, favour
- **Active** — "Companies are racing" not "it is being observed that"
- **Conversational** — reads like a brilliant dinner companion, not a textbook
- **Precise** — every word chosen deliberately, no filler

## Anti-Patterns (Common Pipeline Failures)

These patterns appear frequently in generated articles and must be
eliminated:

1. **Literature review structure** — cataloguing findings source by
   source instead of arguing a point
2. **Listicle disguised as prose** — numbered recommendations,
   "5 ways to..." format
3. **Abstract opening** — starting with the concept rather than a
   concrete hook
4. **Reverent data tone** — treating every statistic as sacred instead
   of wielding it as evidence for an argument
5. **Summary ending** — restating the thesis in the conclusion
6. **Excessive headings** — fragmenting the argument into disconnected
   sections
7. **Generic attribution** — "organisations" instead of named companies

## Integration Points

- **Stage 3 Writer Agent** — primary consumer of this skill
- **Stage 4 Editorial Reviewer** — evaluates against these rules
- **Article Evaluator** — scores opening, voice, structure against these standards
- **Deterministic Polish** — strips banned phrases and patterns listed here
- **Editorial Judge** — post-deployment check against writing quality
