"""
Unified Test Run Reporter and Dashboard Generator.

Parses test metrics, JUnit XML artifacts, failure classifications, and self-healing logs.
Generates glassmorphic HTML dashboards with Base64 embedded screenshots and Git diff patches.
"""
import json
from pathlib import Path
import os
import xml.etree.ElementTree as ET

REPORTS = Path("reports")
REPORTS.mkdir(parents=True, exist_ok=True)

class RunReporter:
    """
    Consolidates session data and generates reports, patches, and unified JSON summaries.
    """
    def __init__(self, run_id: str, reports_dir: Path, schema_version: str = "1.0"):
        """
        Initialize the RunReporter.

        Args:
            run_id (str): Unique execution run identifier hex.
            reports_dir (Path): Output directory path for branch reports.
            schema_version (str): Reporting JSON schema version.
        """
        self.run_id = run_id
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.schema_version = schema_version

    def generate_summary(self, stats: dict, healing_events: list, flaky_db_path: Path) -> dict:
        """
        Aggregates run statistics, healing counts, and flaky test metrics into a JSON summary.

        Args:
            stats (dict): Test outcome counts from JUnit parser (passed, failed, skipped).
            healing_events (list): List of self-healing event dictionaries.
            flaky_db_path (Path): Path to flaky history database.

        Returns:
            dict: Comprehensive summary dictionary.
        """
        passed = stats.get("passed", 0)
        failed = stats.get("failed", 0)
        skipped = stats.get("skipped", 0)
        
        flaky_count = 0
        try:
            from src.testing.flaky_detection import FlakyDetector
            detector = FlakyDetector(flaky_db_path)
            history = detector.load_history()
            for test_id in history:
                if detector.is_flaky(test_id):
                    flaky_count += 1
        except Exception as e:
            print(f"[Reporter] Error reading flaky database for summary: {e}")
                
        healed_count = len(healing_events)
        
        summary = {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "total": passed + failed + skipped,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "flaky": flaky_count,
            "healed": healed_count,
            "healing_events": healing_events
        }
        
        summary_path = self.reports_dir / "run_summary.json"
        try:
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            print(f"[Reporter] Unified summary written to {summary_path}")
        except Exception as e:
            print(f"[Reporter] Failed to write run summary: {e}")
            
        return summary

    def save_failure_classifications(self, classifications: dict):
        """Saves failure classification mapping to JSON file."""
        class_path = self.reports_dir / "failure_classification.json"
        data = {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "classifications": classifications
        }
        try:
            with open(class_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"[Reporter] Failure classifications written to {class_path}")
        except Exception as e:
            print(f"[Reporter] Failed to write failure classifications: {e}")

    def generate_healing_patch(self, healing_events: list):
        patch_lines = []
        for event in healing_events:
            test_name = event.get("test_name", "")
            parts = test_name.split("::")
            file_path_str = parts[0]
            file_path = Path(file_path_str)
            if not file_path.exists():
                file_path = Path(__file__).parent / file_path_str
            if not file_path.exists():
                continue
                
            orig = event.get("original_selector")
            healed = event.get("healed_selector")
            if not orig or not healed:
                continue
                
            try:
                content = file_path.read_text(encoding="utf-8")
                if orig in content:
                    lines = content.splitlines()
                    diff_hunk = []
                    for i, line in enumerate(lines):
                        if orig in line:
                            new_line = line.replace(orig, healed)
                            start_ctx = max(0, i - 2)
                            end_ctx = min(len(lines), i + 3)
                            ctx_before = lines[start_ctx:i]
                            ctx_after = lines[i+1:end_ctx]
                            hunk_len = len(ctx_before) + 1 + len(ctx_after)
                            
                            diff_hunk.append(f"@@ -{start_ctx+1},{hunk_len} +{start_ctx+1},{hunk_len} @@")
                            for l in ctx_before:
                                diff_hunk.append(f" {l}")
                            diff_hunk.append(f"-{line}")
                            diff_hunk.append(f"+{new_line}")
                            for l in ctx_after:
                                diff_hunk.append(f" {l}")
                    
                    if diff_hunk:
                        patch_lines.append(f"diff --git a/{file_path_str} b/{file_path_str}")
                        patch_lines.append(f"--- a/{file_path_str}")
                        patch_lines.append(f"+++ b/{file_path_str}")
                        patch_lines.extend(diff_hunk)
                        patch_lines.append("")
            except Exception as e:
                print(f"[Reporter] Patch generation failed for {file_path_str}: {e}")
                
        if patch_lines:
            patch_path = self.reports_dir / "healing_patch.diff"
            try:
                patch_path.write_text("\n".join(patch_lines) + "\n", encoding="utf-8", newline="\n")
                print(f"[Reporter] Healing patch/PR suggestion written to {patch_path}")
            except Exception as e:
                print(f"[Reporter] Failed to write patch file: {e}")

    def generate_beautiful_html(self, html_path: Path, junit_path: Path, healing_events: list, classifications: dict, branch: str):
        tests = []
        duration = 0.0
        passed = failed = skipped = 0
        
        if junit_path.exists():
            try:
                tree = ET.parse(str(junit_path))
                root = tree.getroot()
                for tc in root.iter('testcase'):
                    classname = tc.attrib.get('classname', '')
                    name = tc.attrib.get('name', '')
                    tc_time = float(tc.attrib.get('time', '0'))
                    duration += tc_time
                    
                    status = 'passed'
                    failure_msg = ''
                    traceback = ''
                    
                    fail_node = tc.find('failure')
                    if fail_node is None:
                        fail_node = tc.find('error')
                    skip_node = tc.find('skipped')
                    
                    if fail_node is not None:
                        status = 'failed'
                        failed += 1
                        failure_msg = fail_node.attrib.get('message', '')
                        traceback = fail_node.text or ''
                    elif skip_node is not None:
                        status = 'skipped'
                        skipped += 1
                    else:
                        passed += 1
                        
                    tests.append({
                        'nodeid': f"{classname}::{name}",
                        'name': name,
                        'classname': classname,
                        'time': tc_time,
                        'status': status,
                        'failure_msg': failure_msg,
                        'traceback': traceback
                    })
            except Exception as e:
                print(f"[Reporter] Failed to parse JUnit for HTML: {e}")

        healed_test_names = {h["test_name"] for h in healing_events}
        healed_count = len(healed_test_names)
        normal_passed = max(0, passed - healed_count)
        
        flaky_count = 0
        try:
            from src.testing.flaky_detection import FlakyDetector
            flaky_db_path = self.reports_dir.parent / "flaky_history.json"
            detector = FlakyDetector(flaky_db_path)
            history = detector.load_history()
            for t_id in history:
                if detector.is_flaky(t_id):
                    # Only count flaky if it ran in this test set
                    if any(t['nodeid'] in t_id or t_id in t['nodeid'] for t in tests):
                        flaky_count += 1
        except Exception:
            pass
            
        patch_content = ""
        patch_path = self.reports_dir / "healing_patch.diff"
        if patch_path.exists():
            try:
                patch_content = patch_path.read_text(encoding="utf-8")
            except Exception:
                pass
                
        class_stats = {}
        for tc_id, c in classifications.items():
            cat = c.get("category", "Other")
            class_stats[cat] = class_stats.get(cat, 0) + 1

        test_list_html = ""
        for idx, t in enumerate(tests):
            nodeid = t['nodeid']
            status_badge = ""
            is_healed = any(h_name in nodeid or nodeid in h_name for h_name in healed_test_names)
            
            is_flaky = False
            try:
                from src.testing.flaky_detection import FlakyDetector
                flaky_db_path = self.reports_dir.parent / "flaky_history.json"
                detector = FlakyDetector(flaky_db_path)
                for t_id in history:
                    if (t_id in nodeid or nodeid in t_id) and detector.is_flaky(t_id):
                        is_flaky = True
                        break
            except Exception:
                pass
                
            if is_healed:
                status_badge = '<span class="badge badge-heal">PASSED (healed)</span>'
            elif is_flaky and t['status'] == 'passed':
                status_badge = '<span class="badge badge-flaky">FLAKY (passed)</span>'
            elif t['status'] == 'failed':
                status_badge = '<span class="badge badge-fail">FAILED</span>'
            else:
                status_badge = '<span class="badge badge-pass">PASSED</span>'
                
            details_html = ""
            click_handler = ""
            if t['status'] == 'failed' and t['traceback']:
                details_id = f"details_{idx}"
                escaped_tb = t['traceback'].replace('<', '&lt;').replace('>', '&gt;')
                details_html = f"""
                <div id="{details_id}" class="test-details" style="display: none;">
                    <strong>Error Message:</strong> {t['failure_msg']}
                    <hr style="border: 0; border-top: 1px solid #27272a; margin: 10px 0;">
                    {escaped_tb}
                </div>
                """
                click_handler = f'onclick="toggleDetails(\'{details_id}\')"'
                
            test_list_html += f"""
            <div class="test-item">
                <div class="test-header" {click_handler} style="{ "cursor: pointer;" if click_handler else "" }">
                    <div class="test-name-group">
                        {status_badge}
                        <span>{t['name']}</span>
                    </div>
                    <span class="test-duration">{t['time']:.2f}s</span>
                </div>
                {details_html}
            </div>
            """

        healing_section_html = ""
        if healing_events:
            import base64
            def encode_base64(path_str, prefix_fallback=None):
                if path_str:
                    p = Path(path_str)
                    if not p.is_absolute():
                        p = Path.cwd() / p
                    if p.exists():
                        try:
                            data = base64.b64encode(p.read_bytes()).decode("utf-8")
                            return f"data:image/png;base64,{data}"
                        except Exception:
                            pass
                if prefix_fallback:
                    scr_dir = Path("screenshots")
                    if scr_dir.exists():
                        matching_files = sorted(scr_dir.glob(f"{prefix_fallback}_*.png"), key=lambda f: f.stat().st_mtime, reverse=True)
                        if matching_files:
                            try:
                                data = base64.b64encode(matching_files[0].read_bytes()).decode("utf-8")
                                return f"data:image/png;base64,{data}"
                            except Exception:
                                pass
                return ""

            healing_cards = ""
            for h in healing_events:
                before_src = encode_base64(h.get("before_screenshot"), "before_heal")
                after_src = encode_base64(h.get("after_screenshot"), "after_heal")
                
                healing_cards += f"""
                <div class="healing-event-card">
                    <div style="font-weight: bold; margin-bottom: 8px;">{h.get('test_name', '').split('::')[-1]}</div>
                    <div style="font-size: 13px; color: var(--text-secondary);">
                        Action: <code style="color: #38bdf8;">{h.get('action')}</code> | 
                        Target: <code style="color: #f43f5e;">{h.get('original_selector')}</code>
                    </div>
                    <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">
                        Healed to: <code style="color: #10b981;">{h.get('healed_selector')}</code>
                    </div>
                    <div class="screenshot-container">
                        <div class="screenshot-box">
                            <img src="{before_src}" alt="Before Heal">
                            <div class="screenshot-label">Before Heal</div>
                        </div>
                        <div class="screenshot-box">
                            <img src="{after_src}" alt="After Heal">
                            <div class="screenshot-label">After Heal</div>
                        </div>
                    </div>
                </div>
                """
            healing_section_html = f"""
            <div class="card">
                <div class="section-title">Self-Healing Activities ({len(healing_events)})</div>
                {healing_cards}
            </div>
            """

        classifications_html = ""
        if class_stats:
            for cat, count in class_stats.items():
                classifications_html += f"""
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 14px;">
                    <span style="color: var(--text-secondary);">{cat}</span>
                    <span style="font-weight: bold;">{count}</span>
                </div>
                """
        else:
            classifications_html = '<div style="color: var(--text-secondary); font-size: 14px;">No failures to classify.</div>'

        patch_section_html = ""
        if patch_content:
            diff_lines = []
            for line in patch_content.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    diff_lines.append(f'<div class="diff-added">{line}</div>')
                elif line.startswith("-") and not line.startswith("---"):
                    diff_lines.append(f'<div class="diff-removed">{line}</div>')
                elif line.startswith("diff") or line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
                    diff_lines.append(f'<div class="diff-header">{line}</div>')
                else:
                    diff_lines.append(f'<div>{line}</div>')
            diff_html = "\n".join(diff_lines)
            
            patch_section_html = f"""
            <div class="card">
                <div class="section-title">Proposed PR Git Patch</div>
                <pre class="diff-code">{diff_html}</pre>
            </div>
            """

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QA Intelligence Report - {branch.upper()}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0b0f19;
            --bg-secondary: #161f30;
            --border-color: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --color-pass: #10b981;
            --color-fail: #ef4444;
            --color-heal: #0ea5e9;
            --color-flaky: #f59e0b;
        }}
        body {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        h1 {{
            margin: 0;
            font-size: 28px;
            background: linear-gradient(135deg, #38bdf8 0%, #0ea5e9 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .run-info {{
            font-size: 14px;
            color: var(--text-secondary);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative;
            overflow: hidden;
        }}
        .stat-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        }}
        .stat-label {{
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-secondary);
            margin-bottom: 10px;
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: 700;
        }}
        .card-pass {{ border-left: 4px solid var(--color-pass); }}
        .card-fail {{ border-left: 4px solid var(--color-fail); }}
        .card-heal {{ border-left: 4px solid var(--color-heal); }}
        .card-flaky {{ border-left: 4px solid var(--color-flaky); }}
        
        .stat-value.pass {{ color: var(--color-pass); }}
        .stat-value.fail {{ color: var(--color-fail); }}
        .stat-value.heal {{ color: var(--color-heal); }}
        .stat-value.flaky {{ color: var(--color-flaky); }}

        .main-layout {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
            margin-bottom: 40px;
        }}
        @media (max-width: 900px) {{
            .main-layout {{
                grid-template-columns: 1fr;
            }}
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 600;
            margin-top: 0;
            margin-bottom: 20px;
            color: var(--text-primary);
        }}
        .card {{
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 30px;
        }}
        .test-item {{
            border-bottom: 1px solid var(--border-color);
            padding: 16px 0;
        }}
        .test-item:last-child {{
            border-bottom: none;
        }}
        .test-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .test-name-group {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .badge {{
            font-size: 11px;
            font-weight: 600;
            padding: 4px 8px;
            border-radius: 4px;
            text-transform: uppercase;
        }}
        .badge-pass {{ background: rgba(16, 185, 129, 0.1); color: var(--color-pass); border: 1px solid rgba(16, 185, 129, 0.2); }}
        .badge-fail {{ background: rgba(239, 68, 68, 0.1); color: var(--color-fail); border: 1px solid rgba(239, 68, 68, 0.2); }}
        .badge-heal {{ background: rgba(14, 165, 233, 0.1); color: var(--color-heal); border: 1px solid rgba(14, 165, 233, 0.2); }}
        .badge-flaky {{ background: rgba(245, 158, 11, 0.1); color: var(--color-flaky); border: 1px solid rgba(245, 158, 11, 0.2); }}
        
        .test-duration {{
            font-size: 13px;
            color: var(--text-secondary);
        }}
        .test-details {{
            margin-top: 15px;
            background: #090d16;
            border-radius: 8px;
            padding: 15px;
            font-family: monospace;
            font-size: 13px;
            overflow-x: auto;
            white-space: pre-wrap;
            border: 1px solid #27272a;
        }}
        .healing-event-card {{
            border: 1px solid var(--border-color);
            background: #111827;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
        }}
        .screenshot-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-top: 15px;
        }}
        .screenshot-box {{
            text-align: center;
        }}
        .screenshot-box img {{
            max-width: 100%;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s;
            cursor: pointer;
        }}
        .screenshot-box img:hover {{
            transform: scale(1.02);
        }}
        .screenshot-label {{
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 6px;
            text-transform: uppercase;
        }}
        .diff-code {{
            background: #090d16;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 13px;
            white-space: pre-wrap;
            border: 1px solid #27272a;
            margin: 0;
            overflow-x: auto;
        }}
        .diff-added {{ color: #4ade80; }}
        .diff-removed {{ color: #f87171; }}
        .diff-header {{ color: #60a5fa; }}
    </style>
    <script>
        function toggleDetails(id) {{
            const details = document.getElementById(id);
            if (details.style.display === 'none' || !details.style.display) {{
                details.style.display = 'block';
            }} else {{
                details.style.display = 'none';
            }}
        }}
    </script>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>📊 QA Intelligence Report</h1>
                <div class="run-info">Branch: <strong>{branch}</strong> | Run ID: <strong>{self.run_id}</strong></div>
            </div>
            <div class="run-info" style="text-align: right;">
                Total Duration: <strong>{duration:.2f}s</strong>
            </div>
        </header>

        <div class="stats-grid">
            <div class="stat-card card-pass">
                <div class="stat-label">Passed</div>
                <div class="stat-value pass">{normal_passed}</div>
            </div>
            <div class="stat-card card-heal">
                <div class="stat-label">Healed</div>
                <div class="stat-value heal">{healed_count}</div>
            </div>
            <div class="stat-card card-fail">
                <div class="stat-label">Failed</div>
                <div class="stat-value fail">{failed}</div>
            </div>
            <div class="stat-card card-flaky">
                <div class="stat-label">Flaky</div>
                <div class="stat-value flaky">{flaky_count}</div>
            </div>
        </div>

        <div class="main-layout">
            <div>
                <div class="card">
                    <div class="section-title">Test Executions ({len(tests)})</div>
                    {test_list_html}
                </div>

                {healing_section_html}
            </div>

            <div>
                <div class="card">
                    <div class="section-title">Failure Classifications</div>
                    {classifications_html}
                </div>

                {patch_section_html}
            </div>
        </div>
    </div>
</body>
</html>"""
        
        try:
            html_path.write_text(html_template, encoding="utf-8")
            print(f"[Reporter] Custom HTML report generated at {html_path}")
        except Exception as e:
            print(f"[Reporter] Failed to write custom HTML report: {e}")

    def make_chart(self, stats: dict, title: str):
        try:
            import matplotlib.pyplot as plt
            labels = ['passed', 'failed', 'skipped']
            sizes = [stats.get('passed', 0), stats.get('failed', 0), stats.get('skipped', 0)]
            colors = ['#2ecc71', '#e74c3c', '#f1c40f']
            plt.figure(figsize=(6, 6))
            plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, colors=colors)
            plt.title(title)
            chart_path = self.reports_dir / f"chart_{self.run_id}.png"
            plt.savefig(chart_path)
            plt.close()
            print(f"[Reporter] Pie chart generated at {chart_path}")
        except Exception as e:
            print(f"[Reporter] matplotlib chart not generated: {e}")
