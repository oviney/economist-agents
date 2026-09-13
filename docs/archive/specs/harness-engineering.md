# Spec: Harness engineering — close the sensor loop (B-030 … B-034)

**Status:** DRAFT — implemented same session under the owner's autonomous mandate
**Date:** 2026-07-29
**Assessment:** `docs/reviews/harness-engineering-assessment-2026-07-29.md`
**Source framework:** SE Radio 730 — Birgitta Boeckeler on harness engineering
**Related open items:** B-028 (a guide the default ignores), B-029 (an oracle that cannot fail)

---

## Assumptions

1. **Harness layer only.** This spec changes the Claude Code harness (`.claude/`,
   `.mcp.json`, `.pre-commit-config.yaml`, `ruff.toml`, `scripts/hooks/`). It does not
   change the content pipeline's behaviour. B-028's own fix (`deploy_to_blog.py`
   `default="post"`) stays with B-028; B-030 makes the policy unskippable from the harness
   side regardless of that default.
2. **Keyless throughout.** Every sensor added here is `ruff`, `git`, `pytest`, or Python
   stdlib. No new dependency, no key, no paid service. Constraints #1–#3 hold by
   construction.
3. **`.claude/settings.json` is committed; `.claude/settings.local.json` stays personal.**
   Hooks are team policy and must be in version control. The existing 122-entry permission
   allowlist stays in `settings.local.json` untouched.
4. **The `Stop` gate must be bounded.** An unbounded blocking `Stop` hook can trap a
   session in a loop. It blocks **at most once per session**, keyed by `session_id`.
5. **Pre-existing violations are not a wall.** 41 `C901` + 75 `PLR09xx` violations exist
   today. The complexity sensor is scoped to *files the agent just touched*, not the whole
   tree, and ships with a recorded-override path.

## Objective

The repo has a strong sensor inventory and no wiring: every sensor fires at the owner's
gate (`pre-commit`, `make ci-local`), so the owner performs the triage an agent could have
performed mid-session. Success is that **the agent gets the feedback first**, that
**sensors which cannot fail are either fixed or removed**, and that **the guide layer
becomes measurable** so it can shrink.

Concretely, when this is done:

- Editing a Python file produces lint + complexity feedback *inside the session*.
- Introducing a forbidden API key or an unreviewed publish is **denied by the harness**,
  not merely discouraged by prose.
- Ending a turn with a red tree is caught by the harness once, with a reason.
- Sensor state is recorded per session so "did violations spike mid-session?" is answerable.
- Every pre-commit hook can actually fail.
- Any skill can be evaluated with/without and deleted if it does not move a score.

## Commands

```bash
# The gate (unchanged, still the merge authority)
make ci-local

# New: complexity sensor, standalone
.venv/bin/python -m scripts.complexity_sensor src/agent_sdk/stage3_runner.py
.venv/bin/python -m scripts.complexity_sensor --changed        # git-diff scoped

# New: skill eval harness
.venv/bin/python -m scripts.skill_eval --list
.venv/bin/python -m scripts.skill_eval --skill economist-writing

# New: hook scripts are exercised by piping the documented stdin payload
echo '{"session_id":"t","tool_name":"Edit","tool_input":{"file_path":"scripts/foo.py"}}' \
  | .venv/bin/python -m scripts.hooks.post_edit_sensor

# Tests for everything added here
.venv/bin/pytest tests/test_harness_hooks.py tests/test_complexity_sensor.py \
                 tests/test_skill_eval.py tests/test_harness_config.py -q
```

## Project structure

```
.claude/settings.json              → NEW, committed: the hook wiring (team policy)
scripts/hooks/__init__.py          → NEW: hook package
scripts/hooks/_io.py               → NEW: stdin/stdout JSON contract, shared
scripts/hooks/post_edit_sensor.py  → NEW: PostToolUse — format, lint, complexity
scripts/hooks/guard_constraints.py → NEW: PreToolUse — deny forbidden keys / unreviewed publish
scripts/hooks/session_gate.py      → NEW: Stop — bounded red-tree gate
scripts/hooks/session_context.py   → NEW: SessionStart — constraints + branch + open items
scripts/complexity_sensor.py       → NEW: C901/PLR wrapper with the tuned message
scripts/skill_eval.py              → NEW: with/without skill eval harness
logs/sensor_history.jsonl          → NEW (gitignored): per-session sensor snapshots
docs/harness-overrides.md          → NEW: the recorded-override register
tests/test_harness_hooks.py        → NEW
tests/test_complexity_sensor.py    → NEW
tests/test_skill_eval.py           → NEW
tests/test_harness_config.py       → NEW: asserts config invariants (no inert hooks, no forbidden keys)
```

