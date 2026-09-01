.PHONY: install test lint format type-check mypy-advisory quality ci-local clean help art publish require-venv

# B-039: ADR-0015 makes `make ci-local` THE merge gate — there is no GitHub Actions and
# main is unprotected — so it has to mean the same thing on every machine and in every
# shell. Resolving tools from ambient PATH broke that three ways, all measured 2026-08-01:
# the gate linted with homebrew's ruff 0.15.9 while requirements-dev.txt pins ruff==0.14.10
# exactly, and demanded a reformat of a file nobody had touched; bare `python` does not
# exist on macOS outside an activated venv, so the gate died at step 3 with "command not
# found"; and the advisory mypy step reported a *missing* mypy identically to one that ran
# and found errors.
#
# Recipes name $(VENV_BIN)/<tool> EXPLICITLY. Exporting PATH is not enough and looks like
# it is: GNU make 3.81 (what macOS ships) direct-execs any recipe line with no shell
# metacharacters, and resolves the binary against its own startup PATH rather than the
# exported one — so `ruff check .` silently kept using the ambient ruff while
# `mypy ...; status=$$?` (has metacharacters, so a shell runs it) used the venv. The export
# below still earns its place: it fixes the tools that *child* processes go looking for.
VENV_BIN := $(CURDIR)/.venv/bin
PY       := $(VENV_BIN)/python
export PATH := $(VENV_BIN):$(PATH)

# Fail loudly rather than falling through to whatever the machine happens to have. Every
# tool-running target depends on this; `install` deliberately does not, because it is what
# creates the venv.
require-venv:
	@test -x "$(PY)" || { \
		echo "✗ no pinned toolchain at $(VENV_BIN)"; \
		echo "  create it, then re-run:  make install"; \
		exit 1; \
	}

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      - Create the venv if needed, install dependencies and hooks"
	@echo "  make test         - Run tests with coverage"
	@echo "  make lint         - Run ruff linter"
	@echo "  make format       - Format code with ruff"
	@echo "  make type-check   - Run mypy type checker"
	@echo "  make quality      - Run all quality checks (fast)"
	@echo "  make ci-local     - Full pre-merge gate (replaces GitHub Actions CI)"
	@echo "  make publish SLUG=<slug> - Promote an approved B-013 review draft to a post"
	@echo "  make clean        - Remove cache files"

# The one target that may not require the venv — it is what builds it. Creating it here
# makes require-venv's instruction ("make install") true from a bare shell (B-039).
install:
	@test -x "$(PY)" || python3 -m venv .venv
	$(VENV_BIN)/pip install -r requirements.txt
	$(VENV_BIN)/pip install -r requirements-dev.txt
	$(VENV_BIN)/pre-commit install --install-hooks
	$(VENV_BIN)/pre-commit install --hook-type pre-push
	@echo "✅ Installation complete"

# B-031: threshold was 40 here and 70 in ci-local. One gate, one number — this
# matches ci-local so a green `make test` means the same thing as a green gate.
test: require-venv
	$(VENV_BIN)/pytest tests/ -v \
		--cov=src --cov=scripts \
		--cov-report=term-missing \
		--cov-fail-under=70

lint: require-venv
	$(VENV_BIN)/ruff check .

format: require-venv
	$(VENV_BIN)/ruff format .

type-check: require-venv
	$(VENV_BIN)/mypy scripts/

# B-039: mypy exits 0 (clean), 1 (type errors found), and >1 for everything else — 2 for a
# usage or internal error, 127 for "command not found". Only exit 1 is the known-red
# backlog this step is allowed to wave through. The old form,
# `(mypy scripts/ || echo "advisory")`, printed the same reassuring line for all of them,
# so a mypy that never ran passed the gate. That is B-031's complaint exactly: a sensor
# that cannot tell "I ran and found problems" from "I never ran".
mypy-advisory: require-venv
	@$(VENV_BIN)/mypy scripts/; status=$$?; \
	if [ $$status -gt 1 ]; then \
		echo "✗ mypy did not run (exit $$status) — a missing or broken tool must fail the gate, not pass it quietly (B-039)"; \
		exit 1; \
	elif [ $$status -eq 1 ]; then \
		echo "⚠️  mypy advisory — repo-wide backlog is known-red (611 errors); NEW type errors are blocked per-commit by the baselined mypy hook (B-031, B-035 Task 2 — see docs/mypy-baseline.md)"; \
	fi

quality: format lint type-check test
	@echo "✅ All quality checks passed!"

# Full pre-merge gate — reproduces every check the retired GitHub Actions
# `Quality Gates CI` (ci.yml) enforced, so verification is local-first and
# paywall-free (ADR-0015). main is unprotected: run this before you merge.
ci-local: require-venv
	@echo "── ruff format ──"        && $(VENV_BIN)/ruff format --check .
	@echo "── ruff lint ──"          && $(VENV_BIN)/ruff check .
	@echo "── bare-name imports ──"  && $(PY) scripts/check_bare_name_imports.py
	@echo "── docs-truth gate ──"    && $(PY) scripts/check_docs_references.py
	@echo "── mypy (advisory) ──"    && $(MAKE) --no-print-directory mypy-advisory
	@echo "── mypy baseline gate ──" && $(PY) scripts/mypy_baseline.py --all
	@echo "── tests + coverage ──"   && $(VENV_BIN)/pytest tests/ \
		--cov=src --cov=scripts \
		--cov-report=term-missing \
		--cov-fail-under=70
	@echo "── src/quality per-module coverage ──" && $(VENV_BIN)/coverage report --include='src/quality/*' --fail-under=90
	@echo "── security scan (bandit) ──" && $(VENV_BIN)/bandit -r scripts/ \
		--exclude '*/.venv/*,*/__pycache__/*,scripts/archived' \
		--severity-level medium -q
	@echo "── destructive-change guard ──" && $(PY) scripts/destructive_change_guard.py
	@echo "── sensor proofs ──"           && $(PY) scripts/check_sensor_proofs.py
	@echo "✅ ci-local passed — you are the merge gate (main is unprotected)."

art: require-venv
	@if [ -z "$(SLUG)" ]; then echo "Usage: make art SLUG=<slug>"; exit 2; fi
	$(PY) -m scripts.finalise_art --slug $(SLUG)

publish: require-venv
	@if [ -z "$(SLUG)" ]; then echo "Usage: make publish SLUG=<slug>"; exit 2; fi
	$(PY) -m scripts.promote_review --slug $(SLUG)

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	rm -rf output/*.md output/charts/*.png
	@echo "✅ Cleaned cache files"
