# Economist Agents

**A keyless pipeline that turns the owner's take on a quality-engineering topic into a
published post on [viney.ca](https://www.viney.ca).** One writer, one prompt, one owner.

![Verification](https://img.shields.io/badge/verification-local--first-blue)
![Python](https://img.shields.io/badge/Python-3.12-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

The name is a misnomer: the Economist identity was retired by [ADR-0020](docs/adr/0020-the-owners-voice-is-the-input-not-the-gate.md).

## How it works

```
briefs/<slug>.md ──► research (claude_web) ──► write ──► gates ──► review packet
  the owner's take     evidence for and        one Claude   blocking +   what to draw,
                       against it, named       call, first  advisory     what to fix,
                       cases; no key           person       findings     where to deploy
```

1. **Write the brief** — copy `briefs/TEMPLATE.md` to `briefs/<slug>.md`: your thesis, two
   or three things you have seen, where you disagree, what would change your mind. The
   take is the one hard requirement.
2. **Run** — `python -m src.agent_sdk.pipeline --brief briefs/<slug>.md`. Research is
   Claude's own WebSearch on the subscription (no search key). A stat audit strips any
   number the research did not source. The pipeline draws nothing (constraint #4): it
   writes a hero *brief* and, if the research carried figures, a chart spec for you to
   frame.
3. **Read the packet** at `output/posts/<slug>.review.md`. Blocking findings are invariants
   a reader would be harmed by; advisory findings are style, and your call.
4. **Add art, deploy to an unlisted review URL, read it live, then publish:**

```bash
make art SLUG=<slug>                                                          # fold art in
python -m scripts.deploy_to_blog --article output/posts/<slug>.md --mode review  # unlisted URL
make publish SLUG=<slug>                                                      # after reading it
```

`--mode` has no default; the old default published a post unreviewed (B-028). After
publishing, fill in `## Verdict` in the brief — the next run reads the last five.

## Constraints (non-negotiable, enforced by a hook)

No new API keys, ever. No paid services. The only LLM auth is the Claude subscription via
the Agent SDK. The owner makes every image. The pipeline runs locally. `CLAUDE.md` has the
full text; `scripts/hooks/guard_constraints.py` enforces it on every tool call.

## Installation

```bash
git clone https://github.com/oviney/economist-agents.git && cd economist-agents
make install        # python3.12 venv + requirements
claude              # log the Agent SDK in once, on the subscription
```

`BLOG_REPO_TOKEN` (a free GitHub token for `oviney/blog`) is the only variable needed.

## Development

Verification is local-first ([ADR-0015](docs/adr/0015-local-first-verification.md)): no CI,
`main` unprotected, so `make ci-local` (ruff, docs-truth, mypy, pytest + coverage, bandit) is
the merge gate and you are its operator. Work items live in `BACKLOG.md`.

## Layout

```
briefs/                    the owner's briefs (input) and their verdicts (feedback)
src/agent_sdk/             pipeline.py · brief.py · research/ · stage3_runner.py
                           stage4_runner.py · _shared.py · review_packet.py · chart_renderer.py
scripts/                   publication_validator.py · deploy_to_blog.py · promote_review.py
                           finalise_art.py · html_to_brief.py · hooks/
skills/                    four SKILL.md files: writing rules, code standards, routing, ADRs
docs/adr/  docs/specs/     decisions; the current redesign spec
docs/HANDOFF.md            cross-session memory
docs/archive/              everything retired, kept whole
```

## License

MIT — see [LICENSE](LICENSE).