## Code style

Repo standards apply (`skills/python-quality`): type hints mandatory, docstrings required,
`orjson` not `json`, `logger` not `print()`. Hook scripts are the one place a
`print()`-shaped write is correct, because **stdout is the hook's return channel** — so
they use an explicit `sys.stdout.write` of an `orjson`-serialised payload, never a bare
`print` for logging.

```python
def emit(payload: dict[str, Any]) -> None:
    """Write a hook response to stdout — the harness's only return channel.

    Hooks communicate by serialising JSON to stdout; logging must go to stderr so it
    cannot corrupt the payload.
    """
    sys.stdout.write(orjson.dumps(payload).decode())
```

A hook must **never** crash the session. Every entry point wraps its body and exits 0 with
an empty payload on unexpected failure — a broken sensor degrades to no sensor, never to a
blocked developer.

## Testing strategy

`pytest`, tests in `tests/`, no network (`tests/_netguard.py` already enforces this).
Every hook is tested by **piping its documented stdin payload** and asserting on the
parsed stdout payload — the same contract the harness uses, so a passing test means the
hook works, not that its internals are reachable.

| Concern | Level | Test |
|---|---|---|
| Hook JSON contract | unit | `test_harness_hooks.py` — payload in, payload out, for every hook |
| Deny decisions | unit | forbidden-key Bash, `--mode post` deploy, and their allowed twins |
| `Stop` bounding | unit | second call in the same session must not block |
| Never-crash guarantee | unit | malformed stdin → exit 0, empty payload |
| Complexity message | unit | violation → judgment-call text + override instruction present |
| Config invariants | unit | `test_harness_config.py` — no `\|\| true` hook, no duplicate hook id, no forbidden key in `.mcp.json`, hooks present in `.claude/settings.json` |
| Skill eval | unit | scenario scoring is deterministic and with/without produces a delta |

Coverage: `make ci-local` thresholds are authoritative (70% overall, 90% `src/quality`).
New code must not lower them.

## Boundaries

**Always**
- Keep every hook exit-0-on-error. A sensor may report; it may not break the session.
- Bound anything that blocks. `Stop` blocks once per session, maximum.
- Scope edit-time sensors to the touched file, never the whole tree.
- Make the message actionable: what is wrong, what the judgment call is, how to record an
  override.

**Ask first**
- Raising `max-complexity` above 10, or adding a blanket `noqa` instead of a recorded
  override.
- Deleting any skill that a `B-033` eval says is inert (the eval informs the owner; it does
  not license deletion).
- Any change to `deploy_to_blog.py`'s own default — that is B-028's decision to make.

**Never**
- Add a sensor that cannot fail. If it can only pass, delete it instead.
- Add a hook that requires an API key, a paid service, or network access.
- Weaken `ci-local` to make a new sensor green.
- Reintroduce `image-generator` / `web-researcher` to `.mcp.json`.

---

## The five items

### B-030 · Wire the sensors into the agent's loop (hooks)

**Problem.** Zero hooks. No project `.claude/settings.json`. Every sensor fires at the
owner's gate.

**Change.** Commit `.claude/settings.json` with five hook wirings:

| Event | Matcher | Script | Behaviour |
|---|---|---|---|
| `PostToolUse` | `Edit\|Write` | `scripts.hooks.post_edit_sensor` | On `*.py`: `ruff format` + `ruff check --fix` the file, then report anything left plus complexity findings as `additionalContext`. Records a snapshot. |
| `PreToolUse` | `Bash` | `scripts.hooks.guard_constraints` | `permissionDecision: "deny"` for forbidden-key introduction and for `deploy_to_blog` without `--mode review`. |
| `PreToolUse` | `Write\|Edit` | `scripts.hooks.guard_constraints` | Same deny set, for the file-write path (e.g. writing a key into `.env.example` or `.mcp.json`). |
| `Stop` | — | `scripts.hooks.session_gate` | If tracked Python files are dirty and `ruff check` is red, `decision: "block"` **once per session** with the violations as the reason. |
| `SessionStart` | — | `scripts.hooks.session_context` | Injects the five non-negotiable constraints, the branch, and open `B-` items as `additionalContext`. |

