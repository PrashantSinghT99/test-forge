# Makefile for Test Forge Automation Framework
# Usage: make <target>

.PHONY: install install-browsers test-no-ai test-ai test-stagehand test-all clear help

install:
	pip install -e ".[test]"

install-browsers:
	python -m playwright install --with-deps chromium

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
	@echo "  install          - install Python dependencies"
	@echo "  install-browsers - install Playwright browser (chromium)"
	@echo "  test-no-ai       - run no_ai deterministic suite with self-healing and classification"
	@echo "  test-ai          - run ai-assisted self-healing branch suite"
	@echo "  test-stagehand   - run declarative stagehand agent suite"
	@echo "  test-all         - run all execution branches sequentially"
	@echo "  clear            - clean reports, screenshots, videos, logs"
