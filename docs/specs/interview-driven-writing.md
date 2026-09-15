# Spec — B-049: Interview-driven writing (position B)

**Status:** APPROVED — owner LGTM 2026-09-15: disclosure kept, "we" counts as first person, no voice samples yet.
**Target repo:** `oviney/blog-gate-mcp`. This file moves there as `SPEC.md` § SPEC 3 in slice 0;
`economist-agents` is retired in the last slice.
**Builds on:** `docs/research/2026-09-15-content-systems-synthesis.md` (and its three threads),
the interview of 2026-09-14, and the owner's decision of 2026-09-15: **position B**.

## Assumptions I'm making

1. **Position B means:** Claude asks, the owner answers, Claude arranges a draft *from the owner's
   transcript sentences* with connective tissue. Claude never originates an opinion. Every
   paragraph carrying first-person or opinion cites the transcript turns it came from.
2. **The published posts are not voice samples.** 20 of 29 contain no first-person word. Voice is
   learned from the interview transcripts themselves, accumulating in `voice/voice-notes.md`, plus
   any writing of his the owner drops into `voice/samples/`.
3. **A disclosure line ships on every post**, one sentence, appended by the workflow, wording
   fixed in this spec. The owner can veto (Open Question 2).
4. **The skill lives beside the gate** in `blog-gate-mcp`, not in the blog repo.
5. **Trace is enforced mechanically as far as it can be** (markers present, turns exist, lexical
   overlap advisory) and semantically by the owner reading the provenance view. A gate cannot
   prove meaning; it can prove the author tagged it and show him what he tagged.
