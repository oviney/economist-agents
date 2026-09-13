# Spec — Redesign: the owner's voice is the input, not the gate

**Status:** APPROVED — owner LGTM 2026-09-13, no notes; D3, D6, D7, D8 stand.
Recorded as ADR-0020. Slices 0–6 and 9 landed 2026-09-13; see `BACKLOG.md` B-048 for what is
open (slice 5's live acceptance, D7 blocked on a blog-side rule, D10). Written 2026-09-12 by Fable 5.1 at the
owner's request: *"tell me what's wrong with my thinking, what I'm missing, then refactor or
redesign the whole thing, explaining the reasoning at each decision point."*

**Builds on:** `docs/repo-state-2026-09-10.md` and
`docs/reviews/2026-09-10-fable-complexity-review.md`, which already established that ~58% of
production Python is unreachable from the pipeline and listed ~19,200 lines that can go at
low risk. This spec does not repeat that inventory. It asks the question one level up: is the
system pointed at the right target at all.

Every number below was measured on 2026-09-12; the command is given where it is not obvious.

---

## 1. Diagnosis — what is wrong with the thinking

### 1.1 The product is defined as a style, and the style forbids the only thing you own

The mission statement, in `README.md:3`, is *"Economist-style articles with verified sources."*
`viney.ca/about` says the blog *"distills two decades of software engineering and quality
practice."* Those two sentences are in conflict, and the pipeline resolves it in favour of
the first.

The Economist's voice is an institutional, byline-less voice: it never says "I". The writer
prompt (`stage3_runner.py:136`) enforces exactly that. The result, measured across all 29
published posts:

```bash
for f in temp_blog_repo/_posts/*.md; do grep -cE '\b(I|my|we|our)\b' "$f"; done | sort -n | tail -1
```

| Measure | Value |
|---|---|
| Most first-person words in any published post | 4 |
| Posts with zero | 20 of 29 |
| Owner experiences, clients, or war stories cited across all posts | 0 |

The article the pipeline produces is a well-sourced synthesis of public web material. Read
`2026-08-16-code-coverage-mutation-score-quality.md`: it is genuinely competent. It is also
something any reader can now get from Claude directly in one prompt, and they know it. What
they cannot get anywhere else is what a person who has run quality functions for twenty years
actually saw happen when a board mandated 80% coverage. The pipeline is structurally unable
to produce that sentence, because the only owner input is a topic string, and the style rules
would strip the sentence if the model wrote it.

**The thinking error:** treating "quality" as a property of prose (voice, structure, sourcing)
rather than as a property of the *relationship between author and reader*. A reader of
viney.ca is there for Ouray's judgment. The system was built to keep Ouray's judgment out of
the text, and lets it in only as an approve/reject at the end.

### 1.2 The owner sits at the wrong end of the pipeline

What the owner supplies per article today, in order: a topic sentence → (24 minutes of
machine time; `logs/agent_sdk_costs.jsonl` last row: `stage3_seconds: 1430`) → a hand-drawn
hero → an approve/reject on ~1,000 finished words.

Judgment injected after the draft is the most expensive place to inject it. Editing a finished
argument is harder than stating the argument first. And B-038 (`scripts/html_to_brief.py`)
shows the owner already knows this: he researches by *conversing* with Claude and wants that
conversation fed in. The current architecture labels that conversation "transport, not
judgment." It is the opposite. The conversation is the only place in the whole system where
the owner's judgment exists in writing.

### 1.3 "Quality" is operationalised as rule-compliance measured by regex

| Quality instrument | What it measures |
|---|---|
| `publication_validator.py` — 25 checks | frontmatter shape, word count, heading count, em-dash density, superlatives, banned phrases, ending pattern, references present |
| `article_evals.json` — 5 dimensions, 412 entries | opening_quality, evidence_sourcing, voice_consistency, structure, visual_engagement |
| Reader signal captured | none |

Every instrument scores form. None asks whether a reader learned anything, whether the owner
would stand behind a sentence, or whether anyone read it. GA4 is wired on the blog
(`_config.yml: G-GTFG819MNS`) but the ETL needs a service-account key (constraint #1), so the
loop was never closed — ADR-0007 designed it and it has no callers.

The system has already shown what happens when form-gates are the definition of quality:
B-042. A CRITICAL gate required a chart; the brief had one number; the model invented four
percentages to satisfy the gate. **A blocking gate on form makes the model optimise for the
gate, not the reader.** That is Goodhart's law, and the coverage article the pipeline itself
published explains it better than this paragraph does.

### 1.4 The engineering became the product

| Measure (since 2026-07-01) | Value |
|---|---|
| Commits | 173 |
| Commits whose subject starts with `docs` | 62 (36%) — the 09-10 review counted 68% by diff content |
| Articles published | 5 |
| Production Python, non-archived | ~39,800 lines |
| Of which reachable from the pipeline | ~7,250 |
| Test Python | 48,554 lines (2,791 tests) |
| Markdown files, repo-wide | 376 |
| `BACKLOG.md` | 2,317 lines |

The "second system" (defect tracker, skills-gap analyzer that assigns *Junior/Mid/Senior
hiring levels* to agents, scrum-master protocol, sensor register with proofs-of-teeth,
mypy baseline, docs-truth gate, composite-score audits) is a faithful model of a software
organisation's quality function. It has one person in it and produces five articles a
quarter.

**Why this happened is the useful part.** The owner is a quality-engineering leader. The
system's natural attractor was therefore *quality infrastructure*: every problem got answered
with a gate, a sensor, a tracker, because that is the expertise available. But the thing the
blog is missing — the author's own voice — is not something a gate can produce. The repo
optimises what its author knows how to optimise, and the harder-to-automate asset went
unbuilt.

### 1.5 The throughput model is inverted

The pipeline is sized for volume (topic scout, seven-persona editorial board, dedup index,
A/B scout comparisons). The actual bottleneck is the owner: he draws every hero by hand
(constraint #4, deliberately), reads every packet, approves every post. Cadence is ~one post
per fortnight, which is a fine cadence for a consultant's blog. Nothing upstream of the owner
needs to be fast, and nothing built for volume has been used since July: Stage 1/2 has
produced no published article in the keyless era (09-10 review §6, item 9).

---

## 2. What is missing

1. **The owner's take as a first-class input.** Thesis in his words, two or three things he
   has seen, what he believes that the consensus does not, what would change his mind.
2. **A definition of quality that touches a reader**, keyless. It exists and costs nothing:
   the owner's own rating after publishing, and a monthly glance at the GA4 dashboard in a
   browser (no API, no key).
3. **A through-line.** Topics are picked per article by a synthetic board. A consultant's blog
   is stronger as an argument that develops across posts. Nothing in the system knows what
   the last five posts argued.
4. **Subtraction as a practice.** The repo has a mechanism for adding a gate (`B-043`, "no
   sensor ships without a proof it can fail") and none for retiring one.
5. **A cost model for owner attention.** Machine minutes and nominal dollars are logged;
   owner minutes per article, the scarce resource, are not.

---

## 3. The redesign — decisions and the reasoning behind each

Each decision states the choice, why, the trade-off accepted, and how reversible it is.
Reversibility matters because this spec deletes more than it builds.

### D1 — Invert the input: the pipeline starts from an owner brief, not a topic string

**Decision.** The unit of input becomes `briefs/<slug>.md`, written by the owner (typed, or
dictated to Claude and exported — B-038's transport survives as the import path). Template:

```markdown
# <working title>
## My take          — the thesis, in my words, two or three sentences
## What I've seen   — 2–3 concrete experiences; anonymise clients, keep the specifics
## Where I disagree — with the consensus, the vendor line, or my younger self
## What would change my mind
## Sources I trust on this (optional)
```

Research (`claude_web`) then runs *in service of the take*: find the evidence for it, find the
strongest counter-evidence, find the named cases. The writer is told the thesis and the
experiences are the spine and the research is the supporting steel, not the reverse.

**Why.** The take is the only non-commoditised input the system has. Moving it from the end
(approve/reject of 1,000 words) to the start (200 words before any machine time) is where a
person's judgment is cheapest to apply and most consequential. It also matches how the owner
already works (B-038).

**Trade-off.** The owner must write ~200 words before a run. That is real. It is also the
whole point; a post he could not write 200 words of take for is a post he has nothing to say
about.

**Reversible?** Fully. The brief file is additive; `--topic` can stay as a fallback for a
release or two, then go.

### D2 — Retire "Economist" as the brand; keep the craft rules, drop the institutional ones

**Decision.** The writer's identity becomes *"the editor of a senior practitioner's column"*.
Of the 10 rules in `skills/economist-writing/SKILL.md`, keep the craft: concrete opening,
argue a thesis, no lists in prose, no hedging, cut padding, name names, don't end on a
summary, headings that advance the argument, integrate data. Drop or amend the institutional:
first person is **allowed and expected** where it carries experience; British spelling stays
(the owner is Canadian and the blog already uses it); "dinner-companion wit" becomes
optional rather than mandated. The rename touches the repo name last, if ever.

**Why.** Rule 5 says "name names". Currently the names are Microsoft Research and Google. The
name the reader came for is on the byline. An anonymous institutional voice under a personal
byline reads as exactly what it is.

**Trade-off.** Some of the crispness of the Economist register comes from its impersonality.
Expect early drafts to over-use "I". The polish stage can cap first-person density
(advisory, see D4).

**Reversible?** Yes; it is a prompt and a skill file.

### D3 — Delete Stage 1/2 and the second system; the owner is the editorial board

**Decision.** Remove `flow.py` Stage 1/2 and feeders (topic scout, seven-persona editorial
board, dedup index, GA4/GSC ETL, content intelligence), plus cut items 1–7 from the 09-10
review. This resolves the review's "true fork" (item 9): once D1 is accepted, a topic scout
has nothing to do, because the input is a take, not a topic. Retain `published-topics`'
duplicate check only if it can be one function over `_posts/` titles; otherwise drop it.

**Why.** Seven synthetic personas voting is a simulation of an editorial meeting for a
one-person publication, and its theme-bucket diversity classifier pulls toward "generic
industry topic" — the opposite of D1. It has published nothing since July. Every retained
line costs owner attention; the docs-commit ratio is the invoice.

**Trade-off.** Loses the *option* of autonomous topic discovery. Accepting that: the blog
does not want autonomous topics.

**Reversible?** Git. Tag `pre-redesign-2026-09` before the first deletion.

### D4 — Gates split into "protects the reader" (blocking) and "style opinion" (advisory)

**Decision.** Blocking, kept: stat audit (no number in the text that is not in the brief or
research), reference links resolve, no placeholder or reviewer comment leaks (BUG-065),
Jekyll frontmatter contract, `--mode review` required at deploy. Everything else in the 25
validator checks — em-dash density, superlatives, antithesis scaffold, heading count, word
count ceiling, weak-ending regex, title pattern — becomes an **advisory list in the review
packet**. The 5-dimension `article_evals.json` scorer is deleted.

**Why.** B-042 is the proof: a blocking form-gate manufactured a fabrication. Blocking gates
should encode invariants a reader would be harmed by. Style is the owner's call, and he
reads every packet anyway; a list of findings beside the draft is more useful to him than a
quarantine. This is ADR-0019's principle ("a setpoint is a decision about who decides")
applied consistently: the owner decides style; the machine decides only truth-shaped things.

**Trade-off.** More slop will reach the packet. None will reach the blog without the owner
seeing the finding.

**Reversible?** Yes; any advisory can be promoted back to blocking by moving one entry.

### D5 — Close the quality loop with the owner's own verdict, keyless

**Decision.** After `make publish`, the packet gains a `## Verdict` block the owner fills:
score 1–5, one line on what he would change, one line on what the machine got right. Stored
in `briefs/<slug>.md` under `## Verdict` so brief and outcome live together. The last five
verdicts are injected into the writer prompt as "what the author said about recent drafts".
Monthly, the owner reads the GA4 dashboard in a browser and appends three lines to
`docs/readers.md` (top posts, anything surprising). No API, no key.

**Why.** This replaces two dead mechanisms with one live one: the ChromaDB style memory
(collection count 0 — it has never contributed a sentence) and the ADR-0007 analytics loop
(needs a forbidden key). Five honest sentences from the author beat 412 regex scores.
Deleting ChromaDB also removes the dependency that blocked B-047 (Python 3.14).

**Trade-off.** It relies on the owner doing a two-minute chore per post. If he does not, the
prompt simply has no verdicts, which is today's state.

**Reversible?** Trivially.

### D6 — The harness keeps three gates; the sensors programme is retired

**Decision.** Keep: the `PreToolUse` constraint guard (it enforces constraints #1–#5
computationally, and the SessionStart context). Keep `make ci-local` as ruff + mypy + pytest
+ bandit. Retire: sensor register and proofs-of-teeth, complexity sensor, post-edit sensor,
mypy baseline (fix or `# type: ignore` the residue), destructive-change guard (it protects
files this spec deletes), docs-truth gate (once docs are ~20 files, a dangling-link check is
a 15-line script in `ci-local`, not a sensor with a register entry).

**Why.** B-030…B-035, the harness-engineering set, is 1,072 lines of `BACKLOG.md` — 46% of
the backlog is the second system's own backlog. The sensors protect the second system from
itself. With the second system gone, they have nothing to guard. The constraint guard is
different: it protects the owner's stated constraints from any future session, including this
one, and stays.

**Trade-off.** The docs-truth gate is twelve days old and worked. Retiring it is the
uncomfortable case that proves the rule: a gate's age is not a reason to keep it. **This is
owner-gated** because he built it deliberately; my recommendation is retire.

**Reversible?** Yes, from git, though re-wiring a sensor register is real work.

### D7 — The hero image becomes optional; the deploy gate checks only for leaks

**Decision.** A post whose frontmatter has no `image:` is publishable. The deploy step keeps
refusing an article that still carries the `<!-- HERO IMAGE` reviewer comment (BUG-065), and
keeps refusing a declared `image:` whose file is missing. It stops refusing the *absence* of
a hero. Constraint #4 is untouched: the owner still makes every image that exists.

**Why.** The hero requirement came with the Economist template, not from the reader. The
owner is the slowest stage, and the hero is the slowest thing he does per post. A text post
with a chart he approved (`make art`) is a complete post. When he wants to draw, he draws.

**Trade-off.** The blog's index looks less uniform. **Owner-gated**, because he chose the
current gate; my recommendation is make it optional.

**Reversible?** One condition in `deploy_to_blog.py`.

### D8 — Docs: three living files, the rest is history

**Decision.** Living: `CLAUDE.md` (target ≤120 lines: constraints, the run loop, the
publishing rule), `BACKLOG.md` (open items only; done items become git history), and
`docs/HANDOFF.md`. ADRs stay as the decision record and this spec becomes ADR-0020. Every
other markdown file moves to `docs/archive/` in one commit, untouched, with a one-line index.

**Why.** 376 markdown files for one operator is context flooding, in the sense
`context-engineering` uses: the agent reads *around* the instructions instead of the
instructions. The SessionStart hook already lists finished items as open (B-046) because the
index is too big to be right.

**Trade-off.** Some archived docs will be missed. They are one `git log -S` away.

**Reversible?** `git mv` back.

### D9 — Tests follow the live path only

**Decision.** Keep the tests of the ~8 modules that remain. Target: full suite under 30
seconds, coverage gate 80% on the remaining code with `.coveragerc` omitting nothing (BUG-084:
today it omits the one gate that decides publication). Fix BUG-082 first: no test may touch
`temp_blog_repo/`, `logs/`, or `output/`.

**Why.** 11% of the current suite protects something a reader could notice. A suite that runs
in seconds gets run; one that runs in minutes gets skipped, and a solo operator with no CI is
the person most tempted to skip it.

### D10 — One pipeline module per stage, and a stage is a function

**Decision.** Target shape, ~2,500 lines of production Python:

| File | Job | Lines (est.) | Provenance |
|---|---|---|---|
| `src/pipeline.py` | CLI + orchestration: brief → research → draft → polish → packet | 200 | rewrite of `pipeline.py` (599) |
| `src/brief.py` | load/validate the owner brief; HTML-artifact import | 250 | `html_to_brief.py` + `load_brief_file` |
| `src/research.py` | `claude_web` research in service of the take | 150 | `research/claude_web.py`, as is |
| `src/write.py` | writer prompt + one SDK `query()` | 250 | `stage3_runner.py` (874) |
| `src/polish.py` | stat audit, spelling, frontmatter finalize | 300 | `_shared.py` (1,097) |
| `src/validate.py` | blocking invariants + advisory findings | 400 | `publication_validator.py` (1,497) |
| `src/packet.py` | review packet + verdict block | 150 | `review_packet.py`, as is |
| `src/deploy.py` | `--mode review` / publish | 400 | `deploy_to_blog.py` (874), trimmed |
| `src/art.py` | chart render + embed, on owner-approved spec | 350 | `chart_renderer.py` + `finalise_art.py`, as is |

**Why.** The pipeline is a straight line with no branches the owner uses. A straight line
should read as one. `_shared.py` at 1,097 lines is where every stage's helpers went to hide;
giving each stage its own file makes the reachability question answer itself.

**Trade-off.** A rewrite of `pipeline.py` and `stage3_runner.py` risks regressions in the one
path that works. Mitigation: D3 and D8 (deletions, mechanical) land first; the rewrite lands
last, in slices, each proven by a real run to a review URL.

---

## 4. Not doing

- No new key or paid service, for anything, including analytics. GA4 is read by eye.
- No pipeline-generated image of any kind (constraint #4 stands; D7 only makes the hero optional).
- No LLM judge as a blocking gate. ADR-0018 measured what that costs.
- No multi-agent writer, no crew, no personas. One writer, one prompt, one owner.
- No autonomous topic discovery, scheduling, or cadence targets.
- No re-creation of the sensors programme under another name.
- No rename of the repo in this spec. `economist-agents` can stay a misnomer until the code is small enough that the rename is a morning's work.

---

## 5. Migration plan — slices, each landing green

Order is deletions first (mechanical, low risk, immediately reduces what every later step must
read), then the input inversion, then the rewrite.

| # | Slice | Gate | Owner-gated? |
|---|---|---|---|
| 0 | Tag `pre-redesign-2026-09`. Fix BUG-082 (tests mutate the blog clone). | `ci-local` green; `git -C temp_blog_repo status` clean after tests | no |
| 1 | Delete cut items 1–7 from the 09-10 review (~19k code, ~18k tests); edit `Makefile`, `.coveragerc`, `destructive_change_guard` | `ci-local` green; pipeline runs to a review URL | no |
| 2 | Delete Stage 1/2 + feeders (item 9); `flow.py` goes | same | **yes — D3** |
| 3 | Archive docs (D8); shrink `CLAUDE.md`, `BACKLOG.md` | docs-truth passes or is retired in the same slice | **yes — D6, D8** |
| 4 | Retire sensors programme; `ci-local` = ruff + mypy + pytest + bandit | `ci-local` green | **yes — D6** |
| 5 | `briefs/` + `src/brief.py`; `--brief` becomes the primary input; writer prompt rewritten per D1/D2; `economist-writing` skill amended | one real article from a real owner brief reaches a review URL | no |
| 6 | Validator split (D4); evals scorer and ChromaDB deleted; verdict block (D5) | same article re-run; packet shows advisory list | no |
| 7 | Hero optional (D7) | deploy of a no-hero article to review succeeds; leaked-comment article still refused | **yes — D7** |
| 8 | Stage-per-file rewrite (D10) | three real articles end-to-end, one with chart, one without hero | no |
| 9 | This spec → ADR-0020; README rewritten to ≤80 lines | docs-truth (or its 15-line successor) passes | no |

Each slice is one PR or one commit series on `main`, `ci-local` green, per
`agent-skills:incremental-implementation`. Slice 5 is the one that changes what a reader
sees; it should be the first thing the owner reads in the packet and the last thing he
approves.

## 6. Acceptance for the whole redesign

- A published post contains at least one concrete experience in the owner's first person.
- Production Python ≤ 4,000 lines; test suite < 30 s; `.coveragerc` omits nothing.
- `CLAUDE.md` ≤ 120 lines; `BACKLOG.md` lists only open items; markdown files repo-wide ≤ 40 outside `docs/archive/`.
- The owner's minutes per article are recorded in the packet's verdict block, and the number is falling.
- Constraints #1–#5 hold by construction, enforced by the retained guard.

## 7. Decisions the owner must make before slice 2

Stated as recommendations, not a menu. Each stands unless he says otherwise.

1. **D3** — delete Stage 1/2. Recommendation: yes.
2. **D6** — retire the sensors programme including the docs-truth gate. Recommendation: yes.
3. **D7** — hero optional. Recommendation: yes.
4. **D8** — archive all but three living docs. Recommendation: yes.

An LGTM on this spec with no notes means all four stand.