**Acceptance**
- `jq -e '.hooks.PostToolUse[].hooks[].command' .claude/settings.json` exits 0.
- Piping the documented payload to each hook returns a valid payload and exit 0.
- A forbidden-key Bash command is denied; `git status` is not.
- A `deploy_to_blog --mode post` command is denied; `--mode review` is not.
- `session_gate` blocks on the first call and does not block on the second with the same
  `session_id`.
- Malformed stdin yields exit 0 and an empty payload for every hook.
- `logs/sensor_history.jsonl` gains a line per recorded snapshot; the file is gitignored.

**Revives.** `scripts/agent_trace_logger.py`, currently dead code, becomes the snapshot
writer — closing the observability gap the assessment flagged (§3.6).

### B-031 · Make the inert sensors honest

**Problem.** Four sensors cannot fail (assessment §3.3), so a green run proves nothing.

**Change**
1. **mypy** — remove `stages: [manual]`; run it on `scripts/` as a real pre-commit hook.
   `mypy.ini` stays non-strict (611 known errors is a separate project), but the hook must
   *fail on new errors in the files being committed*, which is what per-file pre-commit
   invocation gives. `ci-local`'s advisory wrapper is retained deliberately and its comment
   updated to say why: repo-wide mypy is known-red, per-commit mypy is not.
2. **coverage** — delete the duplicate `pytest-coverage` manual hook. `make test`'s
   threshold rises from 40 to 70 so it matches `ci-local`. One number, one place.
3. **badge validation** — drop `|| true`. If `validate_badges.py` fails, the commit fails.
4. **`validate-skills`** — delete the duplicate registration and the duplicated
   `always_run: false` key.

**Acceptance**
- `test_harness_config.py` asserts: no pre-commit hook entry contains `|| true`; no hook
  `id` appears twice; `make test` and `ci-local` declare the same `--cov-fail-under`.
- `pre-commit run --all-files` behaves as documented (a real failure fails).

**Explicitly out of scope.** B-029's oracle fix (`acceptance_blog_frontmatter.sh:120`). It
is the same *class* of defect and is cross-referenced from both items, but it lives in the
blog deploy path, not the harness, and B-029 owns it.

### B-032 · A complexity sensor with a tuned message

**Problem.** `ruff.toml` regulates no complexity dimension. Measured: 41 `C901` (worst 33),
28 `PLR0912`, 21 `PLR0913`, 18 `PLR0915`.

**Change.** `scripts/complexity_sensor.py` wraps
`ruff check --select C901,PLR0911,PLR0912,PLR0913,PLR0915` and rewrites the output into a
judgment-call message, per Boeckeler's ESLint technique:

```
COMPLEXITY SENSOR — scripts/foo.py
  bar() is too complex (18 > 10)

This is usually a smell. Consider: is this function doing more than one thing?
Can a branch become a guard clause, or a block become a named helper?

Make a judgment call. If the complexity is genuinely warranted — a dispatch table,
a parser, generated code, test data — you may keep it by recording an override in
docs/harness-overrides.md with a one-line justification. Do NOT add a bare noqa.
```

`ruff.toml` gains `[lint.mccabe] max-complexity = 10` and the `C901`/`PLR09xx` selectors
scoped via `[lint.per-file-ignores]` so the 41 pre-existing violations do not break
`ci-local` on day one; the sensor is enforced on **touched files** through B-030's
`PostToolUse` hook, which is where new complexity is actually born.

**Acceptance**
- A synthetic over-complex function produces the judgment-call text and a non-zero exit.
- A clean file produces no output and exit 0.
- `--changed` scopes to `git diff --name-only` and skips non-Python paths.
- `make ci-local` still passes — the legacy backlog is recorded, not enforced retroactively.
- `docs/harness-overrides.md` exists with the register's format and the day-one baseline.

### B-033 · Make the guide layer measurable

**Problem.** 8,031 lines of `SKILL.md` have never been measured. Boeckeler's point is that
many skills are model-authored and the model may already know their content.

**Change.** `scripts/skill_eval.py` — a with/without harness:

- `--list` enumerates skills with their line count and last-modified date (the cheap
  triage: big + old + never-referenced is the deletion candidate).
