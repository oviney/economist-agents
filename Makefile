.PHONY: install test lint format type-check quality clean help

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies and pre-commit hooks"
	@echo "  make test         - Run tests with coverage"
	@echo "  make lint         - Run ruff linter"
	@echo "  make format       - Format code with ruff"
	@echo "  make type-check   - Run mypy type checker"
	@echo "  make quality      - Run all quality checks"
	@echo "  make clean        - Remove cache files"

install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install --install-hooks
	pre-commit install --hook-type pre-push
	@echo "✅ Installation complete"

test:
	pytest tests/ -v \
		--cov=scripts \
		--cov-report=term-missing \
		--cov-fail-under=80

lint:
	ruff check .

format:
	ruff format .

type-check:
	mypy scripts/

quality: format lint type-check test
	@echo "✅ All quality checks passed!"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	rm -rf output/*.md output/charts/*.png
	@echo "✅ Cleaned cache files"
