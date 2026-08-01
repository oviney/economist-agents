#!/usr/bin/env python3
"""Gate: no sensor ships without a proof it can fail (B-043).

`docs/specs/sensor-proof-of-teeth.md` is the spec. The short version: the
2026-07-29 harness assessment graded this repo *guide-maximal, sensor-disconnected*,
B-030…B-035 fixed the wiring, and then a single day (2026-08-01) produced four
independent proofs that **nothing validates the sensors themselves** —

* **B-039** — `(mypy || echo "advisory")` returned exit 0 against a stub `mypy`
  exiting 127. A *fifth* inert sensor, found after B-031 fixed four by name.
* **B-040** — a gate that has run once, by hand, with no ground truth.
* **B-041** — a ledger that recorded only the runs where the hero succeeded.
* **B-042** — a sensor whose setpoint manufactured the defect it prevents.

B-031 fixed four named sensors; it did not fix the class. This is the standing
check rather than another audit.

**Why this is a sensor and not a line in a `SKILL.md`.** The strongest guide in
this codebase — `CLAUDE.md` constraint #1, *"NO new API keys. Ever."* — had zero
computational backing until B-030 gave it a `PreToolUse` deny. B-028 is the same
story: the review stage existed as prose while `--mode` defaulted to `post`, and
the default won. A rule nothing enforces gets skipped, so this ships in
`make ci-local` — and, being a sensor, it carries its own proof of teeth in
`tests/test_check_sensor_proofs.py::TestItsOwnProofOfTeeth`.

## What it checks

1. Every script a **gate site** invokes appears in `docs/sensors/register.yaml`.
   Gate sites are read from the wiring, not guessed from filenames: the
   `Makefile`, `.pre-commit-config.yaml`, `.claude/settings.json`, and the
   publish entrypoints. A filename pattern would be gameable by renaming and
   blind to anything wired in under another name.
2. Every entry names a `proof` that exists, is a real test, and is neither
   skipped nor xfail — or says `proof: none` and records a `reason`.
3. Every entry carries `regulates` (what defect it catches) and, when proved,
   `mutation` (what the proof breaks to make it fire).

## What it deliberately cannot check

**It verifies a proof exists and runs. It cannot verify the proof is genuine.**
A test named `test_gutting_a_critical_file_is_caught` whose body is `assert True`
passes this gate. Closing that hole means mutation-testing the mutation tests,
which is where the value curve goes flat — so the limit is stated rather than
papered over. Genuineness is a review-time concern, and the `mutation:` field
exists so a reviewer can check the claim against the test in one glance without
reading the whole file.

Exit code 0 when the register is honest, 1 otherwise.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The register, relative to the repo root, so fixture trees can be checked too.
REGISTER_RELPATH = "docs/sensors/register.yaml"

#: `proof:` value that declares an unproved sensor. Legitimate with a `reason:` —
#: the spec ships the register green on a TRUE baseline rather than after a
#: backfill sprint, and the count of these is the burndown (see ``--list``).
UNPROVED = "none"

#: `proof:` value for something a gate site wires in that cannot block anything —
#: `session_context` injects the constraints at SessionStart and `post_edit_sensor`
#: returns `additionalContext`; neither can deny a call or fail a gate. They are
#: informants, not sensors, so there is no "can it fail?" to answer.
#:
#: This is a *declared* exemption and the checker cannot verify the claim, the same
#: way it cannot verify a proof is genuine. It is visible in the register and in
#: ``--list`` so a reviewer adjudicates it, which is the `docs/harness-overrides.md`
#: convention. Marking a sensor that CAN block as `n/a` would defeat this gate — do
#: not do it, and expect it to be challenged at review.
NOT_A_SENSOR = "n/a"

#: Both reason-carrying states, kept apart so the burndown counts only what is
#: genuinely owed: `none` is a debt, `n/a` is not.
_REASON_REQUIRED = (UNPROVED, NOT_A_SENSOR)

#: Scripts that gate a publish. `deploy_to_blog` and `promote_review` refuse
#: content themselves (`--mode` is required, B-028; the hero-prompt comment is
#: rejected, BUG-065/ADR-0017) and they run `publication_validator` as the
#: acceptance oracle. Their `from scripts.X import` edges are followed, so a new
#: gate imported into the publish path is discovered without touching this list.
PUBLISH_ENTRYPOINTS: tuple[str, ...] = (
    "scripts/deploy_to_blog.py",
    "scripts/promote_review.py",
)

#: An in-repo script path inside a gate-site config value.
_SCRIPT_RE = re.compile(r"\b(scripts/(?:hooks/)?[a-z0-9_]+\.py)\b")

#: `python -m scripts.foo` / `-m scripts.hooks.foo`.
_MODULE_RE = re.compile(r"-m\s+(scripts(?:\.hooks)?\.[a-z0-9_]+)\b")

#: `run_hook.sh <name>` in `.claude/settings.json` → `scripts/hooks/<name>.py`.
_HOOK_RE = re.compile(r"run_hook\.sh[\\\"'\s]+([a-z0-9_]+)")


@dataclass(frozen=True)
class Finding:
    """One reason the register is not honest.

    Attributes:
        subject: The entry id, script path, or file the finding is about.
        message: What is wrong, phrased so the fix is obvious.

    """

    subject: str
    message: str

    def __str__(self) -> str:
        return f"{self.subject}: {self.message}"


# ═══════════════════════════════════════════════════════════════════════════
# Discovery — a script is a sensor when a gate site invokes it
# ═══════════════════════════════════════════════════════════════════════════


def _uncommented_makefile(text: str) -> str:
    """Drop comment lines from a Makefile.

    The real Makefile discusses its sensors at length in comments — B-039's whole
    reasoning lives there. Counting those would make the register a transcript of
    the commentary rather than a list of what runs.
    """
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def _module_to_path(module: str) -> str:
    """Turn ``scripts.hooks.foo`` into ``scripts/hooks/foo.py``."""
    return module.replace(".", "/") + ".py"


def _scripts_in(text: str) -> set[str]:
    """Return every in-repo script path a blob of config text invokes."""
    found = set(_SCRIPT_RE.findall(text))
    found.update(_module_to_path(m) for m in _MODULE_RE.findall(text))
    return found


def _from_makefile(root: Path) -> set[str]:
    path = root / "Makefile"
    if not path.is_file():
        return set()
    return _scripts_in(_uncommented_makefile(path.read_text(encoding="utf-8")))


def _from_pre_commit(root: Path) -> set[str]:
    """Read hook `entry:` values, so a comment about a sensor is not a gate site."""
    path = root / ".pre-commit-config.yaml"
    if not path.is_file():
        return set()
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return set()
    if not isinstance(config, dict):
        return set()

    found: set[str] = set()
    for repo in config.get("repos") or []:
        if not isinstance(repo, dict):
            continue
        for hook in repo.get("hooks") or []:
            if isinstance(hook, dict) and hook.get("entry"):
                found |= _scripts_in(str(hook["entry"]))
    return found


def _from_harness_hooks(root: Path) -> set[str]:
    """Read `.claude/settings.json`.

    Answers the spec's open question 2 — yes, a hook is registered separately from
    the script it invokes. A hook can be inert while its script is fine; that is
    exactly how `validate_badges` was `|| true` for months.
    """
    path = root / ".claude" / "settings.json"
    if not path.is_file():
        return set()
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()

    text = json.dumps(settings)
    found = _scripts_in(text)
    found.update(f"scripts/hooks/{name}.py" for name in _HOOK_RE.findall(text))
    return found


def _from_publish_path(root: Path) -> set[str]:
    """Follow `from scripts.X import` out of the publish entrypoints."""
    found: set[str] = set()
    for relpath in PUBLISH_ENTRYPOINTS:
        path = root / relpath
        if not path.is_file():
            continue
        found.add(relpath)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                module = node.module or ""
                if module.startswith("scripts.") and module.count(".") <= 2:
                    found.add(_module_to_path(module))
    return found


def discover_gate_scripts(root: Path) -> dict[str, list[str]]:
    """Return every in-repo script a gate site invokes, mapped to its gate sites.

    Args:
        root: Repo (or fixture tree) root.

    Returns:
        ``{"scripts/foo.py": ["Makefile", ".pre-commit-config.yaml"]}``. A gate
        site file that does not exist contributes nothing and is not an error —
        degrade, do not crash.

    """
    sources = {
        "Makefile": _from_makefile,
        ".pre-commit-config.yaml": _from_pre_commit,
        ".claude/settings.json": _from_harness_hooks,
        "publish path": _from_publish_path,
    }

    discovered: dict[str, list[str]] = {}
    for site, reader in sources.items():
        for script in sorted(reader(root)):
            if not (root / script).is_file():
                # A gate site naming a script that does not exist is its own
                # defect, caught by TestHooksPointAtRealScripts (B-036). Not
                # this gate's job, and registering a phantom helps nobody.
                continue
            discovered.setdefault(script, []).append(site)
    return discovered


# ═══════════════════════════════════════════════════════════════════════════
# Proof resolution
# ═══════════════════════════════════════════════════════════════════════════

_MUTING_MARKS = ("skip", "skipif", "xfail")


def _muting_mark(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> str:
    """Return the name of a skip/xfail mark on a node, or "".

    Skipping is how a proof rots quietly: it stays green in the suite and stops
    running, so the sensor it covers silently loses its teeth.
    """
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        parts: list[str] = []
        while isinstance(target, ast.Attribute):
            parts.append(target.attr)
            target = target.value
        if isinstance(target, ast.Name):
            parts.append(target.id)
        names = list(reversed(parts))
        if "pytest" in names and "mark" in names:
            for mark in _MUTING_MARKS:
                if mark in names:
                    return mark
    return ""


def _resolve_proof(root: Path, proof: str) -> Finding | None:
    """Check that a ``path::[Class::]test`` reference names a test that will run.

    Args:
        root: Repo (or fixture tree) root.
        proof: The register entry's ``proof`` value.

    Returns:
        A Finding when the proof cannot run, else None.

    """
    parts = proof.split("::")
    if len(parts) < 2:
        return Finding(proof, "proof must be 'path/to/test_x.py::test_name'")

    relpath, *path_in_file = parts
    path = root / relpath
    if not path.is_file():
        return Finding(proof, f"proof file {relpath} does not exist")

    try:
        tree: ast.AST = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        return Finding(proof, f"proof file {relpath} could not be parsed: {exc}")

    body: list[ast.stmt] = tree.body  # type: ignore[attr-defined]
    for index, name in enumerate(path_in_file):
        is_last = index == len(path_in_file) - 1
        match = next(
            (
                node
                for node in body
                if isinstance(
                    node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
                )
                and node.name == name
            ),
            None,
        )
        if match is None:
            return Finding(proof, f"{relpath} defines no {name}")
        mark = _muting_mark(match)
        if mark:
            return Finding(
                proof,
                f"{name} is marked pytest.mark.{mark} — a proof that does not run "
                "is not a proof",
            )
        if not is_last:
            body = match.body
    return None


# ═══════════════════════════════════════════════════════════════════════════
# The check
# ═══════════════════════════════════════════════════════════════════════════


def load_register(root: Path) -> tuple[list[dict[str, object]], list[Finding]]:
    """Parse the register.

    Args:
        root: Repo (or fixture tree) root.

    Returns:
        ``(entries, findings)``. A register that cannot be read yields no entries
        and a finding — "could not run" must never look like "clean", which is
        B-039's complaint exactly.

    """
    path = root / REGISTER_RELPATH
    if not path.is_file():
        return [], [Finding(REGISTER_RELPATH, "register does not exist")]

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [], [Finding(REGISTER_RELPATH, f"register is not valid YAML: {exc}")]

    if not isinstance(data, dict) or "sensors" not in data:
        return [], [
            Finding(REGISTER_RELPATH, "register must be a mapping with 'sensors'")
        ]

    sensors = data.get("sensors") or []
    if not isinstance(sensors, list):
        return [], [Finding(REGISTER_RELPATH, "'sensors' must be a list")]

    entries = [entry for entry in sensors if isinstance(entry, dict)]
    findings = [
        Finding(REGISTER_RELPATH, "every sensor entry must be a mapping")
        for entry in sensors
        if not isinstance(entry, dict)
    ]
    return entries, findings


def _check_entry(root: Path, entry: dict[str, object]) -> list[Finding]:
    """Validate one register entry."""
    entry_id = str(entry.get("id") or "<entry with no id>")
    findings: list[Finding] = []

    if not entry.get("id"):
        findings.append(Finding(entry_id, "entry needs an 'id'"))

    script = str(entry.get("script") or "")
    if not script:
        findings.append(Finding(entry_id, "entry needs a 'script'"))
    elif not (root / script).is_file():
        findings.append(
            Finding(
                entry_id, f"{script} does not exist — the register outlived its sensor"
            )
        )

    if not str(entry.get("regulates") or "").strip():
        findings.append(
            Finding(
                entry_id,
                "entry needs 'regulates' — a proof whose reasoning is not written "
                "down cannot be re-adjudicated when the sensor changes",
            )
        )

    proof = str(entry.get("proof") or "").strip()
    if not proof:
        findings.append(
            Finding(
                entry_id,
                f"entry needs a 'proof' (or 'proof: {UNPROVED}' plus a 'reason')",
            )
        )
    elif proof in _REASON_REQUIRED:
        if not str(entry.get("reason") or "").strip():
            findings.append(
                Finding(
                    entry_id,
                    f"'proof: {proof}' needs a 'reason' — an unproved sensor that "
                    "says so is a baseline; one that says nothing is a mute button",
                )
            )
    else:
        if not str(entry.get("mutation") or "").strip():
            findings.append(
                Finding(
                    entry_id,
                    "entry needs 'mutation' — what the proof breaks to make the "
                    "sensor fire, so a reviewer can check the claim in one glance",
                )
            )
        resolved = _resolve_proof(root, proof)
        if resolved is not None:
            findings.append(Finding(entry_id, resolved.message))

    return findings


def check_register(root: Path | None = None) -> list[Finding]:
    """Check a tree's sensors against its register.

    Args:
        root: Repo (or fixture tree) root. Defaults to this repo.

    Returns:
        Every reason the register is not honest, in a stable order. Empty means
        the gate passes.

    """
    root = root or REPO_ROOT
    entries, findings = load_register(root)

    seen: set[str] = set()
    for entry in entries:
        entry_id = str(entry.get("id") or "")
        if entry_id and entry_id in seen:
            findings.append(
                Finding(entry_id, "duplicate id — one of these is never read")
            )
        seen.add(entry_id)
        findings.extend(_check_entry(root, entry))

    registered = {str(entry.get("script") or "") for entry in entries}
    for script, sites in sorted(discover_gate_scripts(root).items()):
        if script not in registered:
            findings.append(
                Finding(
                    script,
                    f"invoked by {', '.join(sites)} but absent from {REGISTER_RELPATH} "
                    "— every sensor ships with a proof it can fail (B-043)",
                )
            )
    return findings


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════


def _print_list(root: Path) -> None:
    """Print what is registered and what is proved, unproved count last."""
    entries, findings = load_register(root)
    for finding in findings:
        print(f"✗ {finding}", file=sys.stderr)

    # Gate sites are COMPUTED, never read from the entry. A hand-written `gates:`
    # field is a claim about the wiring that drifts the moment the wiring moves,
    # which is the class of defect this whole gate exists to catch.
    gate_sites = discover_gate_scripts(root)

    unproved = informants = 0
    for entry in sorted(entries, key=lambda e: str(e.get("id") or "")):
        proof = str(entry.get("proof") or "").strip()
        reason = str(entry.get("reason") or "").strip()
        if proof == UNPROVED:
            unproved += 1
            mark, detail = "○", f"UNPROVED — {reason}"
        elif proof == NOT_A_SENSOR:
            informants += 1
            mark, detail = "·", f"cannot block — {reason}"
        else:
            mark, detail = "●", proof
        script = str(entry.get("script") or "")
        where = ", ".join(
            gate_sites.get(script, ["declared, not wired to a gate site"])
        )
        print(
            f"{mark} {entry.get('id')}  ({script})\n    fires at: {where}\n    {detail}"
        )

    proved = len(entries) - unproved - informants
    print(
        f"\n{len(entries)} registered: {proved} proved, {unproved} unproved, "
        f"{informants} cannot block."
    )
    if unproved:
        print(
            "The unproved count is the burndown — retire them one at a time (B-043 step 5)."
        )


def main(argv: list[str] | None = None) -> int:
    """Run the gate.

    Returns:
        0 when the register is honest, 1 otherwise.

    """
    parser = argparse.ArgumentParser(description="Check that every sensor has a proof.")
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="repo root to check (default: this repo)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="show what is registered and what is proved, then exit 0",
    )
    args = parser.parse_args(argv)

    if args.list:
        _print_list(args.root)
        return 0

    findings = check_register(args.root)
    if not findings:
        print("OK: every sensor a gate site invokes has a register entry and a proof.")
        return 0

    print(
        f"::error::{len(findings)} sensor(s) without an honest register entry. "
        "B-043: no sensor ships without a proof it can fail — see "
        "docs/specs/sensor-proof-of-teeth.md.",
        file=sys.stderr,
    )
    for finding in findings:
        print(f"  {finding}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
