#!/usr/bin/env bash
# Launcher for the harness hooks (B-030).
#
# `.claude/settings.json` calls this rather than a bare `python -m` for two reasons:
#
#   1. It resolves the repo root from its OWN location, so a hook works no matter what
#      cwd the harness happens to use.
#   2. It falls back from the project venv to system python3, so a fresh clone without
#      `make install` degrades to a working hook rather than a shell error.
#
# Usage: run_hook.sh <module-name-under-scripts.hooks>
#
# Exits 0 unconditionally. A hook must never be able to fail the tool call it observes —
# see scripts/hooks/_io.py:run for the Python-side half of the same guarantee.

set -u

hook_name="${1:-}"
[ -n "$hook_name" ] || exit 0

hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || exit 0
repo_root="$(cd "${hook_dir}/../.." && pwd)" || exit 0

python_bin="${repo_root}/.venv/bin/python"
if [ ! -x "$python_bin" ]; then
  python_bin="$(command -v python3 2>/dev/null)" || exit 0
  [ -n "$python_bin" ] || exit 0
fi

cd "$repo_root" || exit 0
"$python_bin" -m "scripts.hooks.${hook_name}"
exit 0
