import pytest
from playwright.sync_api import Playwright, Locator
import uuid
from pathlib import Path
import shutil
import os
import json

from src.framework.core.flaky_detection import FlakyDetector, FileLock
from src.framework.core.failure_classification import classify_failure
from src.framework.no_ai.healer import HealingPage

def pytest_addoption(parser):
    parser.addoption("--branch", action="store", default=None, help="Target branch folder")
    parser.addoption("--flaky-db", action="store", default="reports/flaky_history.json", help="Path to flaky database")
    parser.addoption("--classify", action="store_true", help="Enable failure classification")
    parser.addoption("--self-heal", action="store_true", help="Enable self-healing locators")
    parser.addoption("--ai-model", action="store", default=None, help="AI model for healing")


@pytest.fixture(scope="function")
def setup_teardown(playwright: Playwright, request):
    browser = playwright.chromium.launch()
    repo_root = Path(__file__).parents[1]
    videos_dir = repo_root / "videos"
    logs_dir = repo_root / "logs"
    screenshots_dir = repo_root / "screenshots"
    
    videos_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    unique_id = uuid.uuid4().hex[:8]
    per_test_video_dir = videos_dir / unique_id
    per_test_video_dir.mkdir(parents=True, exist_ok=True)

    context = browser.new_context(record_video_dir=str(per_test_video_dir))
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    page = context.new_page()
    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto("https://www.saucedemo.com/")

    self_heal = request.config.getoption("--self-heal")
    branch = request.config.getoption("--branch")
    ai_model = request.config.getoption("--ai-model")
    
    use_ai = (branch == "ai" or ai_model is not None)
    
    wrapped_page = HealingPage(
        page, 
        test_name=request.node.nodeid, 
        enabled=self_heal, 
        use_ai=use_ai, 
        max_attempts=3
    )

    request.node._video_dir = per_test_video_dir

    yield wrapped_page

    # Teardown
    try:
        page.screenshot(path=str(screenshots_dir / f"snapshots_{unique_id}.png"))
    except Exception:
        pass
        
    try:
        context.tracing.stop(path=str(logs_dir / f"tracing_{unique_id}.zip"))
    except Exception:
        pass
        
    context.close()
    browser.close()

    # Write healing events to pytest_healing.json
    if hasattr(wrapped_page, "healed_attempts") and wrapped_page.healed_attempts:
        heal_path = Path("reports/pytest_healing.json")
        heal_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = str(heal_path) + ".lock"
        try:
            with FileLock(lock_path):
                data = []
                if heal_path.exists():
                    try:
                        with open(heal_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except Exception:
                        pass
                data.extend(wrapped_page.healed_attempts)
                with open(heal_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[conftest] Error writing healing events: {e}")

    # collect video files
    vids = []
    if per_test_video_dir.exists():
        for p in per_test_video_dir.rglob('*'):
            if p.is_file():
                vids.append(p)
    request.node._video_paths = vids
    try:
        meta = {'nodeid': request.node.nodeid}
        (per_test_video_dir / 'metadata.json').write_text(json.dumps(meta))
    except Exception:
        pass

# Define paths for clear session fixture
REPO_ROOT = Path(__file__).parents[1]
VIDEOS_DIR = REPO_ROOT / 'videos'
SCREENSHOTS_DIR = REPO_ROOT / 'screenshots'
LOGS_DIR = REPO_ROOT / 'logs'

def clear_directory(directory: Path):
    if directory.exists():
        for child in directory.iterdir():
            try:
                if child.is_file() or child.is_symlink():
                    child.unlink()
                elif child.is_dir():
                    shutil.rmtree(child)
            except Exception as e:
                print(f'Failed to delete {child}. Reason: {e}')

@pytest.fixture(scope='session', autouse=True)
def clear_videos_and_screenshots():
    for d in (VIDEOS_DIR, SCREENSHOTS_DIR, LOGS_DIR):
        clear_directory(d)

def _rel_path_from_reports(p: Path):
    try:
        return str(p.relative_to(REPO_ROOT))
    except Exception:
        return str(p)

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    
    config = item.config
    flaky_db = config.getoption("--flaky-db")
    classify = config.getoption("--classify")
    
    if rep.when == 'call':
        test_id = item.nodeid
        
        # 1. Record pass/fail outcome to flaky history
        if flaky_db:
            try:
                db_path = Path(flaky_db)
                detector = FlakyDetector(db_path)
                detector.record_result(test_id, rep.outcome)
            except Exception as e:
                print(f"[conftest] Error recording flaky result: {e}")
                
        # 2. Failure Classification
        if rep.failed and classify:
            exc_type = call.excinfo.type.__name__ if call.excinfo else "Unknown"
            exc_msg = str(call.excinfo.value) if call.excinfo else ""
            tb_str = str(call.excinfo.traceback) if call.excinfo else ""
            
            result = classify_failure(exc_type, exc_msg, tb_str)
            
            class_path = Path("reports/pytest_classifications.json")
            class_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path = str(class_path) + ".lock"
            try:
                with FileLock(lock_path):
                    data = {}
                    if class_path.exists():
                        try:
                            with open(class_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                        except Exception:
                            pass
                    data[test_id] = result.to_dict()
                    with open(class_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
            except Exception as e:
                print(f"[conftest] Error writing classification: {e}")

    # Attach video link to HTML report
    if rep.when == 'call' and rep.failed:
        video_paths = getattr(item, '_video_paths', None)
        if not video_paths:
            return
        try:
            from pytest_html import extras
        except Exception:
            extras = None
        if extras:
            extra = getattr(rep, 'extra', [])
            for vp in video_paths:
                rel = _rel_path_from_reports(vp)
                link = f"{rel}"
                extra.append(extras.html(f'<p>Video: <a href="{link}">{vp.name}</a></p>'))
            rep.extra = extra
