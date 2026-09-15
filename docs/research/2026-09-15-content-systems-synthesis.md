# How the best content systems are designed in 2026, and what that means for our build

**Synthesis of three research threads run 2026-09-15**, before any spec for the interview-driven
workflow. The threads, each with full sources and a "could not verify" list:

- `2026-09-15-market-content-generation.md` — products, market direction, practitioner positions
- `2026-09-15-ux-ai-writing-interfaces.md` — interaction patterns, HCI evidence, terminal limits
- `2026-09-15-workflow-blog-content.md` — how solo technical writers work, editorial craft, failures

Context: the owner's stated intent (2026-09-14) is "make the work easy, but authentic", with a
conversation as the input — Claude interviews him, or interviews him about an article he just
read. Constraints unchanged: no keys, no paid services, Claude subscription only, he draws every
image, nothing reaches the blog unvalidated.

---

## 1. Seven findings that should shape the design

**1. Nobody sells what we are building, and the closest thing confirms the shape.** No product
interviews the author first for a blog post except Spiral (Every), which asks "what you're
actually trying to say" before drafting, shows three drafts to choose between, learns voice from
samples, and exposes itself over MCP to Claude Code. It costs $15/mo and is a third-party service,
so it is out of scope, but it is independent evidence that interview-first is the right ordering.
Everything else on the market is either an enterprise brand-voice layer over generated text
(Jasper, Writer, Typeface, HubSpot) or a quiet editor with a completion key (Lex). The two most
starred open-source Claude writing skills, at 33.7k and 15.2k stars, exist to *remove* AI tells
from text. That is where the pain is.

**2. The writers the owner admires draw a hard line at opinions.** Willison: "if text expresses
opinions or has 'I' pronouns attached to it then it's written by me." Orosz: zero AI, Grammarly
off. Larson: "either it isn't a book worth writing or he is the wrong author." Majors: a "violent
disgust reflex" at AI in relational text. None of them describes an interview-to-draft workflow.
Our design sits between their position and Spiral's, and it has to answer their objection
explicitly or it will produce exactly the text they say readers can smell.

**3. LLM revision flattens voice even when instructed not to.** The 2026 "Voice Under Revision"
study on 300 personal narratives across three frontier models: first-person pronouns,
contractions and function words fall; register becomes "more polished, less situated";
voice-preserving prompts reduce the magnitude but not the direction. The earlier pipeline's
voicelessness was not a prompt bug. "Improve this" is the wrong verb; "rephrase in my voice" and
bounded edits are the right ones.

**4. Ownership is measurable and recoverable.** AI assistance cuts psychological ownership by
about one point on a seven-point scale; conditioning on the writer's own samples recovers half of
it, and reminding writers that they *edited* raises claimed ownership from 17% to 63%. Writers in
a 109-paper review ask for proposals to accept or reject, not takeovers. Design implication: the
owner's sentences go in first, Claude proposes, the owner accepts per change, and the packet
shows him what is his.

**5. Fabrication is structural, and the guardrail is source-binding.** CNET corrected 41 of 77
AI explainers. About 20% of model-generated references are wholly invented, and 100 fabricated
citations reached accepted NeurIPS 2025 papers past expert review. Semafor's answer, 4,900 claims
"each anchored to a specific quote" from transcripts, is the pattern. Our existing stat audit
("no number not in the brief") is the same idea for numbers; it should extend to opinions and
"I" statements, each traced to a transcript line.

**6. Disclosure erases the penalty.** The one peer-reviewed study (PLOS One 2026, n=366, 11
countries) found readers rate AI-assisted blogs marginally lower, that honest disclosure "almost
completely offset" the penalty, and that engagement intent was unaffected. Substack now lets
readers scan any post for AI and offers a "How I make this" statement; DEV labels posts Hand
Written / AI-Assisted / Fully Autonomous; AP requires disclosure when AI "materially contributes";
Google's helpful-content guidance asks "how was automation or AI used". A one-line process
statement per post is cheap insurance.

