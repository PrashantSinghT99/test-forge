import pytest
from pathlib import Path
import tempfile
import time
import os

from src.testing.failure_classification import classify_failure, FailureResult
from src.testing.flaky_detection import FlakyDetector, FileLock
from src.testing.self_healing.strategies import parse_keywords, calculate_similarity, match_selectors

def test_failure_classification():
    # 1. Timeout Classification
    res_timeout = classify_failure("TimeoutError", "Page.click: Timeout 30000ms exceeded.")
    assert res_timeout.category == "Timeout"
    
    # 2. Assertion Classification
    res_assert = classify_failure("AssertionError", "expected 'Products' but got 'Prod'", "assert 'Products' == 'Prod'")
    assert res_assert.category == "Assertion"
    
    # 3. Locator Issue Classification with selector extraction
    exc_msg = "playwright._impl._api_types.Error: waiting for locator(\"xpath=//input[@id='user-name-bad']\")"
    res_locator = classify_failure("Error", exc_msg)
    assert res_locator.category == "Locator Issue"
    assert res_locator.locator == "xpath=//input[@id='user-name-bad']"

def test_flaky_detector_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "flaky_history.json"
        detector = FlakyDetector(db_path)
        
        test_id = "tests/test_login.py::test_login_standard_user"
        
        # 1. Guard check: < 3 runs
        detector.record_result(test_id, "passed")
        detector.record_result(test_id, "failed")
        assert detector.calculate_flaky_score(test_id) == 0.0
        
        # 2. Check 3 runs: passed, failed, failed -> score should be 2 * 1 / 3 = 0.667
        detector.record_result(test_id, "failed")
        score = detector.calculate_flaky_score(test_id)
        assert abs(score - 0.6666) < 0.01
        assert detector.is_flaky(test_id)
        
        # 3. Suggest rerun check (since passed is in history and last was failed)
        assert detector.suggest_rerun(test_id, "failed")

def test_flaky_detector_sqlite():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "flaky_history.db"
        detector = FlakyDetector(db_path)
        
        test_id = "tests/test_login.py::test_login_standard_user"
        
        detector.record_result(test_id, "passed")
        detector.record_result(test_id, "failed")
        assert detector.calculate_flaky_score(test_id) == 0.0
        
        detector.record_result(test_id, "failed")
        score = detector.calculate_flaky_score(test_id)
        assert abs(score - 0.6666) < 0.01
        assert detector.is_flaky(test_id)

def test_healing_strategies():
    # 1. Keyword parser
    keywords = parse_keywords("//input[@id='user-name']")
    assert "user" in keywords and "name" in keywords
    
    # 2. Similarity match (Exact match on ID)
    failed_sel = "//input[@id='user-name-bad']"
    candidate = {
        "tag": "input",
        "id": "user-name",
        "name": "user-name",
        "data_test": "username",
        "placeholder": "Username",
        "text": "",
        "className": "input_error form_input"
    }
    score = calculate_similarity(failed_sel, candidate)
    assert score >= 0.5
    
    # 3. Match selectors from list
    candidates = [
        {"tag": "input", "id": "password", "name": "password", "xpath": "xpath1", "css": "css1"},
        {"tag": "input", "id": "user-name", "name": "user-name", "xpath": "xpath2", "css": "css2"}
    ]
    matches = match_selectors(failed_sel, candidates, threshold=0.5)
    assert len(matches) == 1
    assert matches[0][1]["id"] == "user-name"
