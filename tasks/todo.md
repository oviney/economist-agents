# TODO: Keyless subscription pipeline (B-006)

**Plan**: [`tasks/plan.md`](./plan.md) · **Spec**: [`docs/specs/B-006-keyless-subscription-pipeline.md`](../docs/specs/B-006-keyless-subscription-pipeline.md)
**Status**: awaiting LGTM on the plan before starting.

## Todo (dependency-ordered)

- [ ] **T0** — Env: reliable keyless `claude-agent-sdk` install + document `IS_SANDBOX=1` under root
- [ ] **T1** — `src/agent_sdk/research/claude_web.py` → `build_claude_web_brief()` (WebSearch/WebFetch) + test
- [ ] **T2** — Wire `research_mode="claude_web"` through `stage3_runner` + `pipeline` + CLI + test
- [ ] **— CHECKPOINT A —** keyless article via mocked test; show green, get go
- [ ] **T3** — Reroute `refine_image_metadata` to `query()` vision, drop key gate + test
- [ ] **T4** — `economist_agent.py` fail-loud keyless message + test
- [ ] **T5** — ADR: LLM-in-research keyless mode
- [ ] **T6** — Runbook doc + `BACKLOG.md` B-006 + install fix
- [ ] **— CHECKPOINT B —** live keyless subscription run → `publication_validator` exit 0

## Done

_(none yet)_
