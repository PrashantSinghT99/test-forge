# Test Forge Automation Framework

A lightweight yet robust test automation framework designed for **learning and architectural demonstration**.  
It utilizes the **Page Object Model (POM)** pattern, a custom **Click-based CLI orchestrator**, and **Pytest** to handle UI automation with Playwright.

This project is augmented with a shared core testing layer providing failure classification, process-safe flaky test history tracking, and self-healing locators (supporting both local heuristics and AI models).

---

## 🚀 Key Features

- **Execution Branches**
  - `tests/no_ai/`: Completely deterministic production-ready tests using localized self-healing heuristics.
  - `tests/ai/`: AI-assisted testing integrating open-source local and cloud-hosted LLM endpoints.
  - `tests/stagehand/`: Declarative AI Browser Agent planning tests executing goals step-by-step.

- **Failure Classification**
  - Parses test failures and categorizes exceptions into typed results (`Timeout`, `Locator Issue`, `Assertion`, `Other`).
  - Automatically extracts failed locators from exception messages.

- **Process-Safe Flaky Detection**
  - Tracks historical results using SQLite (WAL-mode) or JSON (with cross-platform file locking).
  - Enforces `min_runs=3` sample guard before flagging test cases as flaky.

- **Self-Healing Locator Guardrails**
  - Captures `before_heal.png` and `after_heal.png` screenshots on successful locator healing.
  - Caps healing attempts at 3 per action, requiring a minimum similarity score threshold of 0.5.
  - Healed tests are tracked as `PASSED (healed)` in summaries.

- **Multi-Provider AI Client**
  - Dynamically routes requests for selector healing and planning to:
    1. **Local Ollama:** `qwen2.5-coder:1.5b` running on `http://localhost:11434`.
    2. **Hugging Face Serverless API:** `Qwen/Qwen2.5-Coder-7B-Instruct` using `HF_API_TOKEN`.
    3. **Gemini API:** `gemini-2.5-flash` using `GEMINI_API_KEY`.
    4. **Local Heuristics:** Falls back to offline similarity logic if APIs are unavailable.

---

## 🔬 Deterministic (`no_ai`) Technical Breakdown

