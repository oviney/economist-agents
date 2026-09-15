# AI-assisted publishing for a solo byline blog: market research

Research thread 1 of 3 for the 2026-09-15 pre-build study. Companion documents:
`2026-09-15-ux-ai-writing-interfaces.md`, `2026-09-15-workflow-blog-content.md`, and the
synthesis `2026-09-15-content-systems-synthesis.md`.

Date: 2026-09-15. Every claim carries a URL; unverifiable items are flagged inline and collected at the end.

## 1. Products and how each is designed

**Enterprise marketing suites (Jasper, Copy.ai, Writer, Typeface, HubSpot Breeze).** All five are built for teams producing volume against a brand-voice profile. Jasper's own pricing page lists Pro at $69/mo monthly, $59/mo annual, with "2 voices" and "5 multi-modal knowledge assets"; Business (custom, 12-month minimum) unlocks unlimited voices and a Style Guide ([jasper.ai/pricing](https://www.jasper.ai/pricing)). Voice is a profile derived from up to eight samples ([eesel review](https://www.eesel.ai/blog/jasper-ai-review-2026)); reviewers repeatedly conclude solo creators "get 90% of the value from ChatGPT or Claude" ([aiworthit](https://www.aiworthit.com/blog/jasper-ai-review/)). Copy.ai has left writing altogether and calls itself a GTM platform: Chat $29/mo, Agents $249/mo, tiers to $3,000/mo; reviewers say "prose quality on freeform writing trails Claude" ([eesel](https://www.eesel.ai/blog/copy-ai), [thestacc](https://thestacc.com/reviews/copy-ai/)). Writer sells governed "Playbooks" on its own Palmyra models; Starter $39/user/mo, enterprise deals reported at $500K+ ([eesel](https://www.eesel.ai/blog/writer-com-pricing)). Typeface is custom-priced, reported $100K–$1M+/yr, and trains a private brand model from tone guidelines and product data ([eesel](https://www.eesel.ai/blog/typeface-ai)). HubSpot's Breeze Content Agent drafts from CRM data; practitioner reviews say output "typically needs significant editing to match your brand voice" and that setting the brand voice explicitly is "the difference between AI-generic and passable-first-draft" ([hublead](https://www.hublead.io/blog/hubspot-breeze-ai), [pedowitz](https://www.pedowitzgroup.com/blog/hubspot-ai-tools-2026-blog)). None of these is designed around the author's lived experience; the "voice" abstraction is a style layer over generated content.

**Writer-first editors (Lex, Sudowrite, Spiral).** Lex is a distraction-free editor: type `++` for a continuation, ask for feedback checks; Claude and GPT under the hood; free tier with limited checks, Pro roughly $12–18/mo (secondary sources disagree on exact numbers; lex.page/pricing did not list prices when fetched) ([buildfastwithai](https://www.buildfastwithai.com/ai-tools/lex), [lex.page/pricing](https://lex.page/pricing)). Sudowrite is fiction-only, credit-metered, $10–59/mo ([builtwritten](https://www.builtwritten.com/blog/sudowrite-ai-2026)). **Spiral (Every)** is the closest commercial analogue to the proposed workflow: it "asks what you're actually trying to say before it writes anything," runs a collaborative interview, shows three drafts side by side, learns voice by stylometry from uploaded samples or connected social accounts, and exposes itself over MCP to Claude Code, Cursor and ChatGPT. Personal $15/mo, Team $25/user/mo, Every bundle $30/mo ([writewithspiral.com](https://writewithspiral.com/), [Spiral v3 launch, 2025-10-21](https://every.to/on-every/introducing-spiral-v3-an-ai-writing-partner-with-taste)). Third-party listings quoting $199/mo are stale ([selecthub](https://www.selecthub.com/p/ai-writing-assistant-software/spiral-ai/)).

**Publishing platforms.** beehiiv bundles a writing assistant, tone changer, subject-line generator and image generator ([indie-ai-stack](https://indie-ai-stack.com/blog/07_best-ai-newsletter-tools/)). Substack has no AI writing features but in July 2026 integrated Pangram AI-detection so readers can scan any post >100 characters, plus an optional "How I make this" author statement; CEO Chris Best framed it as encouraging disclosure, not penalising use ([TechCrunch, 2026-07-22](https://techcrunch.com/2026/07/22/substacks-new-tool-tells-you-whos-been-writing-their-newsletters-with-ai/)). Gergely Orosz called it "a great initiative … When I know that something is AI-written, I just don't take time to read it" ([on.substack.com, 2026-07-24](https://on.substack.com/p/how-writers-are-reacting-to-substacks)). Ghost ships no AI in the editor; a July 2026 forum thread asking for Ghost's stance got no official answer ([forum.ghost.org](https://forum.ghost.org/t/ghost-stance-on-ai/63383)). Medium bars AI-generated writing (majority AI, little editing) from the paywall since 2024-05-01 and does not distribute it; AI-assisted (grammar, outlining) needs no disclosure ([onlinewritingclub](https://www.onlinewritingclub.com/p/mediums-new-rules-for-ai-generated), [seo.ai](https://seo.ai/blog/medium-com-is-saying-no-ai-content)). Medium's own help page returned 403; treat details as secondary.

**Creator/social tools.** Typefully has a Claude-powered writing assistant and a "voice-matched AI" tier reported around $10–12.50/mo ([posteverywhere](https://posteverywhere.ai/blog/25-best-ai-tools-for-threads), [voicemoat](https://voicemoat.com/compare/best-twitter-tools-2026)); its pricing page did not render, so unverified. Hypefury dropped X support in August 2026 and pivoted to video-to-Threads agents ([xholic](https://xholic.ai/blog/hypefury-vs-tweethunter-vs-xholic/)). Buffer is a scheduler with AI bolt-ons.

**Voice-to-text.** Wispr Flow: Free tier, Pro $12–15/mo, "learns your names and jargon" ([wisprflow.ai/pricing](https://wisprflow.ai/pricing)); a developer reviewer dictates first drafts and PR descriptions with it, 184 wpm, no Linux client ([zackproser, 2026-08-01](https://zackproser.com/blog/wisprflow-review)). AudioPen: "ramble freely," rewrite intensity Low/Medium/High, custom styles, Prime $99/yr, 15-minute cap ([audiopen.ai](https://audiopen.ai/)). Descript's Underlord drafts scripts and show notes from recordings; Creator $24/mo annual ([shade](https://shade.inc/blog/descript-pricing), [descript.com](https://www.descript.com/blog/article/descript-season-6-meet-underlord)). Castmagic turns one recording into blog drafts with a custom style-guide prompt workspace ([coldiq](https://coldiq.com/tools/castmagic)).

**Second-brain tools.** Kortex is migrating to "Eden" (beta.eden.so); reviews praise writer-first minimalism, 5 GB free ([allbestapps](https://allbestapps.net/ai-app/kortex/)). Obsidian: Copilot plugin ~7.7k stars ([github](https://github.com/logancyang/obsidian-copilot/issues)); Smart Connections ~5.2k stars, 1M downloads, "a finder, not a writer" ([shadow.do](https://www.shadow.do/blog/best-ai-plugins-for-obsidian-2026)); reviewers now recommend Claude Code over the vault via MCP as the active writing surface ([nxcode](https://www.nxcode.io/resources/news/obsidian-ai-second-brain-complete-guide-2026)).

**General chat products.** Notion AI is now bundled only in Business ($20/user/mo) after the $10 add-on was retired ([eesel](https://www.eesel.ai/blog/notion-pricing)). ChatGPT Canvas is judged the better inline prose editor; Claude Artifacts the better builder; Gemini Canvas is catching up ([unmarkdown](https://unmarkdown.com/blog/claude-artifacts-vs-chatgpt-canvas), [canvaslink](https://canvaslink.app/blog/claude-artifacts-vs-chatgpt-canvas-vs-gemini-canvas)). Claude's custom Styles learn from uploaded samples and are migrating into Skills in 2026 ([anthropic.com/news/styles](https://www.anthropic.com/news/styles), [ai-toolbox](https://www.ai-toolbox.co/claude-management-and-productivity/how-to-set-up-claude-custom-instructions-2026)).

### Comparison table

| Product | Audience | Interaction model | Voice handling | Pricing | Distinctive |
|---|---|---|---|---|---|
| Jasper | Marketing teams 3+ | Templates + chat + agents | Profile from ≤8 samples; 2 voices on Pro | $59–69/mo; Business custom | Style Guide governance |
| Copy.ai | Sales/RevOps | Workflow builder | Infobase context | $29 → $3,000/mo | Left writing for GTM |
| Writer | Enterprise | Governed Playbooks | Rules: terms, forbidden phrases, dept. voices | $39/user; $500K+ ent. | Own Palmyra models |
| Typeface | Large brands | Arc agents/spaces | Private brand model | $100K–$1M+/yr | Multimodal brand assets |
| HubSpot Breeze | HubSpot SMBs | Agent drafts from CRM | Brand-voice setting; needs heavy edit | Content Hub tiers | CRM-grounded |
| Lex | Essayists, bloggers | Editor; `++` continue; checks | Model-level, no explicit profile | Free; Pro ~$12–18/mo | Quiet editor, Claude+GPT |
| Sudowrite | Novelists | Story tools, credits | Learns manuscript style | $10–59/mo | Fiction craft |
| Spiral | Newsletter/personal-brand writers | Interview → 3 drafts → pick | Stylometry from samples/social; MCP | $15/mo; bundle $30 | Interview-first, agent-native |
| beehiiv | Newsletter ops | Assistant in editor | Tone changer | Platform tiers | Subject-line uplift |
| Substack | Writers | No AI writing; Pangram scans | "How I make this" statement | Free/rev-share | Reader-side detection |
| Ghost | Indie publishers | None | BYO | Hosted or OSS | Deliberately AI-free |
| Medium | Writers | None | n/a | Partner Program | AI-generated barred from paywall |
| Typefully | X/LinkedIn creators | Compose + AI assistant | "Voice-matched" tier (unverified) | ~$10–12.50/mo | Cleanest compose UI |
| Wispr Flow | Anyone dictating | System-wide dictation | Personal dictionary | Free; $12–15/mo | 4x typing speed; no Linux |
| AudioPen | Thinkers-out-loud | Ramble → rewrite | Custom styles, intensity dial | $99/yr | Cheapest, 15-min cap |
| Descript/Castmagic | Podcasters | Transcript-based editing/repurposing | Style-guide prompts | $16–50/mo | Recording → many assets |
| Obsidian + Copilot/Claude Code | Devs, PKM users | Vault RAG; MCP | Whatever you write into rules | Free + subscription | Local-first, editable |
| Claude/ChatGPT/Gemini | Everyone | Chat + canvas/artifacts + projects | Claude Styles from samples | $20/mo | You already pay for this |

## 2. Market trend

The market is bifurcating. Enterprise tools are chasing volume and agents; the writer-facing end is moving to *verification and disclosure*. Google's spam policy explicitly lists "using generative AI tools … to generate many pages without adding value" under scaled content abuse ([spam policies](https://developers.google.com/search/docs/essentials/spam-policies)), and its helpful-content guidance asks Who/How/Why, demanding "first-hand expertise … from having actually used a product or service" and disclosure of "why automation or AI was seen as useful" ([creating-helpful-content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)). The Quality Rater Guidelines were revised 2025-09-11, keeping Experience as the first E ([theguidex](https://theguidex.com/google-quality-rater-guidelines-summary)). **Flag:** SEO blogs claim the March 2026 core update "explicitly named scaled content abuse"; Google's status page says only "Released the March 2026 core update" ([status.search.google.com](https://status.search.google.com/incidents/7eTbAa2jWdToLkraZj5y)). Treat the 50–80% traffic-drop figures as unverified.

Reader-trust data: Reuters DNR 2026 puts trust in AI-chatbot news at 20% globally versus 37% for news overall ([Reuters Institute](https://reutersinstitute.politics.ox.ac.uk/digital-news-report/2026/dnr-executive-summary)). Fortune (2026-06-05) cites Gartner (53% distrust AI search results) and a global survey (70% uncomfortable with AI media), with Hachette withdrawing a novel over AI passages ([Fortune](https://fortune.com/2026/06/05/war-ai-slop-publicis-groupe-hachette-publishers-association/)). A TRG Datacenters analysis reported "AI slop" mentions at 2.4M (82% negative) and 40% of consumers saying heavy AI use lowers brand trust; methodology is thin ([storyboard18](https://www.storyboard18.com/digital/ai-fatigue-rises-in-2026-as-consumer-excitement-drops-to-19-report-95162.htm)). Originality.AI classified 81.2% of 5,000 public LinkedIn posts as "likely AI" in July 2026; LinkedIn is rolling out a "Seems like AI slop" report button (vendor sells detection, so discount) ([originality.ai](https://originality.ai/blog/linkedin-ai-study-engagement)).

Engagement evidence is mixed and mostly vendor-published. Picmim's 10,024-post study found AI-assisted (human-edited) posts got 31% more engagement, but the AI accounts posted twice as often and Picmim sells the tool ([picmim](https://blog.picmim.com/blog/we-analyzed-10000-posts-ai-vs-human-content-performance-2026-data-study)). The one peer-reviewed study (PLOS One, 2026-03-25, n=366 across 11 countries) found AI research blogs rated marginally lower on quality, a penalty "almost completely offset" by honest disclosure, and no effect on engagement intent ([PLOS One](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0342852)). Net: no clean evidence that AI drafts lose engagement; consistent evidence that undisclosed or detectable AI costs trust, and that disclosure is cheap insurance.

## 3. "Extract the author's thinking" niche

- **Spiral** (above) is the flagship: interview, push-back, three drafts, stylometric voice, MCP into Claude Code. Adopted by Lenny Rachitsky, Ben Tossell ([producthunt](https://www.producthunt.com/products/spiral-8)); criticisms are generic (dependence, needs manual review) ([selecthub](https://www.selecthub.com/p/ai-writing-assistant-software/spiral-ai/)).
- **SocraDraft (hisocra)** claims to organise voice input and then "begins asking questions specific to your argument"; the page 403'd, so unverified ([hisocra](https://hisocra.com/blog/voice-to-blog-post-ai-workflow)).
- **Cleve** builds a "working memory" from voice notes/docs and drafts posts in your tone; 40K users, pricing not on the page ([cleve.ai](https://www.cleve.ai/)).
- **AudioPen, Wispr Flow, VoicePen, Castmagic** cover the talk-to-text leg without the interview leg ([voicepen](https://voicepen.ai/)).
- Reception signal: one 2026 newsletter-ops guide says the 2024–25 wave of "writes your newsletter in your voice" tools "none survived more than 8 weeks" in the author's stack ([lilachbullock](https://www.lilachbullock.com/ai-for-newsletter-operators/)); a Substack commenter's objection to detection, "who had the original thought, who lived the experience," is precisely the value an interview workflow preserves ([on.substack.com](https://on.substack.com/p/how-writers-are-reacting-to-substacks)).

## 4. Open-source and developer projects

- **nadiem99/claude-writing-skills** — 11 Claude Code skills: interview (one-question-at-a-time Socratic), outline, draft, coach, edit, source-check, top-edit, repurpose; draft skill must read `context/voice-notes.md` and state what it calibrates against; after each top-edit it proposes additions to the voice notes. Built for Substack + Obsidian + Readwise. MIT, 2 stars, 3 commits ([github](https://github.com/nadiem99/claude-writing-skills)). Tiny, but the closest design match to the proposed workflow.
- **blader/humanizer** — 33.7k stars; strips AI tells using Wikipedia's AI-writing guide and rewrites toward pasted samples of your own writing. **hardikpandya/stop-slop** — 15.2k stars; phrase bans and a 1–10 directness/authenticity score ([analyticsvidhya, 2026-08](https://www.analyticsvidhya.com/blog/2026/08/top-5-claude-writing-skills/)). The two most-starred writing skills are *de-AI-ing* tools, which says where the pain is.
- **AgriciDaniel/claude-blog** — 1.6–2.1k stars, 32 skills, 5 agents, 5 quality gates, `/blog write <topic>`; optimised for SEO and AI citations, not author voice ([github](https://github.com/AgriciDaniel/claude-blog)).
- **IrtezaAsadRizvi/article-writing-skills** — persona prompts "modelled on famous engineers" ([github](https://github.com/IrtezaAsadRizvi/article-writing-skills)); the opposite of owner voice.
- Topic-to-commit tutorials exist ([claudecodeguides](https://claudecodeguides.com/claude-skills-automated-blog-post-workflow-tutorial/)); they generate from a topic, not from the author.
- Voice capture: **drajb/whisper-local** (offline Wispr alternative, Windows/macOS), **OpenWhispr** (local Parakeet/Whisper, cross-platform), a fully local Faster-Whisper-to-Obsidian pipeline ([github topics](https://github.com/topics/whisper-cpp?o=asc&s=stars), [OpenWhispr](https://github.com/OpenWhispr/openwhispr), [medium](https://medium.com/@textmaster.rf/how-i-built-a-fully-local-voice-to-obsidian-pipeline-no-cloud-no-api-keys-no-nonsense-33354341d6f0)). All keyless.

## 5. What practitioners say

- **Simon Willison** (2026-03-01): "if text expresses opinions or has 'I' pronouns attached to it then it's written by me"; LLMs allowed for READMEs and proofreading, and he strips AI-written rationales ([simonwillison.net](https://simonwillison.net/2026/Mar/1/ai-writing/)). Earlier: "I don't like letting LLMs write for me … sophisticated readers can sniff out LLM-generated text, which inevitably hurts your credibility"; uses them "as a thesaurus, as a proofreader and occasionally to check that the argument … does not have any embarrassing holes" ([writethatblog, 2026-01-15](https://writethatblog.substack.com/p/simon-willison-on-technical-blogging)).
- **Gergely Orosz** (AMA, 2026-07-08): "I choose to use zero AI in my writing for the Pragmatic Engineer, and Grammarly is turned off as well," to keep the skill from deteriorating ([pragmaticengineer](https://newsletter.pragmaticengineer.com/p/the-pragmatic-engineer-ama)).
- **Charity Majors** (2026-09-14): a "violent disgust reflex" at AI text in relational communication; AI is fine for functional text, a trust breach for opinions and personal messages ([charity.wtf](https://charity.wtf/p/confessions-of-an-unrepentant-slop)).
- **swyx** (2026-01-23): "the most important problem in media now is scaling without slop"; AI News is agent-summarised, but Latent Space's answer is more human curators and "saying no a lot," not more generation ([latent.space](https://www.latent.space/p/2026)).
- **Will Larson** (2025-06-14): uses Claude Projects loaded with his own writing to answer reader questions and package "datapacks"; does not describe drafting essays with LLMs ([lethain](https://lethain.com/competitive-advantage-author-llms/)).
- **Kent Beck** (2024-01): "tuning a model based on all of my writings" for Q&A, plus AI illustrations; no claim of LLM-drafted essays ([kentbeck](https://newsletter.kentbeck.com/p/exploring-ai)).
- **Julia Evans** (Mastodon, 2026-02-23): "not doing the creative stuff is giving up on the things that bring me the most happiness"; LLMs "very good at doing things that have been done before" ([social.jvns.ca](https://social.jvns.ca/@b0rk/116120098443249108)). Full text could not be fetched; quotes are from the search excerpt.
- **Dan Abramov**: no 2025–26 post about AI in writing on overreacted.io ([overreacted.io](https://overreacted.io/)). Nothing to cite.

Pattern: every named engineer-writer either bans LLM prose outright or confines it to functional text and checking. None describes an interview-to-draft workflow. The proposed build sits in the gap between their position (my opinions, my words) and Spiral's (AI drafts in your voice).

## What to copy / what to avoid

**Copy**
1. Spiral's ordering: interview and push-back *before* any drafting; multiple candidate drafts to choose between rather than one to edit.
2. nadiem99's `voice-notes.md` loop: the draft skill declares which voice patterns it used, and the edit pass proposes new notes. Cheap, inspectable, no model training.
3. Willison's rule as a hard gate: first-person and opinion sentences must trace to something the owner said in the interview. The existing stat audit ("no number not in the brief") is the same idea; extend it to claims and "I" statements.
4. Substack's "How I make this": ship a one-line process disclosure on every post. PLOS One shows disclosure erases the quality penalty.
5. humanizer/stop-slop as a final gate: AI-tell and phrase-ban checks are the most-demanded open-source writing feature.
6. Voice capture keyless: Wispr Flow's free tier or a local Whisper tool for the interview answers; no need for AudioPen.
7. Google's Who/How/Why: byline, process, first-hand experience. The brief template already asks for experiences; keep that mandatory.

**Avoid**
1. Topic-in, post-out pipelines (claude-blog, HubSpot Breeze, the Claude Code tutorials). Every reviewer says the output "needs significant editing"; every practitioner says readers detect it.
2. Persona prompts ("write like Kent Beck"). Wrong direction entirely.
3. Brand-voice-as-profile abstraction (Jasper/Writer). A style layer over generated content is what the market is backlashing against; the owner's voice comes from his sentences, not a tone setting.
4. SEO/AI-citation gates and rubric scores as the definition of done; Medium and Substack now treat that output as second-class.
5. Volume. LinkedIn is 81% likely-AI; the differentiator is scarcity of a real opinion, not cadence.
6. Any dependency that reintroduces a key: Spiral's MCP is attractive but is a $15/mo third-party service, out of scope.

**Could not verify:** Typefully's current pricing and voice tier; Medium's official policy page (403; 2024 secondary coverage used); SocraDraft's interview claim (403); Julia Evans' full post; the TRG Datacenters method; claims that Google's March 2026 core update named scaled content abuse; Kortex's Eden migration status; Lex's exact plan prices.

## Sources

- https://www.jasper.ai/pricing
- https://www.eesel.ai/blog/jasper-ai-review-2026
- https://www.aiworthit.com/blog/jasper-ai-review/
- https://www.eesel.ai/blog/copy-ai
- https://thestacc.com/reviews/copy-ai/
- https://www.eesel.ai/blog/writer-com-pricing
- https://www.eesel.ai/blog/typeface-ai
- https://www.hublead.io/blog/hubspot-breeze-ai
- https://www.pedowitzgroup.com/blog/hubspot-ai-tools-2026-blog
- https://www.buildfastwithai.com/ai-tools/lex
- https://lex.page/pricing
- https://www.builtwritten.com/blog/sudowrite-ai-2026
- https://writewithspiral.com/
- https://every.to/on-every/introducing-spiral-v3-an-ai-writing-partner-with-taste
- https://www.producthunt.com/products/spiral-8
- https://www.selecthub.com/p/ai-writing-assistant-software/spiral-ai/
- https://indie-ai-stack.com/blog/07_best-ai-newsletter-tools/
- https://techcrunch.com/2026/07/22/substacks-new-tool-tells-you-whos-been-writing-their-newsletters-with-ai/
- https://on.substack.com/p/how-writers-are-reacting-to-substacks
- https://forum.ghost.org/t/ghost-stance-on-ai/63383
- https://www.onlinewritingclub.com/p/mediums-new-rules-for-ai-generated
- https://seo.ai/blog/medium-com-is-saying-no-ai-content
- https://posteverywhere.ai/blog/25-best-ai-tools-for-threads
- https://voicemoat.com/compare/best-twitter-tools-2026
- https://xholic.ai/blog/hypefury-vs-tweethunter-vs-xholic/
- https://wisprflow.ai/pricing
- https://zackproser.com/blog/wisprflow-review
- https://audiopen.ai/
- https://shade.inc/blog/descript-pricing
- https://www.descript.com/blog/article/descript-season-6-meet-underlord
- https://coldiq.com/tools/castmagic
- https://voicepen.ai/
- https://hisocra.com/blog/voice-to-blog-post-ai-workflow
- https://www.cleve.ai/
- https://www.lilachbullock.com/ai-for-newsletter-operators/
- https://allbestapps.net/ai-app/kortex/
- https://github.com/logancyang/obsidian-copilot/issues
- https://www.shadow.do/blog/best-ai-plugins-for-obsidian-2026
- https://www.nxcode.io/resources/news/obsidian-ai-second-brain-complete-guide-2026
- https://www.eesel.ai/blog/notion-pricing
- https://unmarkdown.com/blog/claude-artifacts-vs-chatgpt-canvas
- https://canvaslink.app/blog/claude-artifacts-vs-chatgpt-canvas-vs-gemini-canvas
- https://www.anthropic.com/news/styles
- https://www.ai-toolbox.co/claude-management-and-productivity/how-to-set-up-claude-custom-instructions-2026
- https://developers.google.com/search/docs/essentials/spam-policies
- https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- https://status.search.google.com/incidents/7eTbAa2jWdToLkraZj5y
- https://theguidex.com/google-quality-rater-guidelines-summary
- https://www.digitalapplied.com/blog/scaled-content-abuse-google-march-update-ai-pages-decimated
- https://reutersinstitute.politics.ox.ac.uk/digital-news-report/2026/dnr-executive-summary
- https://fortune.com/2026/06/05/war-ai-slop-publicis-groupe-hachette-publishers-association/
- https://www.storyboard18.com/digital/ai-fatigue-rises-in-2026-as-consumer-excitement-drops-to-19-report-95162.htm
- https://originality.ai/blog/linkedin-ai-study-engagement
- https://blog.picmim.com/blog/we-analyzed-10000-posts-ai-vs-human-content-performance-2026-data-study
- https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0342852
- https://github.com/nadiem99/claude-writing-skills
- https://www.analyticsvidhya.com/blog/2026/08/top-5-claude-writing-skills/
- https://github.com/AgriciDaniel/claude-blog
- https://github.com/IrtezaAsadRizvi/article-writing-skills
- https://claudecodeguides.com/claude-skills-automated-blog-post-workflow-tutorial/
- https://github.com/topics/whisper-cpp?o=asc&s=stars
- https://github.com/OpenWhispr/openwhispr
- https://medium.com/@textmaster.rf/how-i-built-a-fully-local-voice-to-obsidian-pipeline-no-cloud-no-api-keys-no-nonsense-33354341d6f0
- https://simonwillison.net/2026/Mar/1/ai-writing/
- https://writethatblog.substack.com/p/simon-willison-on-technical-blogging
- https://newsletter.pragmaticengineer.com/p/the-pragmatic-engineer-ama
- https://charity.wtf/p/confessions-of-an-unrepentant-slop
- https://www.latent.space/p/2026
- https://lethain.com/competitive-advantage-author-llms/
- https://newsletter.kentbeck.com/p/exploring-ai
- https://social.jvns.ca/@b0rk/116120098443249108
- https://overreacted.io/
