# Testing — Run instructions

Quick run instructions and CI notes.

Local run (Windows):

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install
pytest -q
# or use runner
python runner.py
```

Runner examples:

```powershell
python runner.py --parallel 3 --retries 2 --video
python runner.py --target tests/test_login.py
```

CI notes:

- Ensure Playwright browsers are installed (`playwright install`) in the CI job.
- Persist `reports/`, `screenshots/`, `videos/`, and `logs/` as artifacts for debugging.
- The workflow file is `.github/workflows/test-forge.yml`.
