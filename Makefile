# Makefile for Test Forge Automation Framework
# Usage: make <target>

.PHONY: install install-browsers lint test-no-ai test-ai test-stagehand test-all clear help

install:
	pip install -e ".[test]"
	pip install ruff

install-browsers:
	python -m playwright install --with-deps chromium

lint:
	ruff check . --output-format=concise
	ruff format --check .

lint-fix:
	ruff check . --fix
	ruff format .

test-no-ai:
	python runner.py --branch no_ai --self-heal --classify --retries 2

test-ai:
	python runner.py --branch ai --self-heal --classify

test-stagehand:
	python runner.py --branch stagehand

test-all: test-no-ai test-ai test-stagehand

clear:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['reports','videos','screenshots','logs']]"

help:
	@echo "Makefile targets:"
	@echo "  install          - install Python dependencies + ruff"
	@echo "  install-browsers - install Playwright browser (chromium)"
	@echo "  lint             - run Ruff linter and format check"
	@echo "  lint-fix         - auto-fix Ruff lint and format issues"
	@echo "  test-no-ai       - run no_ai deterministic suite with self-healing and classification"
	@echo "  test-ai          - run ai-assisted self-healing branch suite"
	@echo "  test-stagehand   - run declarative stagehand agent suite"
	@echo "  test-all         - run all execution branches sequentially"
	@echo "  clear            - clean reports, screenshots, videos, logs"
