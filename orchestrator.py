import uuid
import time
import json
import subprocess
import platform
import os
from pathlib import Path
import shutil
from reporter import RunReporter

ROOT = Path(__file__).parent
REPORTS = ROOT / "reports"
LOGS = ROOT / "logs"
VIDEOS = ROOT / "videos"
SCREENSHOTS = ROOT / "screenshots"
SESSION_DIR = ROOT / "session"

def ensure_dirs():
    for d in (REPORTS, LOGS, VIDEOS, SCREENSHOTS, SESSION_DIR):
        d.mkdir(parents=True, exist_ok=True)

def clear_previous():
    for d in (REPORTS, LOGS, VIDEOS, SCREENSHOTS):
        if d.exists():
            for child in d.iterdir():
                try:
                    if child.is_file() or child.is_symlink():
                        child.unlink()
                    elif child.is_dir():
                        shutil.rmtree(child)
                except Exception:
                    pass

def run_pytest(test_args, html_path: Path, junit_path: Path, parallel: int, extra_opts: dict):
    cmd = ["python", "-m", "pytest"] + test_args + [f"--html={html_path}", f"--self-contained-html", f"--junitxml={junit_path}"]
    if parallel and parallel > 0:
        cmd = ["python", "-m", "pytest", "-n", str(parallel)] + test_args + [f"--html={html_path}", f"--self-contained-html", f"--junitxml={junit_path}"]
        
    if extra_opts.get("branch"):
        cmd.append(f"--branch={extra_opts['branch']}")
    if extra_opts.get("flaky_db"):
        cmd.append(f"--flaky-db={extra_opts['flaky_db']}")
    if extra_opts.get("classify"):
        cmd.append("--classify")
    if extra_opts.get("self_heal"):
        cmd.append("--self-heal")
    if extra_opts.get("ai_model"):
        cmd.append(f"--ai-model={extra_opts['ai_model']}")
        
    # Pass branch to subprocess via env so healer.py knows where to write screenshots
    env = os.environ.copy()
    if extra_opts.get("branch"):
        env["PYTEST_BRANCH"] = extra_opts["branch"]
        
    print("Running command:", " ".join(cmd))
    start = time.time()
    res = subprocess.run(cmd, env=env)
    duration = time.time() - start
    return res.returncode, duration

