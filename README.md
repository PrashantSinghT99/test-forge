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

## 🔮 Future Enhancements Roadmap

> These are the planned next steps to evolve Test Forge from a Senior SDET project into a Principal Architect portfolio piece. Ordered by implementation priority.

---

### ✅ Priority 1 — Impact Analysis & Regression Optimization

**Problem:** Running the full suite on every push is expensive and slow.

**Solution:** Build an `impact_analyzer.py` pre-flight script that runs *before* Pytest:
1. Run `git diff origin/master` to identify changed application files.
2. Send the diff + test file mapping to `ai_helper` (Ollama / Gemini).
3. The LLM returns a list of test IDs affected by those changes.
4. `runner.py` consumes the output as a `-k` expression, slicing 500 tests down to the 10 that matter.

**Outcome:** CI runtimes drop by 80–90%. PR feedback loops shrink from minutes to seconds.

---

### ✅ Priority 2 — Self-Healing "Memory" (Persistent Healing Cache)

**Problem:** The framework heals in-flight every single run, even for the same broken locator — paying the full timeout + API cost each time.

**Solution:** Implement a `reports/active_heals.json` healing cache:
1. On successful healing, write `{ "original_selector": "healed_selector" }` to the cache.
2. Intercept `HealingPage.locator()` before it even tries the original — if a cached mapping exists, swap immediately.
3. Bypass the timeout and AI query entirely until the developer merges the `.diff`.

**Outcome:** Zero-latency re-healing for known-broken locators. Eliminates redundant API calls entirely.

---

### 🔬 Priority 3 — Vision-Language Model (VLM) Healing

**Problem:** DOM extraction can fail on obfuscated dynamic class names (React, Angular minified output). A JSON DOM snapshot is insufficient context for ambiguous layouts.

**Solution:** When a locator fails, take a full-page Playwright screenshot and send the base64-encoded image *alongside* the DOM snippet to `gemini-2.5-flash` (multimodal) or `gpt-4o`:
> *"I was trying to click the 'Checkout' button. Look at this screenshot, find the button visually, and return its CSS selector from the DOM provided."*

**Outcome:** Healing accuracy on complex/obfuscated UIs improves dramatically. Positions the framework for real-world enterprise applications.

---

### 🔬 Priority 4 — Evaluation Layer (DeepEval Integration)

**Problem:** How do you know the AI healed the *right* element and didn't hallucinate? (e.g., healed "Submit Order" to "Cancel Order" instead.)

**Solution:** Create an `evals/` directory with a nightly evaluation script:
1. Feed historical `pytest_healing.json` logs into [DeepEval](https://github.com/confident-ai/deepeval).
2. DeepEval uses an LLM judge to score healing quality: *"Was the healed locator semantically equivalent to the original intent?"*
3. Flag low-confidence heals for human review.

**Outcome:** Makes AI healing *trustworthy and auditable*, not just functional. Critical for any regulated or enterprise environment.

---

### 🧪 Priority 5 — DSPy Prompt Optimization

**Problem:** The hardcoded prompts in `ai_helper.py` were written once and never optimized. Their performance degrades as page complexity grows and models change.

**Solution:** Replace hardcoded string prompts with [DSPy](https://github.com/stanfordnlp/dspy) modules:
1. Collect 20+ examples of `(broken_locator, DOM_context) -> correct_healed_locator` from past run logs.
2. DSPy automatically rewrites and optimizes the prompt via few-shot bootstrapping.
3. The optimized prompt is serialized and checked into `prompts/healer_prompt.json`.

**Outcome:** The framework self-improves its own AI instructions over time. Prompt quality compounds — the more the framework is used, the better it gets.

---

### 🏢 Priority 6 — Distributed Flaky State for Parallel CI

**Problem:** `FileLock` + SQLite WAL works perfectly on a single machine. With 10 parallel GitHub Actions runners, there is no shared filesystem.

**Solution:** Add a `FLAKY_STORAGE=redis` environment variable flag:
1. If set, `FlakyDetector` writes results to a free Redis cloud instance (e.g., [Upstash](https://upstash.com/)) or PostgreSQL via a simple REST API call.
2. All parallel runners converge on the same shared state.
3. Keep the local JSON fallback when `FLAKY_STORAGE` is not set.

**Outcome:** Proves enterprise-scale architectural awareness. Flakiness detection works correctly across massive distributed test grids.

---

> **Recommended implementation order:** Priority 1 → 2 → 3 → 4 → 5 → 6  
> Implementing even Priority 1 + 2 places this framework in the top 1% of QA engineering portfolios worldwide.
