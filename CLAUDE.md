# Economist-Agents

Multi-agent content pipeline that generates Economist-style articles with verified sources.

## Operating Constraints (NON-NEGOTIABLE — read before proposing anything)

The owner has stated these repeatedly. Violating them is a hard failure, not a
judgement call. **Never** propose, add, wire, or require a solution that breaks
one of these, and never re-litigate them.

1. **NO new API keys. Ever.** This includes "free-tier" keys (they expire and
   require setup/maintenance the owner will not do). Do not propose DALL-E,
   OpenAI, Serper, Gemini/Imagen, or *any* service that needs an API key.
   `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `SERPER_API_KEY`, `GEMINI_API_KEY`,
   etc. are all forbidden as a requirement.
2. **NO paid third-party services.** No new subscriptions, no metered APIs.
3. **The only LLM auth is the Claude subscription** via the Agent SDK
   (`claude_agent_sdk` / the authenticated `claude` CLI). The default runtime is
   keyless: writing/graphics/vision via `query()`, research via
   `research_mode="claude_web"` (Claude's own WebSearch), never Serper.
4. **The pipeline does NOT generate the hero image — it generates a PROMPT.**
   The hero workflow is human-in-the-loop at PR-review time:
   (a) the pipeline writes a hero-image *prompt* (`image_prompt_synth.py` →
   `compose_prompt`), surfaces it in the post (inline placeholder comment) and
   as the `output/posts/<slug>.image_prompt.md` sidecar so it is visible when
   reviewing the post in the PR; (b) the owner takes that prompt, generates the
   image themselves, and drops it in. Do **not** add image generation of any
   kind — not DALL-E/Gemini/Midjourney (violates #1), and not procedural/PIL
   image generation either. The only pipeline-drawn raster is the **data chart**
   (`chart_renderer.py`, matplotlib), which is not an illustration.
5. **No github.com-only workflows for running the pipeline.** It must run
   locally / in the session on the subscription.

If a task *seems* to need a key or a paid service, the answer is "do it keyless
or say it cannot be done keyless" — not "add a key". Encode any new constraint
the owner gives into this section immediately.

## Default Operating Mode

Every task follows the `skills/using-agent-skills` discovery flowchart before any code is written:

```
Task arrives
  ├── Vague idea?              → skills/idea-refine (clarify first)
  ├── New feature/change?      → skills/spec-driven-development (spec → human review → plan → human review → implement)
  ├── Have a spec, need tasks? → skills/planning-and-task-breakdown (dependency graph → human review)
  ├── Implementing?            → skills/incremental-implementation (thin slices, each tested + committed)
  ├── Deploying?               → skills/shipping-and-launch (pre-launch checklist, staged rollout)
  └── Bug / defect?            → log in defect_tracker → spec → fix → regression test
