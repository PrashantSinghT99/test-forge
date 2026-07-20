"""
Generates the Test Forge QA Intelligence Dashboard index.html for GitHub Pages.
Called from the CI/CD deploy-report job after reports are consolidated.
"""
import sys
from pathlib import Path

def make_dashboard(reports_dir: str = "reports"):
    out = Path(reports_dir) / "index.html"
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Forge - QA Intelligence Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 40px 20px; }
        .container { max-width: 860px; width: 100%; background: #1e293b; padding: 40px; border-radius: 16px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }
        h1 { color: #38bdf8; text-align: center; margin-bottom: 8px; font-size: 2rem; }
        .subtitle { text-align: center; color: #94a3b8; margin-bottom: 36px; font-size: 0.95rem; }
        .branch-card { display: flex; justify-content: space-between; align-items: center; background: #334155; padding: 22px 28px; border-radius: 12px; margin-bottom: 16px; border: 1px solid #475569; transition: border-color 0.2s; }
        .branch-card:hover { border-color: #38bdf8; }
        .branch-info .branch-name { font-size: 1.1rem; font-weight: 700; margin-bottom: 4px; }
        .branch-info .branch-desc { font-size: 0.82rem; color: #94a3b8; }
        .btn { background: #0284c7; color: white; padding: 10px 22px; border-radius: 8px; text-decoration: none; font-size: 0.9rem; font-weight: 600; transition: background 0.2s, transform 0.1s; display: inline-block; }
        .btn:hover { background: #0369a1; transform: translateY(-1px); }
    </style>
</head>
<body>
    <div class="container">
        <h1>&#128202; QA Intelligence Dashboard</h1>
        <p class="subtitle">Test Forge - Parallel Branch Execution Reports</p>
        <div class="branch-card">
            <div class="branch-info">
                <div class="branch-name">&#128302; Deterministic Branch (No AI)</div>
                <div class="branch-desc">Self-healing locators - Failure classification - Flaky detection</div>
            </div>
            <a class="btn" href="no_ai/index.html">View Reports</a>
        </div>
        <div class="branch-card">
            <div class="branch-info">
                <div class="branch-name">&#129302; AI-Assisted Branch</div>
                <div class="branch-desc">LLM-powered healing - AI assertion analysis</div>
            </div>
            <a class="btn" href="ai/index.html">View Reports</a>
        </div>
        <div class="branch-card">
            <div class="branch-info">
                <div class="branch-name">&#127381; Stagehand Branch (Browser Agent)</div>
                <div class="branch-desc">Declarative AI browser agent execution</div>
            </div>
            <a class="btn" href="stagehand/index.html">View Reports</a>
        </div>
    </div>
</body>
</html>"""
    out.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {out}")

if __name__ == "__main__":
    reports_dir = sys.argv[1] if len(sys.argv) > 1 else "reports"
    make_dashboard(reports_dir)