For a complete architectural overview, refer to [docs/architecture.md](file:///c:/Users/Prashant/Desktop/sauceplaywright/docs/architecture.md).

### 1. ⚡ Self-Healing Locator Engine ([healer.py](file:///c:/Users/Prashant/Desktop/sauceplaywright/src/framework/no_ai/healer.py))
- **Action-Level Interception**: Intercepts element failures in real-time inside `HealingLocator._run_action_with_healing()` *before* the test case fails.
- **Before/After Evidence**: Captures `before_heal_<ts>.png` (showing missing/broken selector state) and `after_heal_<ts>.png` (showing recovered state).
- **Candidate Scoring**: `dom_extractor.py` scans active browser elements via client-side JavaScript, and `strategies.py` ranks candidates using string similarity & attribute intersection boosts (ID +0.2, Name +0.2, Data-Test +0.3).
- **Git Patch Generation**: Writes `reports/no_ai/healing_patch.diff` with 3-line unified diff context lines, allowing CI/CD to auto-create Pull Requests.

### 2. 🎯 Failure Classification ([failure_classification.py](file:///c:/Users/Prashant/Desktop/sauceplaywright/src/framework/core/failure_classification.py))
- **Invoked By**: `pytest_runtest_makereport` hook in [conftest.py](file:///c:/Users/Prashant/Desktop/sauceplaywright/tests/conftest.py).
- **When**: Runs at test completion (`rep.when == 'call'`) whenever `rep.failed == True` and `--classify` is active.
- **Rules**: Categorizes failures into taxonomy buckets (`Assertion`, `Locator Issue`, `Timeout`, `Other`) and extracts target locators using regex.

### 3. 📊 Process-Safe Flaky Detection ([flaky_detection.py](file:///c:/Users/Prashant/Desktop/sauceplaywright/src/framework/core/flaky_detection.py))
- **Phase 1 (Recording)**: `conftest.py` records `'passed'` or `'failed'` for every run/retry into `reports/flaky_history.json` (atomic via `FileLock`).
- **Phase 2 (Scoring)**: `reporter.py` computes variance score:
  $$\text{Flaky Score} = \frac{2 \times \min(\text{passes}, \text{failures})}{\text{total runs}}$$
  Tests alternating between pass and fail ($\text{score} \ge 0.2$) are flagged as **FLAKY DETECTED** on the HTML dashboard.

---

## 🛠️ Project Structure
```text
test-forge/
├── src/
│   ├── pages/           # Page Object Model classes
│   ├── framework/       # Core framework layer
│   │   ├── self_healing/ # Healer, strategies, extractor
│   │   ├── stagehand/    # Stagehand AI planning agent
│   │   ├── failure_classification.py
│   │   ├── flaky_detection.py
│   │   └── ai_helper.py
│   └── tests/           # Internal test helpers / utilities
├── tests/               # Pytest tests divided by execution branch
│   ├── no_ai/           # Deterministic healing & classification
│   ├── ai/              # AI-assisted healing
│   ├── stagehand/       # Declarative planner agent tests
│   ├── utils/           # Framework unit tests
│   └── conftest.py      # Pytest hooks, page wrappers, command flags
├── runner.py            # CLI entrypoint
├── orchestrator.py      # Runner pipeline execution manager
├── reporter.py          # Summary generator & Matplotlib charts
└── docs/                # Design architecture & documentation
```

---

## ⚙️ Quick Setup

### 1. Create and activate environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install dependencies & browsers
```bash
pip install -r requirements.txt
playwright install
```

---

## 🏃 Usage

### CLI Commands

The custom entrypoint `runner.py` manages all pipelines:

**Run deterministic tests with self-healing & classification**
```bash
python runner.py --branch no_ai --self-heal --classify
```

**Run AI-assisted self-healing branch**
```bash
# Using Hugging Face Serverless API
export HF_API_TOKEN="your-hf-token"
python runner.py --branch ai --self-heal --classify

# Or using local Ollama (ensure Ollama is running)
python runner.py --branch ai --self-heal --classify
```

**Run declarative Stagehand browser agent planner**
```bash
python runner.py --branch stagehand
```

### Command Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--branch` | Target branch suite (`no_ai`, `ai`, `stagehand`) | None |
| `--self-heal` | Enable self-healing locator wrapper | False |
| `--classify` | Enable failure classification | False |
| `--flaky-db` | Path to flaky history JSON/SQLite file | `reports/flaky_history.json` |
| `--ai-model` | AI model override parameter | None |
| `--resume` | Resume last session (rerun failed tests) | False |
| `--parallel` | Number of concurrent workers (`pytest-xdist`) | 0 |
| `--retries` | Number of retries for failed tests | 0 |

---

## 📊 Reporting & Outputs

Outputs are saved in the `reports/` folder:
- `reports/run_summary.json`: Unified run statistics containing passed, failed, flaky, and healed counts.
- `reports/failure_classification.json`: Categorized exceptions and locator details.
- `reports/chart_[run_id].png`: Visual execution outcome distribution pie chart.
- `reports/report_[run_id].html`: Standard HTML execution report.

---

## 🔮 Future Enhancements

- **Memory-Based Self-Healing:** Implement a historical baseline snapshot database (`reports/element_baselines.json`). Instead of parsing keywords from failed selectors, the healer will:
  1. Save element metadata (tag, classes, parent DOM tree indices, text) on the first successful run.
  2. On locator failure, compare active DOM candidates against this saved snapshot memory.
  3. Pick the closest match by weighted similarity rules, heal the element, and update the baseline memory.
- **Heal Impact Analysis:** Map dependencies between Page Object Model (POM) classes and test suites. When a locator is healed inside a shared page class (like `LoginPage`), the engine will:
  1. Identify all test cases that instantiate or depend on this POM class.
  2. Flag these dependent test cases as "impacted" and automatically run them to verify the healed locator doesn't cause regressions elsewhere in the suite.