6. **Research is on demand, in-session, keyless** (Claude Code's own WebSearch/WebFetch). No
   research module is ported. The article-reaction trigger fetches the article the same way.
7. **No new binaries.** AI-tell linting extends the validator's existing advisory checks with
   Wikipedia's "signs of AI writing" list rather than adding `vale`.

→ Correct any of these now, or they stand.

## Objective

Publishing on viney.ca becomes *easy but authentic*: the owner talks for about thirty minutes,
reads and edits an arrangement of his own sentences, draws the hero, reads the post on an
unlisted live URL, and publishes. The machinery between him and the page is one Claude Code
skill and one MCP gate. Success is the first three real posts reaching a review URL this way,
each with every opinion traceable to something he said, and the owner rating the process worth
repeating.

**User stories**

- As the owner, I say `/post` with a working title, or `/post --article <url>` after reading
  something I disagree with, and I am interviewed one question at a time until my take, two or
  three things I have seen, one disagreement and what would change my mind are on the table.
- As the owner, I read a brief generated from that transcript and say yes or fix it before any
  drafting happens.
- As the owner, I get a draft in which every paragraph that speaks as me shows me which of my
  answers it came from, and edits are proposed to me, never applied silently.
- As the owner, I can see the claims and numbers I am about to publish before I see the prose.
- As the owner, nothing reaches the blog that fails the gate, and nothing goes live that I have
  not read on the live theme.

## Decisions

**D1 — The transcript is the only source of opinion.** `posts/<slug>/interview.md` is appended
turn by turn as the interview runs (T1, T2, …). It is the raw material and the audit trail. A
draft paragraph that speaks in the first person or asserts a judgement must carry a source
comment `<!-- src: T3 T7 -->` whose turns exist. *Why:* scrollback loss is a documented Claude
Code defect; Semafor's claim-to-quote anchoring is the proven pattern; Willison's rule ("opinions
and 'I' are mine") is the objection this design must answer. *Reversible:* yes; markers are
comments and are stripped at deploy.

**D2 — The brief is generated, not written.** After the stop rule fires, the skill writes
`posts/<slug>/brief.md`: thesis, audience, angle, the incidents, and numbered claims each with
transcript refs. The owner approves it before drafting. *Why:* professional editorial practice
puts a brief between interview and draft; the owner-authored template of B-048 was the step he
would not do. *Reversible:* the template stays as the format of the generated brief.

**D3 — Arrangement, not generation.** The draft skill quotes transcript sentences verbatim where
they already work, adds only connective tissue and structure, and never uses "improve" as an edit
verb. Edits are proposed with explicit scope and accepted per change. *Why:* voice under revision
flattens even when instructed not to; ownership recovers when the writer's own text goes in first
and he visibly edits. *Reversible:* it is a prompt.

**D4 — Gates split as before: blocking protects the reader, advisory informs the owner.**
Blocking (CRITICAL): existing validator criticals; a first-person/opinion paragraph with no
resolving source marker; a number not present in transcript, brief or `research.md`; disclosure
line absent; hero absent; placeholder or reviewer comment present. Advisory: AI-tell phrases,
lexical overlap below threshold between a paragraph and its cited turns, weak ending, word
count. *Why:* B-042 showed a blocking form gate manufactures fabrication; a blocking *provenance*
gate cannot, because its only fix is to cite or delete.

**D5 — Review is consequence-first.** `make ready SLUG=<slug>` writes
`posts/<slug>/review.html`: the claims and numbers first, then each paragraph beside the
transcript turns it cites, then advisory findings, then a word-level diff against the previous
version. The final read is the existing unlisted live-theme URL. *Why:* automation bias is robust
and explanations make it worse; line diffs mislead on prose. *Reversible:* it is a report.

**D6 — Disclosure.** Every post ends with one italic sentence:
*"How this was written: I was interviewed by Claude for about N minutes; the draft arranges my
answers; I edited it; the facts were checked against sources I opened."* N is measured from the
transcript timestamps. *Why:* the one peer-reviewed study finds disclosure erases the reader
penalty; Substack, DEV and AP have all moved to disclosure. *Reversible:* delete the sentence and
the gate rule together.

**D7 — Four things migrate from `economist-agents`; nothing else.** `promote_review.py` and
`make publish`; the superseded-review-draft purge (commit 344d109); `audit_article_stats` as the
number gate; the constraint-guard hook. The writing-craft skill is rewritten, not moved.

**D8 — `economist-agents` is archived** once slice 4's first real post is live: README pointer,
GitHub archive flag. *Ask first* — outward-facing.

## Tech stack

Python 3.13 (the gate repo's pin), `pyyaml`, `pillow`, `matplotlib`, `mcp>=1.29,<2.0`. No new
runtime dependency. `ruff==0.14.10`, `pytest`, `coverage`. Claude Code on the subscription for
the skill; no SDK call in this repo's code.

## Commands

```bash
make install                     # venv + requirements-dev
make test                        # pytest tests/ -q        (floor: 355, never lower)
make lint                        # ruff check + ruff format --check
make coverage                    # suite under coverage, printed
/post <working title>            # in Claude Code: interview → brief → draft   (slice 3)
/post --article <url>            # same, starting from an article he just read
make ready SLUG=<slug>           # gates + review.html                          (slice 2)
make art SLUG=<slug>             # fold the hero (and chart) he made            (exists)
make review SLUG=<slug>          # unlisted noindex URL on the live branch      (exists)
make publish SLUG=<slug>         # promote the reviewed draft to _posts/        (slice 0)
```

## Project structure (target repo, after all slices)

```
.claude/commands/post.md         the /post entry point
.claude/settings.json            PreToolUse constraint guard (ported)
skills/interview/SKILL.md        question classes, stop rule, transcript protocol
skills/arrangement/SKILL.md      drafting-from-transcript rules, edit verbs, craft rules
voice/voice-notes.md             grows one line per post; read by the arrangement skill
voice/samples/                   the owner's own writing, if he adds any
posts/<slug>/interview.md        T-numbered transcript with timestamps (D1)
posts/<slug>/brief.md            generated brief, owner-approved (D2)
posts/<slug>/research.md         facts with URLs gathered on demand
posts/<slug>/draft.v1.md …       arrangement drafts with <!-- src: --> markers
posts/<slug>/review.html         consequence-first packet (D5)
output/posts/<slug>.md           what `make art` / `make review` already consume
scripts/provenance.py            parse, verify, strip markers; overlap score
scripts/publication_validator.py + provenance, number and disclosure checks
scripts/promote_review.py        ported; `make publish`
scripts/stat_audit.py            `audit_article_stats` ported
tests/test_provenance*.py, tests/test_stat_audit.py, tests/test_promote_review*.py
```

## Code style

Type hints and docstrings mandatory; `logger` not `print`; `orjson` not `json` where JSON is
touched; mock every network boundary. The gate repo's ruff config governs. One example of the
shape expected in `scripts/provenance.py`:

```python
@dataclass(frozen=True)
class Paragraph:
    """One draft paragraph and the transcript turns it cites."""

    index: int
    text: str
    turns: tuple[str, ...]  # e.g. ("T3", "T7"); empty when the paragraph cites nothing


def unresolved_turns(paragraphs: Sequence[Paragraph], transcript: Mapping[str, str]) -> list[str]:
    """Return every cited turn id that does not exist in the transcript.

    An empty list is a passing check; the caller decides severity.
    """
    return [t for p in paragraphs for t in p.turns if t not in transcript]
```

## Testing strategy

`pytest`, tests beside the existing suite under `tests/`. TDD for everything with behaviour:
red before green, the failing reason observed. Unit tests for `provenance.py`, the three new
validator checks and the ported audit; a CLI-parity test that `make ready` and the MCP validator
tool give the same verdict on the same file; the existing "pushes nothing" witness re-run against
an article failing each new gate. Coverage stays at or above the current report. The skill
(prompt) is verified by a dry run on a fake topic whose transcript, brief and draft pass the
slice-1 gates, and by the live acceptance in slice 4.

## Boundaries

- **Always:** `make lint && make test` before every commit; one slice per commit; keep the
  355-test floor; provenance markers stripped before anything is pushed; `--mode review` first.
- **Ask first:** any new dependency or binary; any change to the validator's CRITICAL set beyond
  D4; archiving `economist-agents` on GitHub (D8); changing the disclosure wording (D6); any
  edit to the blog repo.
- **Never:** a key, a paid service, a model call from repo code, a second deploy path, an image
  the owner did not make, a topic-in/post-out mode, a persona prompt, an editorial score, an
  autocomplete, publishing without the live read.

## Slices (dependency-ordered; each lands on its own green commit)

- **S0 — Migrate the four (D7).** `promote_review.py` + `make publish`; purge fix into
  `deploy_review`; `stat_audit.py` + tests; constraint hook into `.claude/settings.json`. This
  spec copied in as SPEC 3. *Verify:* ported tests pass; `make publish` dry-run on a fixture.
- **S1 — Provenance and gates (D1, D4, D6).** `provenance.py`; validator checks: unmarked
  first-person paragraph, unresolved turn, unsourced number, missing disclosure; markers
  stripped in `deploy_review`/`deploy`. *Verify:* each check observed red then green; the
  "pushes nothing" witness on each failing case.
- **S2 — `make ready` (D5).** `review.html`: claims first, paragraph-beside-turns, advisory
  list, word-level diff vs previous version. *Verify:* renders for a fixture with two versions;
  no network; validator parity test.
- **S3 — The skill and command (D2, D3).** `/post`, `skills/interview`, `skills/arrangement`,
  `voice/voice-notes.md`. *Verify:* dry run on a fake topic produces files that pass S1 and S2.
- **S4 — Live acceptance (owner-run).** One real post from a real interview to a review URL,
  read live, verdict in `voice/voice-notes.md`; then a second and a third. *Verify:* three
  posts live; owner minutes per post recorded.
- **S5 — Retire `economist-agents` (D8).** README pointer, archive flag, hand-off. *Ask first.*

## Success criteria

- `/post` to review URL in one sitting, under 90 minutes of owner time, measured on S4's posts.
- Every first-person paragraph in the three S4 posts carries resolving markers; zero
  unsourced numbers; the gate refused at least one draft during S4 for a real reason.
- Disclosure sentence present on all three; hero drawn by the owner on all three.
- `make test` ≥ 355 and green; `make lint` clean; coverage not below the pre-S0 report.
- Exactly one deploy implementation; the MCP route still cannot bypass the validator.
- Owner's verdict after post three: worth repeating (his words, in the notes file).

## Not doing

Topic scouting, editorial board, research pipeline, stage runners, deep research, editorial
scoring, ChromaDB, style memory, persona prompts, brand-voice profiles, SEO gates, autocomplete,
multi-agent orchestration, Spiral or any paid tool, voice recording (a local Whisper tool can be
added later if he wants to talk instead of type), a hero-optional mode (the blog's own build
refuses one; stays owner-gated on the blog side).

## Open questions

All three resolved by the owner on 2026-09-15:

1. **Voice samples:** none yet. `voice/samples/` starts empty; voice notes grow from transcripts.
2. **Disclosure (D6):** kept as worded.
3. **"We":** counts as first person for the provenance gate.

## Errata

*(none yet)*
