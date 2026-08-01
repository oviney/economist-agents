.PHONY: install test lint format type-check quality ci-local clean help publish

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies and pre-commit hooks"
	@echo "  make test         - Run tests with coverage"
	@echo "  make lint         - Run ruff linter"
	@echo "  make format       - Format code with ruff"
	@echo "  make type-check   - Run mypy type checker"
	@echo "  make quality      - Run all quality checks (fast)"
	@echo "  make ci-local     - Full pre-merge gate (replaces GitHub Actions CI)"
	@echo "  make publish SLUG=<slug> - Promote an approved B-013 review draft to a post"
	@echo "  make clean        - Remove cache files"

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install --install-hooks
	pre-commit install --hook-type pre-push
	@echo "✅ Installation complete"

# B-031: threshold was 40 here and 70 in ci-local. One gate, one number — this
# matches ci-local so a green `make test` means the same thing as a green gate.
test:
	pytest tests/ -v \
		--cov=src --cov=scripts \
		--cov-report=term-missing \
		--cov-fail-under=70

lint:
	ruff check .

format:
	ruff format .

type-check:
	mypy scripts/

quality: format lint type-check test
	@echo "✅ All quality checks passed!"

# Full pre-merge gate — reproduces every check the retired GitHub Actions
# `Quality Gates CI` (ci.yml) enforced, so verification is local-first and
# paywall-free (ADR-0015). main is unprotected: run this before you merge.
ci-local:
	@echo "── ruff format ──"        && ruff format --check .
	@echo "── ruff lint ──"          && ruff check .
	@echo "── bare-name imports ──"  && python scripts/check_bare_name_imports.py
	@echo "── mypy (advisory) ──"    && (mypy scripts/ || echo "⚠️  mypy advisory — repo-wide backlog is known-red (611 errors); NEW type errors are blocked per-commit by the baselined mypy hook (B-031, B-035 Task 2 — see docs/mypy-baseline.md)")
	@echo "── mypy baseline gate ──" && .venv/bin/python scripts/mypy_baseline.py --all
	@echo "── tests + coverage ──"   && pytest tests/ \
		--cov=src --cov=scripts \
		--cov-report=term-missing \
		--cov-fail-under=70
	@echo "── src/quality per-module coverage ──" && coverage report --include='src/quality/*' --fail-under=90
	@echo "── security scan (bandit) ──" && bandit -r scripts/ \
		--exclude '*/.venv/*,*/__pycache__/*,scripts/archived' \
		--severity-level medium -q
	@echo "── destructive-change guard ──" && python scripts/destructive_change_guard.py
	@echo "✅ ci-local passed — you are the merge gate (main is unprotected)."

publish:
	@if [ -z "$(SLUG)" ]; then echo "Usage: make publish SLUG=<slug>"; exit 2; fi
	python -m scripts.promote_review --slug $(SLUG)

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	rm -rf output/*.md output/charts/*.png
	@echo "✅ Cleaned cache files"
