# Project architecture — ASCII diagram

C:/Users/Prashant/Desktop/sauceplaywright.worktrees/ascii-diagram-project-architecture

├─ .github/
│  └─ workflows/
│     └─ playwrigth.yml
├─ runner.py
├─ requirements.txt
├─ README.md
├─ Makefile
├─ .gitignore
├─ src/
│  ├─ __init__.py
│  ├─ pages/                # Page Object Model (POM) implementations
│  │  ├─ __init__.py
│  │  ├─ LoginPage.py
│  │  ├─ Inventory.py
│  │  ├─ Cart.py
│  │  └─ Checkout.py
│  └─ tests/                # Helper utilities used by tests (helpers, fixtures helpers)
│     └─ utils/
│        ├─ __init__.py
│        └─ helpers.py
├─ tests/                  # Top-level pytest tests (moved here for convention)
│  ├─ conftest.py
│  ├─ test_login.py
│  ├─ test_inventory.py
│  ├─ test_logout.py
│  └─ test_checkout.py


Flow (high level):

1. Developer / CI triggers test run (python runner.py or pytest)
2. runner.py parses options, sets environment, optionally calls pytest programmatically
3. pytest loads tests from `tests/` and applies fixtures from `tests/conftest.py`
4. fixtures (setup_teardown) launch Playwright browser and return a page
5. tests instantiate Page Objects from `src.pages.*` (LoginPage, Inventory, Cart, Checkout)
6. Page Objects perform UI interactions and return page-level objects for chaining
7. Assertions verify UI state; on failures, fixtures attach screenshots / videos
8. Reports, screenshots and videos are collected in `reports/`, `screenshots/`, `videos/`


Suggestions for next edits:
- Add a top-level `pages/` package instead of `src/pages/` only if you prefer imports like `from pages.LoginPage import Loginpage`. Current setup uses `src.pages` as an explicit package.
- Consider adding a test requirements matrix in `tox.ini` and a `pyproject.toml` for tooling.
- Add a testing README in `docs/` with run examples and CI details.