- `--skill <name>` runs the skill's declared scenarios twice — context with the skill, and
  context without it — scoring each output with the existing deterministic scorer
  (`scripts/article_evaluator.py` for content skills; a rubric hook for others) and reports
  the delta.
- Scenarios live in `skills/<name>/eval.yaml`; a skill with no `eval.yaml` reports
  `UNMEASURED` rather than passing silently.

**Acceptance**
- `--list` reports all 38 skills, sorted by line count descending.
- A skill with an `eval.yaml` produces a with/without delta.
- A skill without one reports `UNMEASURED` and exits non-zero under `--strict`.
- The harness makes **no LLM call by default** (`--dry-run` is the default; scoring is
  deterministic) so it is free to run and cannot fail on auth.

**Non-goal.** Deleting skills. This item produces the evidence; the owner decides.

### B-034 · Shrink the tool surface to what the guides permit

**Problem.** `.mcp.json` ships `image-generator` (`OPENAI_API_KEY`) and `web-researcher`
(`SERPER_API_KEY`), both prohibited; `enableAllProjectMcpServers: true` loads them every
session. The harness offers tools its own guides forbid.

**Change**
1. Delete the `image-generator` entry from `.mcp.json` (genuinely DALL-E, genuinely needs
   the key).
2. **Corrected during implementation:** `web_researcher_server.py` is *already keyless* —
   #438 stripped the Serper leg and the module now exposes only `search_arxiv` and
   `fetch_page`, both permitted by constraint #3. Deleting the server would have removed a
   legitimate keyless research tool. Only the stale `env` block and the misleading
   description were removed; the server stays. This is why the spec is a living document:
   the original plan was wrong about the code.
3. Replace `enableAllProjectMcpServers: true` with `enabledMcpjsonServers` naming the six
   keyless servers explicitly.
4. `test_harness_config.py` asserts no forbidden key name appears in `.mcp.json`, and
   additionally that **no server declares any `env` block at all** — an env requirement is
   a key requirement in disguise, so the stricter invariant is the durable one.

**Acceptance**
- `.mcp.json` contains exactly the six keyless servers.
- No `OPENAI_API_KEY` / `SERPER_API_KEY` / `GEMINI_API_KEY` in `.mcp.json`.
- No MCP server declares an `env` requirement.
- The config test fails if any is reintroduced.

**Scope call:** `mcp_servers/image_generator_server.py` and its passing test are left in
place. The finding was that the *harness offers* a forbidden tool; deleting the entry closes
that. Moving the module would churn a green test suite for no harness benefit, and ADR-0014
already retired the workflow. Retiring the dead module is a separate cleanup.

---

## Implementation order

`B-034` → `B-031` → `B-032` → `B-030` → `B-033`.

Highest *leverage* is B-030, but it is not first: B-034 and B-031 are near-zero-risk
cleanups that shrink the surface B-030 must reason about, and B-032 supplies the sensor
B-030's `PostToolUse` hook calls. B-033 is last because its value depends on the session
recording B-030 introduces.

## Success criteria

- [ ] `.claude/settings.json` is committed and every hook returns a valid payload for its
      documented stdin.
- [ ] A forbidden key and an unreviewed publish are **denied**, not discouraged.
- [ ] `Stop` blocks a red tree once per session, never twice.
- [ ] No pre-commit hook can pass unconditionally.
- [ ] `make test` and `make ci-local` agree on one coverage threshold.
- [ ] The complexity sensor emits the judgment-call message and an override path.
- [ ] `.mcp.json` holds only keyless servers, enforced by a test.
- [ ] `scripts/skill_eval.py --list` reports all 38 skills; unmeasured skills say so.
- [ ] `logs/sensor_history.jsonl` records snapshots via the revived trace logger.
- [ ] `make ci-local` passes.

## Open questions for the owner

1. **`Stop` gate strictness.** It currently blocks only on `ruff check` failure over dirty
   tracked Python files. Should it also block on a failing *test* for those files? That is
   stronger and slower; it is one line to enable.
2. **mypy per-commit.** B-031 makes mypy blocking per-commit while leaving repo-wide mypy
   advisory. The alternative is deleting "Type hints mandatory" from `CLAUDE.md` and letting
   the sensor define the standard. Item shipped with the former; say the word for the latter.
3. **Skill deletion.** B-033 will likely find that `.github/copilot-instructions.md`
   (2,601 lines) and several skills are inert. Deletion needs your call, per Boundaries.
