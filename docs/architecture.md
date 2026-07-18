# Project architecture — ASCII diagram

Repository layout (on-disk):

```
sauceplaywright/
├─ .github/
│  └─ workflows/
│     └─ playwright.yml
├─ runner.py
├─ requirements.txt
├─ README.md
├─ Makefile
├─ .gitignore
├─ src/
│  ├─ __init__.py
│  ├─ assets/
│  ├─ data/
│  ├─ pages/                # Page Object Model (POM) implementations
│  │  ├─ LoginPage.py
│  │  ├─ Inventory.py
│  │  ├─ Cart.py
│  │  └─ Checkout.py
	│  └─ pytest.ini
│  ├─ tests/                # Internal helpers used by tests
│  │  └─ utils/
│  │     ├─ __init__.py
│  │     └─ helpers.py
├─ tests/                  # Top-level pytest tests
│  ├─ conftest.py
│  ├─ test_login.py
│  ├─ test_inventory.py
│  ├─ test_logout.py
│  └─ test_checkout.py
├─ logs/
├─ screenshots/
├─ videos/
```

Flow (high level):

1. Developer / CI triggers test run (`python runner.py` or `pytest`)
2. `runner.py` parses options, sets environment, and orchestrates pytest execution
3. Pytest loads tests from `tests/` and applies fixtures from `tests/conftest.py`
4. Fixtures launch Playwright browser contexts and return page objects
5. Tests instantiate Page Objects from `src.pages` (LoginPage, Inventory, Cart, Checkout)
6. Page Objects perform UI interactions; assertions validate UI state
7. On failures, fixtures attach screenshots/videos and write logs
8. Artifacts are stored in `screenshots/`, `videos/`, and `logs/` (HTML reports are optional)

Suggestions for cleanup / follow-ups:

- Remove the empty `src/utils/` folder if it is not needed.
- Consolidate test helpers: choose either `src/tests/utils` or a top-level `tests/utils` to avoid duplication.
- Optionally create a `reports/` directory when enabling HTML report generation.
- Add a short `docs/testing.md` with run examples and CI notes (see `README.md` for quick commands).
