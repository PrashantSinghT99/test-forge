# Test Forge Automation Framework

A lightweight yet robust test automation framework designed for **learning and architectural demonstration**.  
It utilizes the **Page Object Model (POM)** pattern, a custom **Click-based CLI orchestrator**, and **Pytest** to handle UI automation with Playwright.

This project is augmented with a shared core testing layer providing failure classification, process-safe flaky test history tracking, and self-healing locators (supporting both local heuristics and AI models).

---

## 🚀 Key Features

- **Execution Branches**
  - `tests/no_ai/`: Completely deterministic production-ready tests using localized self-healing heuristics.
  - `tests/ai/`: AI-assisted testing integrating open-source local and cloud-hosted LLM endpoints.

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
│   ├── pages/           # Page Object Model classes (LoginPage, Inventory, Cart, Checkout)
│   ├── framework/       # Core framework layer
│   │   ├── no_ai/       # Heuristic healing: healer, strategies, dom_extractor
│   │   ├── ai/          # AI-assisted healing: ai_helper routing client
│   │   ├── core/        # Shared core features: failure_classification, flaky_detection
│   │   └── core/        # Shared core features: failure_classification, flaky_detection
│   └── tests/           # Internal test helpers / utilities
├── tests/               # Pytest tests divided by execution branch
│   ├── no_ai/           # Deterministic healing & classification (unique test flows)
│   ├── ai/              # AI-assisted healing (distinct checkout and locator flows)
│   ├── utils/           # Framework unit tests
│   └── conftest.py      # Pytest hooks, page wrappers, command flags
├── scripts/
│   └── generate_dashboard.py # Python script generating GitHub Pages dashboard index.html
├── runner.py            # CLI entrypoint
├── orchestrator.py      # Runner pipeline execution manager
├── reporter.py          # Summary generator & visual report manager
├── Makefile             # Standardized local execution commands (Ruff, Install, Test)
└── docs/                # Design architecture & documentation
```

---

## ⚙️ Quick Setup

All execution and environment setup is standardized around the `Makefile`.

### 1. Create and activate environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install dependencies & browsers
```bash
make install
make install-browsers
```

### 3. Verify Code Quality (Linter)
We use Ruff for linting and code formatting:
```bash
make lint         # Checks lint and formatting
make lint-fix     # Automatically fixes lint violations and reformats files
```

---

## 🏃 Usage

### Makefile Commands (Recommended)

Run branch-specific suites with automated setup flags using simple make targets:

*   **Deterministic Suite (No AI):** Runs with self-healing, classification, and 2 retries.
    ```bash
    make test-no-ai
    ```
*   **AI-Assisted Suite:** Runs with AI-assisted locator healing and classification.
    ```bash
    # Set your API token before running:
    export HF_API_TOKEN="your-hf-token"
    # Or: export GEMINI_API_KEY="your-gemini-key"
    make test-ai
    ```
*   **Run All Suites:** Runs both execution branches sequentially.
    ```bash
    make test-all
    ```
*   **Clean Outputs:** Cleans all generated reports, screenshots, videos, and logs.
    ```bash
    make clear
    ```

---

## 📊 Reporting & Outputs

Outputs are saved under the `reports/[branch_name]/` directory (e.g., `reports/no_ai/` or `reports/ai/`):
- `report.html`: Custom HTML report with embedded screenshots and Playwright execution videos.
- `run_summary.json`: Unified statistics containing passed, healed, failed, and flaky counts.
- `failure_classification.json`: Categorized exceptions and target locator details.
- `healing_patch.diff`: Git diff containing the suggested code modifications for healed locators.

---

## 🤖 CI/CD Integration

The repository uses two scheduled and event-driven GitHub Actions workflows:

1.  **Test Forge CI/CD Pipeline (`.github/workflows/test-forge.yml`)**:
    *   **Triggers:** Push to `master`, manually, or daily at 02:00 UTC.
    *   **Jobs:** Enforces Ruff linter, runs all three test suites in parallel, automatically opens a Pull Request with healed locators if a patch is found, and publishes the consolidated dashboard to GitHub Pages.
    *   **PR Title Formats:**
        *   `[AI Self-Healing] Fix locator drift in ai - DO NOT MERGE`
        *   `[Non-AI Self-Healing] Fix locator drift in no_ai - DO NOT MERGE`
2.  **Cleanup Stale PRs (`.github/workflows/cleanup-stale-prs.yml`)**:
    *   **Triggers:** Daily at 03:00 UTC (1 hour after tests) or manually.
    *   **Jobs:** Finds open Pull Requests containing `Self-Healing` in the title that are older than 1 day, automatically closes them, and deletes their temporary branches to keep the repository clean.

---

## 🔮 Future Enhancements

- **Memory-Based Self-Healing:** Implement a historical baseline snapshot database (`reports/element_baselines.json`). Instead of parsing keywords from failed selectors, the healer will:
  1. Save element metadata (tag, classes, parent DOM tree indices, text) on the first successful run.
  2. On locator failure, compare active DOM candidates against this saved snapshot memory.
  3. Pick the closest match by weighted similarity rules, heal the element, and update the baseline memory.
- **Heal Impact Analysis:** Map dependencies between Page Object Model (POM) classes and test suites. When a locator is healed inside a shared page class (like `LoginPage`), the engine will:
  1. Identify all test cases that instantiate or depend on this POM class.
  2. Flag these dependent test cases as "impacted" and automatically run them to verify the healed locator doesn't cause regressions elsewhere in the suite.