**7. The interview is an established craft with known failure modes.** Ghostwriters get one
article from a 30-minute interview using four question classes: contrarian ("what does everyone
get wrong about X"), framework ("walk me through how you…"), experience mining ("tell me about the
time you got this wrong"), and perspective ("what is changing that others don't see"). They stay
quiet after a question, reflect back, and always close with "anything else?", which "often yields
the interview's best insights". The LLM-specific pitfalls are documented: sycophantic praise
("great answer!"), leading questions that produce acquiescence, no stop rule ("until complete"),
and in a terminal, the transcript vanishing into scrollback.

## 2. What the practitioner workflow actually looks like

Every documented solo technical writer runs the same loop, and none of it is a pipeline:

| Step | What they do | Who |
|---|---|---|
| Capture | A rolling notes file, phone-first, spelling ignored | Ball, Williams, Evans |
| Trigger | Something confused me; something I just built; a thread that won't leave me alone | Evans, Willison, Majors |
| Draft | Own messy first draft, sometimes as a social thread | Majors, Ball |
| Edit | "Edit twice as much as you write"; rewrite from scratch when stuck | Majors, Ball |
| Ship | "Publish while you are still actively unhappy"; a 60-minute weekly timebox | Willison, Ball |
| Loop | Ask readers what confuses them; revise the post rather than write a rebuttal | Evans, Fowler |

AI, where it appears at all, is confined to proofreading, thesaurus and "does my argument have
holes", never to the sentences that carry an opinion.

## 3. Implications for the build

The research strengthens the architect recommendation of 2026-09-14 (retire the pipeline, keep
the MCP gate, put the interview in a Claude Code skill) and sharpens it into design rules.

**The one decision that matters: how much does Claude write?** Three defensible positions:

| Position | Claude's role | Owner's role | Evidence for | Evidence against |
|---|---|---|---|---|
| A. Willison-strict | Interview, structure, proofread, hole-check | Writes every sentence | Every named practitioner; zero voice risk | Not "easy"; the owner has under-built his voice for years |
| B. Arrangement (recommended) | Interview, then assemble the draft *from the owner's transcript sentences* with connective tissue; every opinion traces to a line he said | Answers the interview, edits the arrangement, accepts per change | Semafor's claim-to-quote; ownership research; Dixit's "choose and shape your own answers" | Requires the trace to be enforced, not trusted |
| C. Spiral-style | Drafts in his voice from the interview | Picks a draft, edits | Spiral's adoption; "easy" | Voice Under Revision; the practitioners' line; the retired pipeline already proved it |

Position B is the recommendation. It is the only one that is both easy and defensibly his, and it
is testable: a gate can check that every first-person sentence maps to the transcript.

**Design rules the evidence supports, each to be enforced rather than hoped for:**

1. **The interview writes a transcript file as it goes.** Scrollback loss is a documented Claude
   Code defect; the transcript is also the only legitimate source of opinion.
2. **One question at a time, no praise, story before opinion, never propose the answer inside
   the question.** Four question classes in order; "skip" and "enough" are first-class answers.
3. **An explicit stop rule**, not "until complete": thesis, two first-hand incidents, one
   disagreement, what would change his mind, then "anything else?".
4. **Voice comes from samples, not adjectives.** Five to ten of his best posts in context and a
   `voice-notes.md` the edit pass appends to. Style-adjective prompts are what the market is
   backlashing against.
5. **Draft from his sentences.** Quote the transcript verbatim where it is already good. The
   contractions and function words the model strips are the voice.
6. **Edits are proposals with explicit scope.** Critique first, then bounded edits; the verb is
   "rephrase in my voice", never "improve"; the owner accepts per change.
7. **Gates, in addition to the existing 24 checks:** every number and every "I" sentence traces
   to transcript or research source; an AI-tells lint (the open-source `vale-ai-tells` rules,
   keyless) that flags and never rewrites; a first-hand incident present; a one-line "how this
   was written" disclosure; a hero on disk.
8. **Review is consequence-first.** The packet leads with the claims he is about to publish under
   his name, before the prose, because automation bias is robust and explanations make it worse.
   Versions are numbered on disk; the diff is word-level and rendered, since line diffs mislead on
   prose; the final read is on the unlisted live-theme URL that already exists.
9. **Three triggers, one timebox.** Something confused him; something he just built or fixed; an
   article he disagreed with. A weekly hour is the only schedule.
10. **Close the loop keyless.** Post the open question to readers; log replies into the notes
    file; revise the post rather than write a rebuttal.

**Not doing, with the reason:**

- Topic-in, post-out generation, personas ("write like Kent Beck"), brand-voice profiles, SEO or
  AI-citation gates, editorial scores: every one is the market's failure mode or the retired
  pipeline's.
- Multi-agent orchestration: production reports show composition drift and runaway loops, and
  nothing in that literature addresses voice.
- Autocomplete or unsolicited suggestions while he types: they homogenise and reduce ownership.
- Spiral, AudioPen, Wispr Pro or any paid service: constraint #2. Voice input, if wanted, is a
  local Whisper tool.
- Trusting the model's own "this sounds like you": sycophancy is documented.

## 4. What is still open, and needs the owner

1. **Position A, B or C above.** ~~The research recommends B. This is the owner's call.~~
   **Decided 2026-09-15: B.** The owner chose arrangement. This is the spec's first line.
2. **The disclosure line**: whether to ship one, and its wording.
3. **Where the skill lives**: beside the gate in `blog-gate-mcp` (recommended 2026-09-14) or in
   the blog repo.

Nothing in the research argues for keeping a pipeline. The evidence is unusually consistent:
the value is scarcity of a real opinion, the risk is a model speaking for the author, and the
remedy is an interview that captures his sentences and a gate that proves they are his.
