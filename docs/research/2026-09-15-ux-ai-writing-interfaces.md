# AI co-writing UX: interaction patterns for an interview-first, terminal-first solo author

Research thread 2 of 3 for the 2026-09-15 pre-build study. Companion documents:
`2026-09-15-market-content-generation.md`, `2026-09-15-workflow-blog-content.md`, and the
synthesis `2026-09-15-content-systems-synthesis.md`.

Date: 2026-09-15. Scope: 30+ searches, ~35 pages fetched. Every claim carries a URL; items that
could not be verified beyond a search snippet are marked **[snippet only]**.

## 1. Interaction patterns in current AI writing interfaces

**ChatGPT Canvas** — chat on the left, editable document on the right. Highlight-to-edit pops a prompt on the selection; a bottom-right toolbar offers "Suggest edits", "Adjust length", "Reading level", "Add final polish". Suggested edits appear as annotations beside highlighted text and are accepted or rejected individually; version arrows and a diff button compare the current version with the previous one. Export is copy-paste only ([DataCamp](https://www.datacamp.com/blog/chatgpt-canvas)). No voice profile; provenance is not shown beyond version history.

**Claude Artifacts** — a side panel beside chat; since October 2025 edits are targeted string replacements ("update") rather than full regeneration, shown as a live preview updating in sequence ([Hyperdev](https://hyperdev.matsuoka.com/p/claudeais-quiet-revolution-in-artifact)). Third-party comparisons rate Canvas better for prose because Claude lacks highlight-a-sentence editing ([ShareDuo](https://www.shareduo.com/blog/claude-artifacts-vs-chatgpt-canvas)). No voice or provenance features.

**Google Docs + Gemini** — suggestions render individually; the user clicks "Show suggestion" then Accept/Reject; edits "remain private until you approve them" ([Google support](https://support.google.com/docs/answer/16558954?hl=en), [9to5Google, Mar 2026](https://9to5google.com/2026/03/10/google-docs-gemini-upgrade/)). A "Refine chip" edits a highlighted section rather than regenerating the document. Voice is captured by "Match writing style": pick a reference Drive document and Gemini rewrites to its tone, sentence structure and vocabulary ([Workspace Updates, Apr 2026](https://workspaceupdates.googleblog.com/2026/04/new-gemini-capabilities-in-google-docs-help-you-go-from-blank-page-to-brilliance.html)). October 2025 added source grounding: restrict writing help to sources linked in the document ([Workspace Updates](https://workspaceupdates.googleblog.com/2025/10/improve-writing-gemini-google-docs-sources.html)).

**Microsoft Copilot in Word** — select text, "Make changes" with a prompt; "Get Coaching" puts feedback beside the text so it "will not be overwritten" ([Neowin](https://www.neowin.net/news/microsoft-words-new-coaching-with-copilot-feature-helps-you-review-and-rewrite-your-content/)). Provenance is via Track Changes: enable it before invoking Copilot and every AI character is an insertion/deletion, but long generations produce markup that "can obscure the original document" ([WiseChecker](https://wisechecker.com/how-to-use-copilot-in-word-with-track-changes-safely/)). **[snippet only]** Copilot now writes tracked changes and comments natively ([Windows Forum](https://windowsforum.com/threads/copilot-in-word-adds-track-changes-comments-for-auditable-enterprise-reviews.413287/)).

**Grammarly** — two relevant pieces. *Voice profiles* are inferred passively from what you type, kept separately for messages and documents, described in an editable AI-generated summary, and applied via one-click "rewrite in my voice" ([Grammarly support](https://support.grammarly.com/hc/en-us/articles/23153676821773-Introducing-voice-features)). *Authorship* logs typed vs pasted vs AI-generated text and produces a colour-coded report with a replay; it is process-tracking, not detection ([Grammarly](https://www.grammarly.com/authorship)). December 2025 relabelled "Rephrased with Grammarly's AI" as "AI-Generated or Rephrased with AI" under "Copied from a Source" after criticism that the Humanizer output was being logged as human-typed; text generated in-document by other tools still lands in "Unknown" ([Plagiarism Today](https://www.plagiarismtoday.com/2025/12/11/grammarly-updates-authorship-improves-labeling/), [earlier critique](https://www.plagiarismtoday.com/2025/11/06/how-grammarly-launders-ai-generated-content/)).

**iA Writer 7 Authorship** — the strongest provenance model for a markdown author. AI text is rendered light grey ("Tabula Grigia"), human text black; as you rewrite AI words they turn black word by word. Pasted ChatGPT/LM Studio conversations are auto-marked; you can also "Mark As" a selection. Annotations live at the end of the file in an open Markdown Annotations format, processed locally, never sent anywhere ([iA](https://ia.net/topics/ia-writer-7), [support](https://ia.net/writer/support/editor/authorship), [Cassinelli](https://matthewcassinelli.com/ia-writer-ai-authorship-markdown-annotations/)). iA's stated position: use AI as a dialogue partner, not a ghostwriter.

**Lex** — inline line-level suggestions in the document plus a chat; voice via *Style Guides* built from writing samples plus AI-generated instructions ("Generate from attachments"); guides can be defaults per folder. Their guidance: "a few great examples are better than lots of mediocre ones" ([Lex Style Guides](https://lex.page/read/3492a59e-ea19-4733-964a-3adc25b5f3e0)).

**Sudowrite** — rejects style descriptions outright: "A prompt is a description of a thing. A sample is the thing." Recommends 5–10 paragraphs or a full chapter of varied prose as persistent context, and "Rewrite with Customize" for directional edits that keep the voice ([Sudowrite](https://sudowrite.com/blog/ai-voice-matching/)). "My Voice" (beta) fine-tunes a private model on your work **[snippet only]** ([changelog](https://feedback.sudowrite.com/pt/changelog/early-access-my-voice)).

**Notion AI** — a "Custom Instructions" page (role, style, banned constructions) that the agent reads every session; voice *input* for prompts shipped April 2026 ([Fazm timeline](https://fazm.ai/blog/notion-ai-updates-2025-2026)). No provenance.

**Obsidian** — Smart Composer gives Cursor-style highlight-and-rewrite with one-click apply inside notes; Copilot for Obsidian is chat-beside-vault ([Shadow.do](https://www.shadow.do/blog/best-ai-plugins-for-obsidian-2026), [Obsidian forum](https://forum.obsidian.md/t/new-plugin-obsidian-smart-composer-cursor-ai-like-editing/90016)).

**Cursor-style inline diff** — the per-hunk accept/reject was Cursor's most-defended feature; when the Agent window moved to session-level "Review +1181 −413" summaries users complained they lost "incremental, visual, reversible approval" ([Cursor forum](https://forum.cursor.com/t/bring-back-per-change-apply-inline-diff-review-you-re-throwing-away-your-best-ux-advantage/160856); same demand in [Kiro #8968](https://github.com/kirodotdev/Kiro/issues/8968)). For prose, line diffs fail: rewording rewraps a paragraph so the whole block shows changed, and moved sections look like delete + add ([Meridian](https://gitmeridian.com/markdown-diff/)). Word-level, move-aware, rendered diffs are the fix.

## 2. Research and design guidance on human-AI co-writing

- **Ownership drops under any AI assistance; personalisation partly restores it.** N=176 study: AI-assisted modes cut psychological ownership by ~0.85–1.0 on a 7-point scale; conditioning suggestions on the writer's own samples recovered +0.43. Five patterns: *on-demand initiation*, *micro-suggestions over takeovers* (≤30 tokens), *voice anchoring via style personalisation*, *persona as audience scaffold, not author*, *provenance cues at the point of decision* (grey until explicitly accepted) ([Who Owns the Text?, 2026](https://arxiv.org/html/2601.10236)).
- **Writers want suggestions, not edits, and control over *when* AI engages.** PRISMA review of 109 papers plus 15 interviews: the literature over-builds "Active Co-Writing" (37% of systems) while writers ask for proposals to accept/reject, global and local toggles, and final decision authority framed as "negotiation" ([Co-Writing with AI, on Human Terms, PACM HCI 2025](https://arxiv.org/html/2504.12488v2)).
- **Ownership rises with visible participation.** Reminding people they prompted raised claimed ownership 17%→29%; reminding them they *edited* raised it to 63% ([LLMs as Writing Assistants](https://arxiv.org/html/2404.00027v3)).
- **LLM revision flattens voice even when told not to.** 300 personal narratives, three frontier models: first-person pronouns, contractions and function words fell; register became "more polished, less situated"; voice-preserving prompts "reduce the magnitude of the changes but do not eliminate their direction" ([Voice Under Revision, 2026](https://arxiv.org/abs/2604.22142)). Cross-cultural CHI 2025 study, N=118: autocomplete suggestions pushed Indian writers toward Western style ([Agarwal et al.](https://arxiv.org/abs/2409.11360)). Essay study, N=6,875: cohesion structure lost 70–78% of variance, but specific prompting reversed it, so homogenisation is "malleable" ([arXiv 2603.21228](https://arxiv.org/abs/2603.21228)).
- **Sycophancy undermines feedback.** NN/G: models align with the user's stated view; to get honest critique, withhold your opinion, reset sessions, verify independently ([NN/G](https://www.nngroup.com/articles/sycophancy-generative-ai-chatbots/)). NN/G's CARE prompt structure (context, ask, rules, examples) is their only writing-specific guidance found ([NN/G video](https://www.nngroup.com/videos/care-for-ai-prompts/)).
- **Microsoft's 18 HAI guidelines** still frame the field: make clear what the system can do, support efficient dismissal and correction, learn from granular feedback, give global controls ([Microsoft Research](https://www.microsoft.com/en-us/research/project/guidelines-for-human-ai-interaction/), [Learn module](https://learn.microsoft.com/en-us/training/modules/introduction-to-microsofts-responsible-ai-approach/3-use-guidelines-for-human-ai-interaction)). No Anthropic or Google design guideline specific to co-writing was found.
- **[snippet only]** CHI 2025 attribution study: credit follows idea and editing contributions more than wording ([ACM](https://dl.acm.org/doi/full/10.1145/3706598.3713522)); CHI 2025 "Can AI writing be salvaged?" catalogues AI idiosyncrasies expert editors remove ([ACM](https://dl.acm.org/doi/full/10.1145/3706598.3713559)). Both 403'd on fetch.

## 3. The "interview me, then draft" pattern

**Who does it.** Jay Dixit's "flip the script" technique: give context, then ask the model to interview you, "in a batch or, if I want it to feel less like a writing assignment and more like a conversation, take them one at a time"; the draft is then assembled by *the writer* "choosing and shaping" their own answers ([Wonder Tools](https://wondertools.substack.com/p/flip-the-script-on-ai)). In Claude Code: Sorbh's `interview-me` skill asks "hard questions one at a time", pushes back on contradictions, and emits a spec with a decisions log and an optional Artifact preview ([GitHub](https://github.com/Sorbh/interview-me)); Thariq's interview command uses `AskUserQuestion` and continues "until it's complete" ([gist](https://gist.github.com/robzolkos/40b70ed2dd045603149c6b3eed4649ad)). Both target specs, not prose; no shipped consumer product that interviews first for blog writing was found — only prompts and skills.

**What users report.** Dixit: ghostwritten drafts are "pure slop"; interview answers surface real memories. Survey methodology backs the format: chatbot surveys produce more differentiated answers and less satisficing than web forms ([Kim et al.](https://www.researchgate.net/publication/332741564_Comparing_Data_from_Chatbot_and_Web_Surveys_Effects_of_Platform_and_Conversational_Style_on_Survey_Response_Quality), [Xiao et al., TOCHI](https://dl.acm.org/doi/fullHtml/10.1145/3381804)); an N=1,800 experiment found LLM probing gave "more detailed and informative" answers "at a slight cost to respondent experience" and with acquiescence-bias false positives ([arXiv 2504.13908](https://arxiv.org/abs/2504.13908)).

**Pitfalls.** (a) Acquiescence/leading: interviewer LLMs coded answers the respondent merely agreed with (same paper). (b) Praise-and-move-on: ChatGPT-style interviewers say "Great answer!" regardless ([DEV](https://dev.to/guanyi_liu_21a5d7417eb332/when-chatgpt-says-great-but-teaches-nothing-building-a-real-interview-coach-with-claude-code-50mh)) — sycophancy again. (c) Socratic research warns "asking many questions is not sufficient" and over-reliance can reduce reflection ([Emergent Mind survey](https://www.emergentmind.com/topics/socratic-questioning-for-llms)). (d) No stop condition: the Thariq command runs "until complete"; the Sorbh skill documents no confidence threshold. (e) Terminal thread loss (see §4) makes a 20-turn interview hard to re-read.

## 4. Terminal and agentic writing workflows

**Skill/command designs.** Content-writing plugins converge on the same primitives: `draft`, `new-version` (numbered files on disk), `proofread`, `improve-tone`, `publish`, plus `add-example` / `analyze-style` / `generate-style-guide` for voice ([Rosehill plugin](https://github.com/danielrosehill/Claude-Content-Writing-Plugin)). Practitioner guidance: a ≤200-line `CLAUDE.md` of *checkable* rules (banned words, "edit, do not rewrite"), samples imported by reference, the human writes the messy first draft, plan mode for a ranked critique before any edit, and per-line accept/reject of diffs ([CC for Everyone](https://ccforeveryone.com/guides/claude-code-for-writers)). Aaron Held runs four windows — Hugo live server, Claude, VS Code markdown preview, mobile browser — and rewrites "most of the content" himself; friction is telling Claude to reload after external edits ([Held](https://www.aaronheld.com/post/streamlining-blog-writing-with-claude-code/)). Nils Durner on Codex CLI for a long document: ~250-line chunked reads and selective scanning caused inconsistent edits; fix was pasting the target passage into context first ([Durner](https://ndurner.github.io/writing-with-codex)).

**Known terminal limits.** Claude Code's alternate screen buffer breaks scrollback in long sessions ([issue #42002](https://github.com/anthropics/claude-code/issues/42002), [#28077](https://github.com/anthropics/claude-code/issues/28077)); flicker and jumping scroll on long drafting sessions, mitigated by `/tui fullscreen` or `CLAUDE_CODE_NO_FLICKER=1` ([Ship with AI Lab](https://shipwithailab.substack.com/p/claude-code-for-everything-your-terminal)). `/rewind` restores file state per prompt for the last 100 checkpoints and can split "restore code" from "restore conversation"; it does not track bash-made or external edits ([Claude Code docs](https://code.claude.com/docs/en/checkpointing)). There is no prose-aware diff in the terminal; the draft on disk plus an editor preview is the universal mitigation.

## 5. Review and approval UX

Preview-URL review is table stakes: Vercel comments pin to page elements and text on preview deployments and email the PR owner ([Vercel](https://vercel.com/docs/comments)); Netlify Drawer adds annotated screenshots, recordings, and PR-synced comment threads ([Netlify](https://docs.netlify.com/deploy/review-deploys/netlify-drawer-for-feedback/overview/)). Ghost previews the post *in the live theme* with a shareable link ([Ghost](https://ghost.org/changelog/post-previews/)); Substack has a resettable secret draft link ([Substack](https://support.substack.com/hc/en-us/articles/360038433692-How-do-I-share-a-preview-of-my-post-with-others)); Jekyll needs a `draft: true` unlisted-post pattern excluded from feeds and sitemaps ([Sieger](https://danielsieger.com/blog/2025/12/31/public-drafts-with-jekyll.html)) — which is what `--mode review` already does.

**Why reviewers rubber-stamp.** Automation bias is robust: explanations made evaluators 19 points *more* likely to follow AI; radiologists' accuracy on AI-wrong cases fell from ~80% to <20% (novices) and 82%→45% (experts) ([TianPan](https://tianpan.co/blog/2026/04/15/human-in-the-loop-rubber-stamp), [Codacy](https://blog.codacy.com/automation-bias-in-ai-generated-code-review-why-clean-code-still-ships-broken)). Remedies that transfer to a solo author: consequence-first display before the content, structured override reasons, friction calibrated to stakes, and adversarial sampling (plant a known error and see if you catch it).

## Interaction pattern table

| Pattern | Where seen | Strengths | Weaknesses | Fit for terminal-first solo author |
|---|---|---|---|---|
| Chat beside document | Canvas, Artifacts, Lex, Copilot | Keeps conversation and text separate; version history | Needs a GUI; Artifacts weak at sentence-level edits | Medium: Artifact as *read* surface for a draft, not as the editor |
| Inline suggestion with accept/reject | Docs Gemini, Lex, Cursor, Smart Composer | Preserves ownership ("suggestions over edits"); provenance at point of decision | Line diffs fail for prose; per-hunk UI needs an editor | High if done as a word-level diff in an editor or HTML preview, not in the TUI |
| Track changes as provenance | Copilot Word | Auditable | Long generations drown the original | Low; markdown has no native equivalent |
| Grey-until-owned authorship marking | iA Writer 7 | Local, open format, turns black as you rewrite | Requires iA or a renderer; manual marking outside it | High for the *published-authenticity* claim; cheap to emulate in a preview |
| Sample-based voice profile | Sudowrite, Lex, Docs "Match writing style", Grammarly voice | Samples beat descriptions; research shows +ownership | Needs curated samples; still drifts (Voice Under Revision) | High: put 5–10 of his best posts in context, not a style adjective list |
| Rules file / custom instructions | Notion, CLAUDE.md guidance | Checkable, persistent | Adherence uneven (Durner); 200-line ceiling | High, already in use |
| Interview-first, one question at a time | Dixit prompt, `interview-me`, `AskUserQuestion` | Draws out real experiences; higher answer quality than forms | Sycophantic praise, leading probes, no stop rule, thread lost in scrollback | Very high; it is the core bet, needs a stop rule and a transcript file |
| Numbered versions on disk | Rosehill plugin, Held | Survives terminal; git-diffable | Clutter | High |
| Plan-mode critique before edit | CC for Everyone | Ranked problems, no silent rewrite | Extra turn | High |
| Preview URL + inline comments | Vercel, Netlify, Ghost | Reviews the real render | Comments need a platform | Medium: unlisted Jekyll URL exists; comments can be a checklist instead |
| Consequence-first / structured override | HITL literature | Counters automation bias | Friction | High and cheap: show the claims list before the prose |

## Recommendations for the build (each tied to a source)

1. **Interview writes to a file, not just the transcript.** Append each Q/A to `briefs/<slug>.interview.md` as it happens, so scrollback loss ([#42002](https://github.com/anthropics/claude-code/issues/42002)) never loses the thread and the answers become the draft's raw material, per Dixit's "choose and shape your own answers" ([Wonder Tools](https://wondertools.substack.com/p/flip-the-script-on-ai)).
2. **One question, no praise, explicit stop rule.** Ban evaluative acknowledgements ("great answer"), and stop at a stated coverage check (thesis, two experiences, one disagreement, what changes his mind) rather than "until complete" ([DEV](https://dev.to/guanyi_liu_21a5d7417eb332/when-chatgpt-says-great-but-teaches-nothing-building-a-real-interview-coach-with-claude-code-50mh), [gist](https://gist.github.com/robzolkos/40b70ed2dd045603149c6b3eed4649ad)). Offer "skip" and "enough" as first-class answers; probing costs respondent experience ([arXiv 2504.13908](https://arxiv.org/abs/2504.13908)).
3. **Ask for the story before the opinion, and never propose the answer inside the question.** Acquiescence bias inflates agreement with the interviewer's framing ([arXiv 2504.13908](https://arxiv.org/abs/2504.13908)); NN/G: withhold the position you want validated ([NN/G](https://www.nngroup.com/articles/sycophancy-generative-ai-chatbots/)).
4. **Voice = samples, not adjectives.** Load 5–10 of his published posts as persistent context and keep the rules file to checkable constraints ([Sudowrite](https://sudowrite.com/blog/ai-voice-matching/), [Lex](https://lex.page/read/3492a59e-ea19-4733-964a-3adc25b5f3e0), [CC for Everyone](https://ccforeveryone.com/guides/claude-code-for-writers), [Who Owns the Text?](https://arxiv.org/html/2601.10236)).
5. **Draft from his sentences.** Quote interview answers verbatim where they are already good; the writer's first-person contractions and function words are exactly what LLM revision strips ([Voice Under Revision](https://arxiv.org/abs/2604.22142)). Make "rephrase in my voice" the default edit op, not "improve" ([Who Owns the Text?](https://arxiv.org/html/2601.10236)).
6. **Iterate by critique-then-bounded-edit, never silent rewrite.** Ranked problems first, then edits with explicit scope ("preserve opening and closing lines") ([CC for Everyone](https://ccforeveryone.com/guides/claude-code-for-writers)); writers want proposals, not takeovers ([Co-Writing on Human Terms](https://arxiv.org/html/2504.12488v2)).
7. **Number versions on disk and diff at word level in a rendered view.** `output/posts/<slug>.v3.md`; render a local HTML side-by-side with word-level highlights for the review step, since line diffs mislead on prose ([Meridian](https://gitmeridian.com/markdown-diff/), [Rosehill plugin](https://github.com/danielrosehill/Claude-Content-Writing-Plugin)).
8. **Carry provenance into the review packet.** Mark which paragraphs are verbatim-his, rephrased-from-his-answer, or Claude-composed, in iA's grey/black spirit ([iA](https://ia.net/topics/ia-writer-7)); ownership rises when the writer sees their own contribution ([arXiv 2404.00027](https://arxiv.org/html/2404.00027v3)).
9. **Consequence-first review.** The review packet should lead with the claims and numbers he is about to publish under his name, before the prose, and require a typed reason to override a gate ([TianPan](https://tianpan.co/blog/2026/04/15/human-in-the-loop-rubber-stamp)). Occasionally plant a known error in a test run to measure his catch rate.
10. **Use `/tui fullscreen` / `CLAUDE_CODE_NO_FLICKER=1` for interview sessions** and rely on `/rewind`'s "restore conversation only" to redo a bad question without losing the file ([Ship with AI Lab](https://shipwithailab.substack.com/p/claude-code-for-everything-your-terminal), [checkpointing docs](https://code.claude.com/docs/en/checkpointing)).
11. **Review on the live theme, unlisted.** Keep the Jekyll `draft: true` unlisted URL as the review surface ([Sieger](https://danielsieger.com/blog/2025/12/31/public-drafts-with-jekyll.html), [Ghost](https://ghost.org/changelog/post-previews/)); an Artifact is a reasonable second surface for reading on a phone.

## What to avoid

- Autocomplete or unsolicited suggestions during drafting; they homogenise and reduce ownership ([Agarwal et al.](https://arxiv.org/abs/2409.11360), [Who Owns the Text?](https://arxiv.org/html/2601.10236)).
- "Improve this" as an edit verb; it formalises and de-personalises even with voice-preserving instructions ([Voice Under Revision](https://arxiv.org/abs/2604.22142)).
- Style-adjective voice prompts ("blunt, measured") as the only voice input ([Sudowrite](https://sudowrite.com/blog/ai-voice-matching/)).
- Batch interviews of 10+ questions in one message (loses the conversational quality Dixit and survey research credit) and open-ended "until complete" interviews.
- Session-level "here is the whole new draft" review; per-change acceptance is what users fight to keep ([Cursor forum](https://forum.cursor.com/t/bring-back-per-change-apply-inline-diff-review-you-re-throwing-away-your-best-ux-advantage/160856)).
- Line-based `git diff` as the review artefact for prose ([Meridian](https://gitmeridian.com/markdown-diff/)).
- Track-changes-style full markup for AI insertions ([WiseChecker](https://wisechecker.com/how-to-use-copilot-in-word-with-track-changes-safely/)).
- Trusting the model's own "does this sound like you?" verdict ([NN/G sycophancy](https://www.nngroup.com/articles/sycophancy-generative-ai-chatbots/)).

## Could not verify

- ACM full texts for [Which Contributions Deserve Credit?](https://dl.acm.org/doi/full/10.1145/3706598.3713522) and [Can AI writing be salvaged?](https://dl.acm.org/doi/full/10.1145/3706598.3713559) (403); cited from search snippets only.
- Sudowrite My Voice documentation page returned 404; the feature's existence rests on the changelog snippet.
- Copilot Word native track-changes/comments integration: Windows Forum thread 403'd.
- The full list of Microsoft's 18 guidelines was not on the fetched pages; only the four categories were confirmed.
- Survey completion-rate figures (47.3%, 85% vs 22%) come from vendor blogs ([Gnosari](https://gnosari.com/blog/conversational-completion-rates)) and should not be cited as research.

## Sources

- https://www.datacamp.com/blog/chatgpt-canvas
- https://hyperdev.matsuoka.com/p/claudeais-quiet-revolution-in-artifact
- https://www.shareduo.com/blog/claude-artifacts-vs-chatgpt-canvas
- https://support.google.com/docs/answer/16558954?hl=en
- https://9to5google.com/2026/03/10/google-docs-gemini-upgrade/
- https://workspaceupdates.googleblog.com/2026/04/new-gemini-capabilities-in-google-docs-help-you-go-from-blank-page-to-brilliance.html
- https://workspaceupdates.googleblog.com/2025/10/improve-writing-gemini-google-docs-sources.html
- https://www.neowin.net/news/microsoft-words-new-coaching-with-copilot-feature-helps-you-review-and-rewrite-your-content/
- https://wisechecker.com/how-to-use-copilot-in-word-with-track-changes-safely/
- https://windowsforum.com/threads/copilot-in-word-adds-track-changes-comments-for-auditable-enterprise-reviews.413287/
- https://support.grammarly.com/hc/en-us/articles/23153676821773-Introducing-voice-features
- https://www.grammarly.com/authorship
- https://www.plagiarismtoday.com/2025/12/11/grammarly-updates-authorship-improves-labeling/
- https://www.plagiarismtoday.com/2025/11/06/how-grammarly-launders-ai-generated-content/
- https://ia.net/topics/ia-writer-7
- https://ia.net/writer/support/editor/authorship
- https://matthewcassinelli.com/ia-writer-ai-authorship-markdown-annotations/
- https://lex.page/read/3492a59e-ea19-4733-964a-3adc25b5f3e0
- https://sudowrite.com/blog/ai-voice-matching/
- https://feedback.sudowrite.com/pt/changelog/early-access-my-voice
- https://fazm.ai/blog/notion-ai-updates-2025-2026
- https://www.shadow.do/blog/best-ai-plugins-for-obsidian-2026
- https://forum.obsidian.md/t/new-plugin-obsidian-smart-composer-cursor-ai-like-editing/90016
- https://forum.cursor.com/t/bring-back-per-change-apply-inline-diff-review-you-re-throwing-away-your-best-ux-advantage/160856
- https://github.com/kirodotdev/Kiro/issues/8968
- https://gitmeridian.com/markdown-diff/
- https://arxiv.org/html/2601.10236
- https://arxiv.org/html/2504.12488v2
- https://arxiv.org/html/2404.00027v3
- https://arxiv.org/abs/2604.22142
- https://arxiv.org/abs/2409.11360
- https://arxiv.org/abs/2603.21228
- https://arxiv.org/pdf/2512.13697
- https://dl.acm.org/doi/full/10.1145/3706598.3713522
- https://dl.acm.org/doi/full/10.1145/3706598.3713559
- https://www.nngroup.com/articles/sycophancy-generative-ai-chatbots/
- https://www.nngroup.com/videos/care-for-ai-prompts/
- https://www.microsoft.com/en-us/research/project/guidelines-for-human-ai-interaction/
- https://learn.microsoft.com/en-us/training/modules/introduction-to-microsofts-responsible-ai-approach/3-use-guidelines-for-human-ai-interaction
- https://wondertools.substack.com/p/flip-the-script-on-ai
- https://github.com/Sorbh/interview-me
- https://gist.github.com/robzolkos/40b70ed2dd045603149c6b3eed4649ad
- https://dev.to/guanyi_liu_21a5d7417eb332/when-chatgpt-says-great-but-teaches-nothing-building-a-real-interview-coach-with-claude-code-50mh
- https://www.emergentmind.com/topics/socratic-questioning-for-llms
- https://arxiv.org/abs/2504.13908
- https://www.researchgate.net/publication/332741564_Comparing_Data_from_Chatbot_and_Web_Surveys_Effects_of_Platform_and_Conversational_Style_on_Survey_Response_Quality
- https://dl.acm.org/doi/fullHtml/10.1145/3381804
- https://gnosari.com/blog/conversational-completion-rates
- https://github.com/danielrosehill/Claude-Content-Writing-Plugin
- https://ccforeveryone.com/guides/claude-code-for-writers
- https://www.aaronheld.com/post/streamlining-blog-writing-with-claude-code/
- https://ndurner.github.io/writing-with-codex
- https://github.com/anthropics/claude-code/issues/42002
- https://github.com/anthropics/claude-code/issues/28077
- https://shipwithailab.substack.com/p/claude-code-for-everything-your-terminal
- https://code.claude.com/docs/en/checkpointing
- https://vercel.com/docs/comments
- https://docs.netlify.com/deploy/review-deploys/netlify-drawer-for-feedback/overview/
- https://ghost.org/changelog/post-previews/
- https://support.substack.com/hc/en-us/articles/360038433692-How-do-I-share-a-preview-of-my-post-with-others
- https://danielsieger.com/blog/2025/12/31/public-drafts-with-jekyll.html
- https://tianpan.co/blog/2026/04/15/human-in-the-loop-rubber-stamp
- https://blog.codacy.com/automation-bias-in-ai-generated-code-review-why-clean-code-still-ships-broken
