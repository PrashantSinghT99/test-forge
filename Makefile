# Makefile for Test Forge Automation Framework
# Usage: make <target>

.PHONY: install test-no-ai test-ai test-stagehand test-all clear help

UV := $(shell command -v uv 2> /dev/null)

install:
ifdef UV
	uv pip install --system -e ".[test]" || uv pip install -e ".[test]"
else
	pip install -e ".[test]"
endif

test-no-ai:
ifdef UV
	uv run runner.py --branch no_ai --self-heal --classify --retries 2
else
	python runner.py --branch no_ai --self-heal --classify --retries 2
endif

test-ai:
ifdef UV
	uv run runner.py --branch ai --self-heal --classify
else
	python runner.py --branch ai --self-heal --classify
endif

test-stagehand:
ifdef UV
	uv run runner.py --branch stagehand
else
	python runner.py --branch stagehand
endif

test-all: test-no-ai test-ai test-stagehand

clear:
	-rm -rf reports/* videos/* screenshots/* logs/* || true

help:
	@echo "Makefile targets:"
	@echo "  install        - install dependencies via uv / pip"
	@echo "  test-no-ai     - run no_ai deterministic suite with self-healing and classification"
	@echo "  test-ai        - run ai-assisted self-healing branch suite"
	@echo "  test-stagehand - run declarative stagehand agent suite"
	@echo "  test-all       - run all execution branches sequentially"
	@echo "  clear          - clean reports, screenshots, videos, logs"
