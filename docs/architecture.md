# Test Forge Architecture

## Repo Structure

```text
test-forge/
├── src/
│   ├── pages/           # Page Object Model (POM) classes
│   └── framework/       # Shared intelligent framework core layer
│       ├── self_healing/ # Locator recovery wrappers & strategy matchers
│       │   ├── dom_extractor.py
│       │   ├── strategies.py
│       │   └── healer.py
│       ├── failure_classification.py # Exception categories & regex locator parser
│       ├── flaky_detection.py # SQLite WAL and JSON locked result history
│       └── ai_helper.py # Ollama / HF / Gemini routing client
├── tests/               # isolated test branches
│   ├── no_ai/           # Deterministic heuristics
│   ├── ai/              # AI-assisted matching
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

---

## 🔬 Deep-Dive Technical Mechanics: `no_ai` Deterministic Branch

### 1. ⚡ Self-Healing Locator Engine (`healer.py`, `dom_extractor.py`, `strategies.py`)

#### **When It Triggers & How It Operates**
- **Action-Level Interception**: Self-healing triggers at the **element action level** inside `HealingLocator._run_action_with_healing()` *before* the test case fails.
- **Code Reference**: [src/framework/self_healing/healer.py](file:///c:/Users/Prashant/Desktop/sauceplaywright/src/framework/self_healing/healer.py#L90-L93)
  ```python
  try:
      return action_fn(self._original)  # 1. Attempt original Playwright action
  except Exception as primary_exc:
      # ⚡ 2. CATCH LOCATOR FAILURE IN-FLIGHT BEFORE TEST CASE FAILS
      ...
  ```

#### **Execution Sequence**:
1. **Evidence Capture (Before)**: Captures `reports/no_ai/screenshots/before_heal_<ts>.png` displaying the broken UI state.
2. **DOM Candidate Extraction**: `dom_extractor.get_candidates(page)` executes client-side JavaScript to scan all interactive elements (`<input>`, `<button>`, `<a>`, `<select>`), extracting attributes (`id`, `name`, `placeholder`, `data-test`, `text`, `className`) and generating live XPaths.
3. **Deterministic Candidate Scoring**: `strategies.match_selectors()` tokenizes the broken selector, computes Levenshtein/string similarity, and applies attribute intersection boosts (ID +0.2, Name +0.2, Data-Test +0.3).
4. **Action Retry**: Re-executes the action (`.fill()`, `.click()`) on the top-ranked fallback locator (`//*[@id="user-name"]`).
5. **Evidence Capture (After)**: Captures `reports/no_ai/screenshots/after_heal_<ts>.png` and appends the healing event payload to `pytest_healing.json`.
6. **Outcome**: The action succeeds and the test case finishes with status **`PASSED (healed)`**.

---

### 2. 🎯 Failure Classification (`failure_classification.py`, `conftest.py`)

#### **Who Calls It & When**
- **Caller**: Called by `pytest_runtest_makereport(item, call)` in [tests/conftest.py](file:///c:/Users/Prashant/Desktop/sauceplaywright/tests/conftest.py#L158-L163).
- **Trigger**: Executed at the end of a test run (`rep.when == 'call'`) **only if the test failed** (`rep.failed == True`) and `--classify` is enabled.

#### **Execution Sequence**:
```python
# conftest.py
if rep.failed and classify:
    result = classify_failure(exc_type, exc_msg, tb_str)
```
1. `classify_failure()` inspects `call.excinfo` (exception type, message, stack trace).
2. Applies rule-based pattern matching to categorize into taxonomy buckets:
   - `Assertion`: Title/text mismatches or `expect()` assertions.
   - `Locator Issue`: Selector not found or element unresolved.
   - `Timeout`: Page or network timeout exceeded.
   - `Other`: Unclassified errors.
3. Uses regex to extract target locator string from stack trace logs (`waiting for locator("...")`).
4. Writes payload to `reports/pytest_classifications.json` using atomic `FileLock`.

---

### 3. 📊 Process-Safe Flaky Detection (`flaky_detection.py`)

#### **2-Phase Lifecycle**

```
Phase 1: Record Result (conftest.py) ──► Phase 2: Compute Variance Score (reporter.py)
```

1. **Phase 1 (Recording)**:
   - Called by `pytest_runtest_makereport` in [tests/conftest.py](file:///c:/Users/Prashant/Desktop/sauceplaywright/tests/conftest.py#L148-L155) at the end of **every single test attempt**.
   - Invokes `FlakyDetector.record_result(test_id, outcome)` to append `'passed'` or `'failed'` to `reports/flaky_history.json` (protected via `FileLock`).

2. **Phase 2 (Scoring & Flagging)**:
   - Executed by `RunReporter` in [reporter.py](file:///c:/Users/Prashant/Desktop/sauceplaywright/reporter.py#L206-L248) during HTML report generation.
   - Computes variance score across historical runs:
     $$\text{Flaky Score} = \frac{2 \times \min(\text{passes}, \text{failures})}{\text{total runs}}$$
   - **Categorization**:
     - Consistent Pass (`['passed', 'passed', 'passed']`) $\rightarrow$ **Stable Pass** (Score 0.0)
     - Consistent Fail (`['failed', 'failed', 'failed']`) $\rightarrow$ **Stable Failure / Bug** (Score 0.0)
     - Alternating/Mixed (`['failed', 'failed', 'passed']`) $\rightarrow$ **FLAKY DETECTED** (Score $\ge 0.2$)
   - Increments **Flaky (detected)** counter on dashboard and attaches **FLAKY** badge to the test item.