```

**No implementation starts without a spec. No sprint planning starts without a dependency-ordered task list.**
Both require human review (a "LGTM") before proceeding.

### Backlog & Issue Tracking (hybrid model)

The backlog is **local-first**. The `github` MCP server has been removed (it was a
token drain); see `docs/specs/local-backlog-migration.md`.

- **Backlog / planning items → `BACKLOG.md`** at repo root. This is the source of
  record for todo / in-progress / done work items (`B-NNN` ids). Edit the file
  directly; do **not** open GitHub issues for new backlog items.
- **PRs + code review → GitHub via the `gh` CLI** (authenticated, near-zero context
  cost). `gh pr create / view / list` etc. remain the standard PR workflow.
- **Bugs / defects** still log in `data/skills_state/defect_tracker.json` per the
  flowchart above, then graduate to a `BACKLOG.md` item if they need scheduling.
- `data/skills_state/backlog.json` is **machine state for autonomous sprint scripts**
  (keyed by `STORY-NNN`) — not the human backlog. Don't conflate the two.

### Lifecycle discipline (non-negotiable)

For any **non-trivial** response (anything beyond Q&A, status checks, or one-line edits):

1. The **first two tool calls** MUST be:
   1. `Skill agent-skills:using-agent-skills` — triages the task and points to the right phase skill
   2. `Skill agent-skills:context-engineering` — sets up focused context for the task
2. After triage, invoke the phase skill the meta-skill points you at (e.g. `agent-skills:spec-driven-development`, `agent-skills:incremental-implementation`, `agent-skills:test-driven-development`, etc.).
3. **Improvising the lifecycle as plain workflow labels is a blocker, not a warning.** If you find yourself running DEFINE/PLAN/BUILD by hand without an active `Skill` invocation, stop and invoke the meta-skill first.
4. Per `agent-skills:using-agent-skills` Core Behavior #1: surface assumptions explicitly before implementing anything non-trivial.

Exempt: simple Q&A, status checks, command output, one-line edits.

### Skill Routing Contract (non-negotiable)

Skill routing follows the upstream agent-skills guide
(https://github.com/addyosmani/agent-skills/blob/main/docs/getting-started.md)
as the **single source of truth** for skill semantics and lifecycle. This
governs how the next skill is chosen — especially when the user asks "what
agent-skill should we use next?" (see #405).

1. **Only `SKILL.md` workflows are agent-skills.** Plugin commands, MCP tools,
   GitHub plugin skills (e.g. `github:yeet`), and repo-local agent personas
   (e.g. `@git-operator`) are **never** agent-skills and must never be presented
   as the next skill.
2. **Follow the lifecycle phase order** — do not invent substitutes:

   | Phase | Skill |
   |-------|-------|
   | `/spec` | `spec-driven-development` |
   | `/plan` | `planning-and-task-breakdown` |
   | `/build` | `incremental-implementation` + `test-driven-development` |
   | `/test` | `test-driven-development` |
   | `/review` | `code-review-and-quality` |
   | `/ship` | `shipping-and-launch` |

3. **Missing-skill rule.** If the next lifecycle skill is not installed locally,
   say so explicitly — e.g. "The next agent-skill is `shipping-and-launch`, but
   it is not installed here; we should add it before proceeding" — rather than
   substituting a plugin skill, MCP tool, or repo persona.
4. **Answer by name.** When asked for the next skill, name the lifecycle's next
   phase skill (or state the install gap per rule 3). Nothing else.

The six lifecycle skills are currently installed under `skills/`.

### Dispatching worker agents

When dispatching agents via the `Agent` tool (orchestrating the fleet), the brief MUST include the worker discipline contract from `docs/worker-brief-contract.md`. Workers that produce output without evidence of `Skill` invocations are rejected and re-dispatched.

## Architecture

- **LLM**: Claude (Anthropic) is the primary LLM. OPENAI_API_KEY only needed for DALL-E images.
- **Research**: Deterministic academic search via free, keyless providers only — arXiv + Semantic Scholar. No LLM and no pay-per-use APIs in the research path.
- **Writing**: Claude via Anthropic Agent SDK (`src/agent_sdk/stage3_runner.py`).
- **Quality gates**: Deterministic post-processing in `src/agent_sdk/stage4_runner.py`, then `scripts/publication_validator.py`.
- **Orchestration**: `src/economist_agents/flow.py` — sequential pipeline over `src.agent_sdk.pipeline.run_pipeline`.

## Directory Structure

```
agents/skills_configs/    # Agent YAML configs (research-analyst, content-writer, etc.)
data/skills_state/        # Runtime state JSON (sprint tracker, metrics, defect tracker)
skills/*/SKILL.md         # Skill workflow definitions (39 skills — see Key Skills below)
src/agent_sdk/            # Anthropic Agent SDK runners (stage3, stage4, pipeline, _shared)
src/economist_agents/     # Flow orchestration, adapters
scripts/                  # Standalone scripts (publication_validator, citation_verifier, etc.)
```

## Code Standards

Type hints mandatory. Docstrings required. Use `orjson` not `json`.
`logger` not `print()`. Mock APIs in tests. >80% coverage required.

See `skills/python-quality/SKILL.md` for complete standards.

## Quality Gates (enforced deterministically)

1. **Stat audit** (`_shared.py`): strips sentences with stats not in the research brief
2. **Category normalization** (`_shared.py`): normalises to Title Case
3. **Description truncation** (`_shared.py`): caps at 160 chars
4. **Heading limit** (`_shared.py`): merges sections when >4 headings
5. **Hedging removal** (`_shared.py`): strips "One suspects", "it is worth noting", etc.
6. **Ending validation** (`publication_validator.py`): flags summary endings (HIGH severity)
7. **Chart auto-embed** (`_shared.py`): inserts chart before References if missing
8. **British spelling** (`_shared.py`): American → British replacements
9. **Publication validator** (`publication_validator.py`): frontmatter, categories, word count, author, image metadata, placeholders

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `BLOG_REPO_TOKEN` | To publish | Free GitHub token (push to `oviney/blog`) so the deploy step can open a PR. No AI key. |

The keyless path uses **no paid AI keys**. Writing/graphics/vision run on the
Claude subscription via the Agent SDK; research uses free keyless providers
(arXiv + Semantic Scholar). There is **no `OPENAI_API_KEY`/DALL-E path** — hero
images are human-supplied per constraint #4, and the DALL-E workflow was retired
(ADR-0014 / B-009). Pay-per-use search APIs (Serper/Google, Brave, Tavily) were
removed by #438.

> Note: a legacy paid path still exists — `EconomistContentFlow` Stage 1 topic
> discovery calls `create_llm_client`, which needs `ANTHROPIC_API_KEY`
> (BUG-046). Making the full flow keyless is tracked in **B-010**; until then the
> keyless generator is `python -m src.agent_sdk.pipeline` (manual topic). See
> `docs/keyless-pipeline-runbook.md`.

## Key Skills

### Workflow (addyosmani/agent-skills — governs all work)
- `skills/using-agent-skills/SKILL.md` — Meta-skill: maps task type to the right skill
- `skills/context-engineering/SKILL.md` — Focus context at session start
- `skills/idea-refine/SKILL.md` — Clarify vague requests before speccing
- `skills/spec-driven-development/SKILL.md` — Spec → human review → plan → human review → implement
- `skills/planning-and-task-breakdown/SKILL.md` — Dependency graph before sprint planning
- `skills/incremental-implementation/SKILL.md` — Thin slices, each tested and committed
- `skills/test-driven-development/SKILL.md` — RED → GREEN → REFACTOR
- `skills/code-review-and-quality/SKILL.md` — Multi-axis review before merge
- `skills/shipping-and-launch/SKILL.md` — Pre-launch checklist, staged rollout, rollback

### Domain
- `skills/economist-writing/SKILL.md` — The 10 writing rules
- `skills/python-quality/SKILL.md` — Code standards
- `skills/defect-prevention/SKILL.md` — Pattern → rule → test cycle
- `skills/agent-delegation/SKILL.md` — Agent assignment rules
- `skills/architecture-patterns/SKILL.md` — CrewAI/AutoGen patterns, audit rubric
