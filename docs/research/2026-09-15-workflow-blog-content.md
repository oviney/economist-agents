# Workflow research: how solo technical writers publish, and what an interview-driven, gate-backed pipeline should look like

Research thread 3 of 3 for the 2026-09-15 pre-build study. Companion documents:
`2026-09-15-market-content-generation.md`, `2026-09-15-ux-ai-writing-interfaces.md`, and the
synthesis `2026-09-15-content-systems-synthesis.md`.

Date: 2026-09-15. Everything below is sourced; items that could not be verified are flagged inline and collected at the end.

## 1. How successful solo technical bloggers actually work

The pattern across every documented practitioner is the same: **a low-friction capture habit, a trigger that is external to "I should write", a rough first draft the author writes themselves, heavy editing, and a cadence commitment that beats perfectionism.** AI, where used at all, is confined to proofreading and argument-checking.

- **Simon Willison.** Triggers are TILs ("most of them took less than 10 minutes to write") and project write-ups ("writing about something is the cost I have to pay for building it") ([what-to-blog-about](https://simonwillison.net/2022/Nov/6/what-to-blog-about/)). Editing rule: "Aim to hit publish while you are still actively unhappy with what you have written" ([writethatblog](https://writethatblog.substack.com/p/simon-willison-on-technical-blogging)). AI policy, March 2026: "if text expresses opinions or has 'I' pronouns attached to it then it's written by me. I don't let LLMs speak for me in this way." He uses LLMs "as a thesaurus, as a proofreader and occasionally to check that the argument I'm making does not have any embarrassing holes", and strips LLM-invented rationales from any generated text ([ai-writing policy](https://simonwillison.net/2026/Mar/1/ai-writing/)). He warns "sophisticated readers can sniff out LLM-generated text, which inevitably hurts your credibility."
- **Julia Evans.** Trigger: "identify something I personally have found confusing or interesting; write about it"; she "store[s] up things that I find confusing for many months or years". She manages uncertainty with qualifiers ("My understanding is…"), writes for one specific person, and credits named draft readers ([some blogging myths](https://jvns.ca/blog/2023/06/05/some-blogging-myths/)). Her git-terminology post was sourced by asking Mastodon "what git jargon do you find confusing?" and summarising the replies ([confusing git terminology](https://jvns.ca/blog/2023/11/01/confusing-git-terminology/)). She drafts in Hugo and uses Google Docs when someone reviews ([usesthis](https://usesthis.com/interviews/julia.evans/)). No AI use documented.
- **Thorsten Ball.** Capture: Apple Notes on the phone, "ignoring all spelling, punctuation"; a rolling notes file he tweaks "over the course of a day, multiple days, weeks". Cadence: Register Spill started as "60min every Sunday to write. Whatever gets written in those 60min gets published." When stuck he deletes drafts and rewrites from scratch. "Send it. Don't be a perfectionist." ([writethatblog](https://writethatblog.substack.com/p/thorsten-ball-on-technical-blogging)). The notes file changed what he noticed: "with the note always available to keep track of what I found interesting, I found more interesting things" ([Noticing & Writing](https://registerspill.thorstenball.com/p/noticing-and-writing)). No AI use documented.
- **Gergely Orosz.** "I choose to use zero AI in my writing for the Pragmatic Engineer, and Grammarly is turned off as well" — to stop his writing skill degrading ([AMA](https://newsletter.pragmaticengineer.com/p/the-pragmatic-engineer-ama)).
- **Will Larson.** Wrote every word of *Crafting Engineering Strategy*; "no interest in an LLM writing any part" of it — "either it isn't a book worth writing or he is the wrong author" ([craftingengstrategy.com preface](https://craftingengstrategy.com/aic/preface/), [ces-ai-next-steps](https://lethain.com/ces-ai-next-steps/)). He does use LLMs downstream: packaging his own posts into "datapacks" and answering reader questions from them ([competitive-advantage-author-llms](https://lethain.com/competitive-advantage-author-llms/)).
- **Charity Majors.** Drafts as Twitter/Bluesky threads ("an incredibly effective form of drafting blog posts"); "Edit twice as much as you write"; one long post took ~35 hours; target one longform piece a month, rarely hit ([writethatblog](https://writethatblog.substack.com/p/charity-majors-on-technical-blogging)). Left WordPress because "there's so much friction in getting a post out that I just don't do it" ([charity.wtf](https://charity.wtf/p/moving-from-wordpress-to-substack)). No AI use documented.
- **Cassidy Williams.** Writes "off-the-cuff in Obsidian", keeps a note of blog ideas, weekly newsletter since 2017; trigger is recurring problems ("I've run into my own blog posts while debugging") ([writethatblog](https://writethatblog.substack.com/p/cassidy-williams-on-technical-blogging), [buttondown](https://buttondown.com/blog/2023-11-06-cassidoo)). No AI use documented.
- **swyx.** Twitter as public notes ("macro-tweeting"), daily newsletter as "a searchable database of AI news"; "the best thought leadership is selfish" — write to solve your own problem ([swyx.io/lead](https://swyx.io/lead), 2026-03-14). No AI writing use mentioned.
- **Kent Beck.** Documented AI use is a "companion model" trained on ~5M words of his own writing, not AI drafting; he reports "very little control" over its outputs ([A New Literature](https://newsletter.kentbeck.com/p/a-new-literature)).
- **Hillel Wayne, Dan Abramov:** no documented process found — flagged below.

Cross-cutting evidence: technical-blogging retrospectives converge on sustainable cadence over intensity, timeboxing, and being selective about which feedback to act on ([writethatblog lessons](https://writethatblog.substack.com/p/technical-blogging-lessons-learned)).

### Table of documented workflows

| Person | Trigger | Drafting | AI use | Edit/review | Cadence | Source |
|---|---|---|---|---|---|---|
| Willison | TIL; finished project; link with commentary | Own prose, publish while unhappy | Proofread, thesaurus, hole-check; never opinions/"I" | Self; LLM proofread prompt | Daily streak 2025 | [1](https://simonwillison.net/2026/Mar/1/ai-writing/), [2](https://writethatblog.substack.com/p/simon-willison-on-technical-blogging) |
| Evans | Something she found confusing; reader replies | Hugo, messy first draft | None documented | Named draft readers; Google Docs | Short posts, regular | [3](https://jvns.ca/blog/2023/06/05/some-blogging-myths/) |
| Ball | Rolling notes file (phone) | Vim, bullets → sentences → paragraphs; rewrite from scratch when stuck | None documented | Self, 60-min timebox | Weekly | [4](https://writethatblog.substack.com/p/thorsten-ball-on-technical-blogging) |
| Orosz | Industry events, reader surveys | Own prose | Zero; Grammarly off | Editor team (not detailed) | 134 issues/yr | [5](https://newsletter.pragmaticengineer.com/p/the-pragmatic-engineer-ama) |
| Larson | Own strategy work | Own prose | Never drafts; datapacks for readers | Self | Weekly newsletter | [6](https://lethain.com/competitive-advantage-author-llms/) |
| Majors | Threads that won't leave her alone | Bluesky/Twitter threads, walking | None documented | "Edit twice as much as you write" | ~Monthly longform (missed) | [7](https://writethatblog.substack.com/p/charity-majors-on-technical-blogging) |
| Williams | Recurring problems | Obsidian, off-the-cuff | None documented | Self | Weekly since 2017 | [8](https://writethatblog.substack.com/p/cassidy-williams-on-technical-blogging) |
| swyx | Own problem; gap nobody filled | Tweets as notes | None mentioned | Self | Daily newsletter | [9](https://swyx.io/lead) |

## 2. Professional editorial workflow and the ghostwriter interview

The standard content-ops chain is ideation → brief → draft → edit → approval → publish → promote → analyse; the **brief** sits after topic approval and before drafting, and states purpose, audience, tone, angle, structure and length ([Multicollab](https://www.multicollab.com/blog/guide-editorial-workflow/), [MarketMuse](https://blog.marketmuse.com/what-is-a-content-brief/), [Content Harmony](https://www.contentharmony.com/blog/what-is-a-content-brief/)). The existing `briefs/TEMPLATE.md` (thesis, experiences, disagreement, what would change your mind) is a reasonable owner-side brief; the professional gap is that a brief normally records *angle and audience*, not just thesis.

The ghostwriter interview is the closest established craft to what is being built:

- **Length and yield.** "Thirty minutes is usually enough for one solid article and several repurposed assets" if the interviewer arrives with a specific angle; longer sessions feed a series ([Higher Pitch playbook](https://thehigherpitch.com/blogs/insights-executive-ghostwriting-playbook-b2b/)). Voice-capture engagements start with 2–3 recorded interviews plus analysis of the executive's existing emails/talks, and the executive reviews every piece, 30–60 min/week ([Shadow](https://www.shadow.inc/resources/executive-ghostwriting-thought-leadership)). These are agency marketing pages; treat the numbers as practice norms, not evidence.
- **Question design.** Four classes: contrarian discovery ("What does everyone in your industry get wrong about X?"), framework extraction ("Walk me through your process for…"), experience mining ("Tell me about a time you got X completely wrong", "most expensive mistake"), perspective ("what's changing that others don't see") ([River](https://rivereditor.com/blogs/thought-leadership-ghostwriting-ceos-complete-guide)). Push past rehearsed talking points to "real client situations, specific numbers, or named disagreements" ([Higher Pitch](https://thehigherpitch.com/blogs/insights-executive-ghostwriting-playbook-b2b/)).
- **Interview conduct.** Open broad and easy ("How did you get started with…"), then "BE QUIET and listen. If they pause, don't immediately jump in"; reflect back with "What I hear you saying is…"; always close with "Do you have anything else you want to share?" — which "often yields the interview's best insights"; record and review transcripts, because the best material "come[s] as asides or offhand comments executives don't recognize as noteworthy" ([Viewfinder](https://viewfinderpartners.com/blog/what-ive-learned-about-interviewing-thought-leaders/), [River](https://rivereditor.com/blogs/thought-leadership-ghostwriting-ceos-complete-guide)).
- **Review.** The executive "reads the final draft aloud (fastest way to catch mismatched phrasing)" and "must genuinely hold the positions expressed" ([Higher Pitch](https://thehigherpitch.com/blogs/insights-executive-ghostwriting-playbook-b2b/), [Shadow](https://www.shadow.inc/resources/executive-ghostwriting-thought-leadership)).

## 3. Multi-agent vs single-agent content pipelines: what went wrong

- **CNET (2022–23).** 77 AI-written finance explainers under "CNET Money Staff"; 41 of 77 needed corrections — transposed numbers, wrong company names, factual errors — plus a plagiarism finding. The remediation is instructive: "No story will be entirely produced by an AI tool", AI limited to data analysis, outlines and explanatory content, plagiarism checks, transparency ([The Decoder](https://the-decoder.com/cnet-investigation-shows-lots-of-flaws-in-ai-written-articles), [Futurism](https://futurism.com/cnet-ai-plagiarism)).
- **Sports Illustrated (2023).** Fake authors with AI-generated headshots via contractor AdVon; content pulled, partnership ended. The ethics lesson quoted: "the mistake is in trying to hide it… a secret is a form of lying" ([Fortune](https://fortune.com/2023/11/28/sports-illustrated-ai-written-articles-reporters-who-dont-exist)).
- **Citation fabrication is structural, not a prompt bug.** ~20% of GPT-generated references were wholly fabricated and fewer than one in three fully accurate ([Enago](https://www.enago.com/responsible-ai-movement/resources/ai-generated-fake-references-scholarly-integrity/)); 100 hallucinated citations reached accepted NeurIPS 2025 papers past 3–5 expert reviewers each, 66% total fabrications, many with "identifier hijacking to create false verifiability" ([arXiv 2602.05930](https://arxiv.org/pdf/2602.05930)). The working guardrail: "the model is never allowed to answer from memory but answers from documents it just retrieved" ([Pickaxe](https://pickaxe.co/post/ai-research-agent)). This matches the B-042 finding (mandatory chart gate → four invented percentages).
- **What a newsroom did right.** Semafor's AI pass over 300 speakers' transcripts produced 4,900 claims with "every claim anchored to a specific quote"; journalists then stress-tested premises and cut to those "most clearly supported by what was actually said". Their conclusion: "current AI systems aren't capable of generating insights on their own more reliably than journalists" ([Semafor](https://www.semafor.com/article/05/06/2026/how-we-used-ai-to-distill-signals-from-semafor-world-economy)).
- **Governance research.** Reuters Institute (2026) documents "cognitive surrender" — users adopting deliberately wrong fluent outputs (Wharton, n=1,372) — reviewer fatigue eroding oversight, the risk of LLMs collapsing nuance into "three bullet points", and the observation that mature shops embed governance in architecture (sentence-level provenance metadata) rather than post-hoc review ([Reuters Institute](https://reutersinstitute.politics.ox.ac.uk/news/guidelines-architecture-how-newsrooms-are-rethinking-ai-governance)).
- **Framework practitioners.** CrewAI production write-ups report broad agents "loop through multiple attempts… and produce inconsistent output formats that downstream agents cannot reliably process", unbounded `max_iter` cost leaks, and composition failures; they recommend sequential (deterministic) orchestration and schema-validated outputs. The "15% → 3%" error figure is vendor-derived and unverified ([AgileSoftLabs](https://www.agilesoftlabs.com/blog/2026/06/crewai-in-production-2026-real-lessons)). Nothing in the agentic-framework literature found addresses voice; it is a non-goal of those systems, which is why the Economist pipeline was competent and voiceless.

## 4. Quality gates for authenticity

- **Platform policies.** Medium: AI-generated text must be disclosed in the first two paragraphs; undisclosed AI gets network-only distribution; AI writing barred from the paywall; outlining and grammar/fact checkers exempt ([Plagiarism Today](https://www.plagiarismtoday.com/2024/04/11/medium-sets-new-policies-on-ai-generated-writing/); primary page returned 403). DEV: disclose (tag or in-copy), fact-check before publishing, and since Aug 2024 a three-tier label — Hand Written / AI-Assisted / Fully Autonomous — with "undisclosed autonomy is problematic and deceptive" ([DEV guidelines](https://dev.to/devteam/guidelines-for-ai-assisted-articles-on-dev-17n6), [DEV disclosure tiers](https://dev.to/devteam/introducing-ai-disclosure-on-dev-tools-for-nuance-clarity-and-better-feeds-34mk)). Hashnode: user must review and approve any AI suggestion before publishing ([Hashnode terms](https://hashnode.com/terms)). Substack: no platform AI policy ([Substack Writers at Work](https://www.substackwritersatwork.com/p/substack-ai-policy-workshop-2026)). ACM/IEEE: AI is not an author; disclose tool, sections and level of use ([SIGCSE policy](https://sigcse2025.sigcse.org/info/policies-ai), [Purdue guide](https://guides.lib.purdue.edu/c.php?g=1371380&p=10135076)). AP (July 2026): "Every AI-generated output must be reviewed and edited by an AP journalist"; AI may research, summarise, transcribe, suggest headlines and fix grammar; may not do "reporting, sourcing, editorial judgment, or verification"; disclose when AI "materially contributes" ([Media Copilot](https://mediacopilot.ai/ap-ai-newsroom-standards-update/), [America's Newspapers](https://www.newspapers.org/stories/ap-updates-newsroom-standards-for-artificial-intelligence,4167054)).
- **Google.** Scaled content abuse = "many pages generated for the primary purpose of manipulating search rankings", explicitly including "using generative AI tools… to generate many pages without adding value" ([spam policies](https://developers.google.com/search/docs/essentials/spam-policies), [gen-AI guidance](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content)). The helpful-content self-assessment asks whether content "clearly demonstrate[s] first-hand expertise" and "Are you providing background about how automation or AI-generation was used?" — the Who/How/Why framing ([creating helpful content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)). Implication: a single-author blog publishing one interviewed post at a time is nowhere near the policy; the risk is E-E-A-T "Experience" — every post needs a first-hand incident, and a short "how this was written" line is cheap insurance.
- **Style-drift checks.** Wikipedia's tells list (delve/tapestry/underscore, "not just X but Y", tacked-on participle phrases, vague "experts argue" attribution, em-dash and bold overuse) is a usable lint list; it warns that detector tools have "non-trivial error rates" and human detection is near chance for non-experts ([Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)). `vale-ai-tells` packages 17 such rules (6 errors, 11 suggestions) and is designed to be driven from Claude Code: it "marks tells; it never bulk-rewrites" ([shadowgraph](https://shadowgraph.io/krishnasunkam/vale-ai-tells), [repo](https://github.com/krishnasunkam/vale-ai-tells)).
- **"Did the author say this."** Semafor's claim→quote anchoring is the model; the ghostwriting read-aloud is the human equivalent.

## 5. Keyless feedback loops

- **Ask readers before writing.** Evans' Mastodon "what confuses you?" produced her most-cited git post; she reports "basically every other core feature of git was mentioned by at least one person" ([jvns.ca](https://jvns.ca/blog/2023/11/01/confusing-git-terminology/)). The comment-mining variant: extract readers' "exact questions, objections, and wording", cluster by intent, draft from that ([Scaleblogger](https://scaleblogger.com/blog/2026-engagement-content-loop/)).
- **Revise rather than repost.** Fowler's bliki exists because blog posts "quickly age. I find writing too hard to want to spend it on things that disappear"; entries are cross-linked and updated ([Fowler](https://martinfowler.com/bliki/WhatIsaBliki.html)).
- **Discussion as correction.** HN threads cluster on posts that are "subtly wrong, incomplete, or provocative enough to produce corrections"; staying around to reply matters ([Syften](https://syften.com/blog/hacker-news-marketing/)).
- **Analytics by eye.** For a solo site, referrers and top pages read in one scroll are the whole signal; GA4 "charges you time" ([LeadFnF](https://leadfnf.com/blog/ga4-vs-plausible-honest-comparison-for-saas-founders-2026)). Majors' caution applies: "It's impossible to predict what is going to resonate… so please don't try" ([writethatblog](https://writethatblog.substack.com/p/charity-majors-on-technical-blogging)).
- What evidence says improves a technical blog over time: consistency of cadence, shorter units, selective response to feedback, writing for one reader ([writethatblog lessons](https://writethatblog.substack.com/p/technical-blogging-lessons-learned), [Evans](https://jvns.ca/blog/2023/06/05/some-blogging-myths/)). No quantitative study of "what improves a technical blog" was found; this is practitioner consensus, not evidence.

## Recommended end-to-end workflow

1. **Capture, always-on.** A single rolling notes file (Ball) plus TIL and "just shipped" hooks (Willison). The entry point should accept a one-line note, not a finished brief.
2. **Trigger, not schedule.** Three triggers: something confused you; something you just built or fixed; an article you disagreed with. A weekly timebox (Ball's 60 minutes) is the only schedule.
3. **Interview, 30 minutes, one question at a time.** Open broad, then contrarian → framework → experience-mining → "what would change your mind" → "anything else?" (River, Viewfinder, Higher Pitch). Claude listens, reflects back ("What I hear you saying is…"), does not fill silences with its own content. The transcript is persisted; it is the only source of opinion.
4. **Brief, generated from transcript, approved by owner.** Thesis, audience, angle, the two or three first-hand incidents, and the numbered claims each anchored to a transcript line (Semafor). This is the brief in the professional sense and it replaces the current owner-authored template.
5. **Research in service of the brief, source-bound.** Research may add external facts only with URL; the existing stat audit stays ("no number not in the brief").
6. **Draft.** Claude drafts from transcript + brief only; every "I" sentence must trace to a transcript claim; no invented rationales (Willison's rule, applied mechanically).
7. **Owner read-aloud and edit.** Owner edits in the file; Claude is limited to proofreading and hole-finding on request (Willison, AP). Vale-ai-tells lint runs here — flags, never rewrites.
8. **Gate.** Existing 24-check validator plus: claim→transcript trace, AI-tells lint, first-hand-incident present, a one-line "how this was written" disclosure (Google How, DEV tiers), hero drawn.
9. **Review URL → publish** (unchanged).
10. **Close the loop keyless.** After publishing: post the open question to Bluesky/LinkedIn (Evans); log replies and corrections into the notes file; schedule a bliki-style revision pass rather than a rebuttal post (Fowler).

## Failure modes and the guardrail that worked

| Failure mode | Evidence | Guardrail |
|---|---|---|
| Fabricated numbers/names | CNET 41/77 | Source-bound facts; no number without a brief/transcript citation |
| Hallucinated citations that look real | NeurIPS 2025, ~20% fake refs | Retrieval-only citing; URL must resolve; owner opens it |
| Voice loss / invented rationale | Willison's "rationale the LLM just made up"; the retired pipeline | Opinion and "I" sentences only from transcript; claim→quote trace |
| Over-polished, LLM-cadenced prose | Wikipedia tells; Willison "readers can sniff out" | Vale-ai-tells lint; owner edits, Claude only flags |
| Nuance collapsed to bullets | Reuters Institute | Interview asks for the incident, not the lesson; brief keeps incidents |
| Reviewer fatigue → cognitive surrender | Wharton via Reuters Institute | One post at a time; read-aloud step; no batch publishing |
| Hidden AI involvement | SI, CNET | One-line disclosure in each post |
| Agent composition drift, runaway loops | CrewAI production reports | Single sequential path, schema-validated handoffs (already done in ADR-0016) |
| Never publishing | Willison, Ball | Timebox; "publish while unhappy" |

## Could not verify

- Hillel Wayne and Dan Abramov: no documented process found; the Abramov "abandoned drafts" anecdote surfaced only in a search summary without a fetchable URL.
- Charity Majors' "three-month weekly short-posts experiment" appeared in a search summary; the primary post could not be located.
- Medium's primary policy page (403); Google's March 2024 announcement post (fetch returned navigation only) — both cited via secondaries. The "40% less unhelpful content" figure comes from SEO secondaries ([Marcel Digital](https://www.marceldigital.com/blog/google-announces-march-2024-core-update-new-spam-policies)).
- AP's primary policy page was not fetched; two secondaries agree on the July 24, 2026 update.
- CrewAI "15% → 3%" and ghostwriting "30 minutes" figures are vendor/agency claims.
- No quantitative evidence on what improves a technical blog over time.

## Sources

- https://simonwillison.net/2026/Mar/1/ai-writing/
- https://simonwillison.net/2022/Nov/6/what-to-blog-about/
- https://writethatblog.substack.com/p/simon-willison-on-technical-blogging
- https://daringfireball.net/linked/2026/08/07/simon-willison-on-blogging
- https://jvns.ca/blog/2023/06/05/some-blogging-myths/
- https://jvns.ca/blog/2023/11/01/confusing-git-terminology/
- https://usesthis.com/interviews/julia.evans/
- https://writethatblog.substack.com/p/thorsten-ball-on-technical-blogging
- https://registerspill.thorstenball.com/p/noticing-and-writing
- https://newsletter.pragmaticengineer.com/p/the-pragmatic-engineer-ama
- https://lethain.com/competitive-advantage-author-llms/
- https://lethain.com/ces-ai-next-steps/
- https://craftingengstrategy.com/aic/preface/
- https://writethatblog.substack.com/p/charity-majors-on-technical-blogging
- https://charity.wtf/p/moving-from-wordpress-to-substack
- https://writethatblog.substack.com/p/cassidy-williams-on-technical-blogging
- https://buttondown.com/blog/2023-11-06-cassidoo
- https://swyx.io/lead
- https://newsletter.kentbeck.com/p/a-new-literature
- https://writethatblog.substack.com/p/technical-blogging-lessons-learned
- https://www.multicollab.com/blog/guide-editorial-workflow/
- https://blog.marketmuse.com/what-is-a-content-brief/
- https://www.contentharmony.com/blog/what-is-a-content-brief/
- https://thehigherpitch.com/blogs/insights-executive-ghostwriting-playbook-b2b/
- https://www.shadow.inc/resources/executive-ghostwriting-thought-leadership
- https://rivereditor.com/blogs/thought-leadership-ghostwriting-ceos-complete-guide
- https://viewfinderpartners.com/blog/what-ive-learned-about-interviewing-thought-leaders/
- https://the-decoder.com/cnet-investigation-shows-lots-of-flaws-in-ai-written-articles
- https://futurism.com/cnet-ai-plagiarism
- https://fortune.com/2023/11/28/sports-illustrated-ai-written-articles-reporters-who-dont-exist
- https://www.enago.com/responsible-ai-movement/resources/ai-generated-fake-references-scholarly-integrity/
- https://arxiv.org/pdf/2602.05930
- https://pickaxe.co/post/ai-research-agent
- https://www.semafor.com/article/05/06/2026/how-we-used-ai-to-distill-signals-from-semafor-world-economy
- https://reutersinstitute.politics.ox.ac.uk/news/guidelines-architecture-how-newsrooms-are-rethinking-ai-governance
- https://www.agilesoftlabs.com/blog/2026/06/crewai-in-production-2026-real-lessons
- https://mediacopilot.ai/ap-ai-newsroom-standards-update/
- https://www.newspapers.org/stories/ap-updates-newsroom-standards-for-artificial-intelligence,4167054
- https://www.plagiarismtoday.com/2024/04/11/medium-sets-new-policies-on-ai-generated-writing/
- https://dev.to/devteam/guidelines-for-ai-assisted-articles-on-dev-17n6
- https://dev.to/devteam/introducing-ai-disclosure-on-dev-tools-for-nuance-clarity-and-better-feeds-34mk
- https://hashnode.com/terms
- https://www.substackwritersatwork.com/p/substack-ai-policy-workshop-2026
- https://sigcse2025.sigcse.org/info/policies-ai
- https://guides.lib.purdue.edu/c.php?g=1371380&p=10135076
- https://developers.google.com/search/docs/essentials/spam-policies
- https://developers.google.com/search/docs/fundamentals/using-gen-ai-content
- https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- https://www.marceldigital.com/blog/google-announces-march-2024-core-update-new-spam-policies
- https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing
- https://shadowgraph.io/krishnasunkam/vale-ai-tells
- https://github.com/krishnasunkam/vale-ai-tells
- https://martinfowler.com/bliki/WhatIsaBliki.html
- https://scaleblogger.com/blog/2026-engagement-content-loop/
- https://syften.com/blog/hacker-news-marketing/
- https://leadfnf.com/blog/ga4-vs-plausible-honest-comparison-for-saas-founders-2026