def execute_run(options: dict):
    ensure_dirs()
    if options.get("clear"):
        clear_previous()

    run_id = uuid.uuid4().hex[:8]
    session_file = SESSION_DIR / f'session_{run_id}.json'
    
    branch = options.get("branch")
    path = options.get("path", ".")
    pattern = options.get("pattern", "test_*.py")
    parallel = options.get("parallel", 0)
    retries = options.get("retries", 0)
    resume = options.get("resume", False)
    markers = options.get("markers")
    kexpr = options.get("kexpr")
    
    self_heal = options.get("self_heal", False)
    classify = options.get("classify", False)
    flaky_db = options.get("flaky_db", "reports/flaky_history.json")
    ai_model = options.get("ai_model")

    if branch and path == ".":
        if branch == "no_ai":
            path = "tests/no_ai"
        elif branch == "ai":
            path = "tests/ai"
        elif branch == "stagehand":
            path = "tests/stagehand"

    base_path = Path(path)
    
    if resume:
        last = sorted(SESSION_DIR.glob('session_*.json'))
        if not last:
            print('No previous session found to resume')
            return
        session_file = last[-1]
        with open(session_file) as fh:
            state = json.load(fh)
        nodeids = state.get('failed_nodeids', [])
        if not nodeids:
            print('No failed tests in last session')
            return
        print(f'Rerunning {len(nodeids)} failed tests from {session_file}')
        html = REPORTS / f'rerun_{session_file.stem}.html'
        junit = REPORTS / f'rerun_{session_file.stem}.xml'
        
        extra_opts = {
            "branch": branch or state.get("env", {}).get("branch", "no_ai"),
            "flaky_db": flaky_db,
            "classify": classify,
            "self_heal": self_heal,
            "ai_model": ai_model
        }
        rc, duration = run_pytest(nodeids, html, junit, parallel, extra_opts)
        print('Rerun complete. See reports.')
        return

    if base_path.is_file():
        test_paths = [base_path]
    else:
        test_paths = [p for p in base_path.rglob(pattern) if p.is_file()]

    if not test_paths:
        print(f"No tests found under {base_path} with pattern {pattern}")
        return

    test_args = [str(p) for p in test_paths]
    if markers:
        test_args += ["-m", markers]
    if kexpr:
        test_args += ["-k", kexpr]

    branch_dir = REPORTS / (branch or "default")
    branch_dir.mkdir(parents=True, exist_ok=True)
    html = branch_dir / "report.html"
    junit = branch_dir / "report.xml"
    
    extra_opts = {
        "branch": branch,
        "flaky_db": flaky_db,
        "classify": classify,
        "self_heal": self_heal,
        "ai_model": ai_model
    }
    
    pytest_class_path = REPORTS / "pytest_classifications.json"
    pytest_heal_path = REPORTS / "pytest_healing.json"
    for p in (pytest_class_path, pytest_heal_path):
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

    rc, duration = run_pytest(test_args, html, junit, parallel, extra_opts)
    
    from runner import parse_junit, failed_nodeids_from_junit, collect_videos_map, inject_videos_into_pytest_html
    stats = parse_junit(junit)
    failed_nodeids = failed_nodeids_from_junit(junit)

    session_state = {
        'run_id': run_id,
        'stats': stats,
        'failed_nodeids': failed_nodeids,
        'duration': duration,
        'env': {
            'platform': platform.platform(),
            'python': platform.python_version(),
            'branch': branch
        }
    }
    with open(session_file, 'w') as fh:
        json.dump(session_state, fh, indent=2)

    attempt = 0
    while retries > 0 and failed_nodeids:
        attempt += 1
        print(f'\nRetry attempt {attempt} for {len(failed_nodeids)} failed tests')
        html_r = branch_dir / f'retry_{run_id}_{attempt}.html'
        junit_r = branch_dir / f'retry_{run_id}_{attempt}.xml'
        rc2, dur2 = run_pytest(failed_nodeids, html_r, junit_r, parallel, extra_opts)
        parsed2 = parse_junit(junit_r)
        
        failed_nodeids = failed_nodeids_from_junit(junit_r)
        retries -= 1
        session_state['failed_nodeids'] = failed_nodeids
        session_state['stats_retry_' + str(attempt)] = parsed2
        with open(session_file, 'w') as fh:
            json.dump(session_state, fh, indent=2)

    classifications = {}
    if pytest_class_path.exists():
        try:
            with open(pytest_class_path, "r", encoding="utf-8") as f:
                classifications = json.load(f)
        except Exception:
            pass
            
    healing_events = []
    if pytest_heal_path.exists():
        try:
            with open(pytest_heal_path, "r", encoding="utf-8") as f:
                healing_events = json.load(f)
        except Exception:
            pass

    reporter = RunReporter(run_id, branch_dir)
    summary = reporter.generate_summary(stats, healing_events, Path(flaky_db))
    reporter.save_failure_classifications(classifications)
    reporter.generate_healing_patch(healing_events)
    reporter.generate_beautiful_html(html, junit, healing_events, classifications, branch or "default")
    reporter.make_chart(stats, title=f"Run {run_id} ({branch or 'default'})")

    try:
        videos_map = collect_videos_map(VIDEOS)
        inject_videos_into_pytest_html(html, videos_map, failed_nodeids)
    except Exception as e:
        print('Failed to inject videos into report:', e)

    print("\n" + "="*40)
    print(f" RUN SUMMARY (ID: {run_id})")
    print("="*40)
    print(f"Total Tests run:  {summary['total']}")
    
    healed_tests_names = {h["test_name"] for h in healing_events}
    passed_healed_count = len(healed_tests_names)
    normal_passed_count = max(0, summary["passed"] - passed_healed_count)
    
    print(f"Passed:           {normal_passed_count}")
    print(f"Passed (healed):  {passed_healed_count}")
    print(f"Failed:           {summary['failed']}")
    print(f"Skipped:          {summary['skipped']}")
    print(f"Flaky (detected): {summary['flaky']}")
    print("="*40)
    
    if classifications:
        print("\nFailures by Classification:")
        cats = {}
        for test_name, c in classifications.items():
            cat = c.get("category", "Other")
            cats[cat] = cats.get(cat, 0) + 1
        for cat, count in cats.items():
            print(f"  - {cat}: {count}")
            
    if healing_events:
        print("\nSelf-Healing Actions taken:")
        for h in healing_events:
            print(f"  - Test '{h['test_name']}': Healed locator '{h['original_selector']}' using '{h['healed_selector']}' on '{h['action']}'")

    print(f"\nHTML Report: {html}")
    print(f"Unified JSON: {branch_dir / 'run_summary.json'}")
    print("="*40)

    # Clean up temporary retry files to keep directory clean
    for p in branch_dir.glob("retry_*"):
        try:
            p.unlink()
        except Exception:
            pass
