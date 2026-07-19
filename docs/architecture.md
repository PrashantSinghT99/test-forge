# Project Architecture

## Repo Structure

```text
sauceplaywright/
├── src/
│   ├── pages/           # Page Object Model (POM) classes
│   └── testing/         # Shared intelligent core layer
│       ├── self_healing/ # Locator recovery wrappers & strategy matchers
│       │   ├── dom_extractor.py
│       │   ├── strategies.py
│       │   └── healer.py
│       ├── stagehand/    # Declarative planning agent
│       │   └── agent.py
│       ├── failure_classification.py # Exception categories & regex locator parser
│       ├── flaky_detection.py # SQLite WAL and JSON locked result history
│       └── ai_helper.py # Ollama / HF / Gemini routing client
├── tests/               # isolated test branches
│   ├── no_ai/           # Deterministic heuristics
│   ├── ai/              # AI-assisted matching
│   ├── stagehand/       # Agent execution workflows
│   └── utils/           # Framework unit tests
├── runner.py            # CLI parser entrypoint
├── orchestrator.py      # Execution flow pipeline manager
└── reporter.py          # Unified stats and summary builder
```

## Architectural Flow

```
   +--------------+      +-------------------+      +-------------+
   |  runner.py   | ---> |  orchestrator.py  | ---> |   pytest    |
   +--------------+      +-------------------+      +-------------+
                                                           |
  +------------------+       +---------------+             |
  |  HealingPage     | <==== | conftest.py   | <===========+
  |  HealingLocator  |       +---------------+
  +------------------+               |
           |                         v
           |               +--------------------+
           | === click/ ===> | failure_class.py |
           |     fill        | flaky_detection  |
           v                 +--------------------+
   +---------------+
   |  ai_helper.py | ===> Ollama / HF Serverless / Gemini API
   +---------------+
```

1. **CLI Execution (`runner.py` / `orchestrator.py`):** Launches selected branch folder, forwarding flags `--branch`, `--self-heal`, `--classify`, `--flaky-db`.
2. **Pytest Fixture (`conftest.py`):** Instruments Playwright `page` inside the explicit `HealingPage` wrapper.
3. **Execution Interception (`healer.py`):** If a locator click/fill action fails, `HealingLocator` intercepts it, takes a screenshot of the broken UI state, extracts page elements, ranks options via `strategies.py` (optionally calling `ai_helper.py`), heals the element, takes a success screenshot, and resumes execution.
4. **Hooks Logging (`conftest.py` / `failure_classification.py` / `flaky_detection.py`):** Classifies tracebacks on failures, updates flaky counts in SQLite/JSON, and logs event metrics.
5. **Run Consolidation (`reporter.py`):** Gathers metrics and outputs a unified `run_summary.json` containing healed count statistics alongside Matplotlib pie charts.
