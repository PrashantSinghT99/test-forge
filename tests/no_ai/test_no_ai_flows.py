"""
Deterministic (No-AI) Test Suite for SauceDemo Application.

This module contains end-to-end test scenarios demonstrating:
1. Self-healing locator capabilities for broken elements.
2. Automated failure classification for assertion mismatches.
3. State-based flaky test detection across execution retry windows.
4. Clean Page Object Model (POM) passing flows.
"""
import pytest
from playwright.sync_api import expect
from src.pages.LoginPage import Loginpage
import tempfile
from pathlib import Path

# Shared temporary counter file for tracking flaky test state across pytest retries
FLAKY_COUNTER_FILE = Path(tempfile.gettempdir()) / "flaky_counter.txt"

def test_login_healing_standard_user(setup_teardown):
    """
    Demonstrates deterministic self-healing locator recovery during execution.

    Args:
        setup_teardown (HealingPage): Playwright page wrapped with Self-Healing Proxy.

    Flow:
        - Executes `.fill()` using an intentionally invalid XPath selector (`user-name-broken`).
        - The `HealingPage` intercepts the locator timeout, extracts DOM elements, matches `//*[@id="user-name"]`,
          captures before/after screenshots, and completes the login flow.
    """
    page = setup_teardown
    # ⚠️  INTENTIONALLY BROKEN LOCATOR — DO NOT FIX THIS LINE ⚠️
    # This test is a permanent self-healing demo fixture for the no_ai branch.
    # The broken locator below will ALWAYS fail on its own.
    # When run with --self-heal (CI/CD only), the engine heals it at runtime,
    # the test passes, and a PR is opened with the fix — which we intentionally
    # never merge, so the locator stays broken for the next CI/CD run.
    page.locator("//input[@id='user-name-broken']").fill("standard_user")  # BROKEN — DO NOT CHANGE
    
    # Complete rest of flow using POM
    login_page = Loginpage(page)
    login_page.enter_password("secret_sauce")
    login_page.click_loginbtn()
    
    expect(page.locator("//span[@class='title']")).to_contain_text("Products")

def test_no_ai_assertion_failure(setup_teardown):
    """
    Demonstrates deterministic failure classification for text assertion mismatches.

    Args:
        setup_teardown (HealingPage): Playwright page wrapped with Self-Healing Proxy.

    Flow:
        - Navigates to login page and asserts an incorrect title string ("Incorrect Logo Name").
        - Triggers an `AssertionError` which is classified under `Assertion` in failure summary.
    """
    page = setup_teardown
    login_page = Loginpage(page)
    login_page.enter_username("standard_user")
    # Assert wrong text to trigger classification
    expect(login_page.loginPage_title()).to_contain_text("Incorrect Logo Name")

def test_flaky_demo(setup_teardown):
    """
    Demonstrates flaky test detection across retry attempts.

    Args:
        setup_teardown (HealingPage): Playwright page wrapped with Self-Healing Proxy.

    Flow:
        - Reads an execution count from disk across pytest retry runs.
        - Deliberately fails on run #1 and #2.
        - Passes on retry attempt #3, registering as a detected Flaky test in the reporter.
    """
    # Simulated flaky test: fails the first 2 times, then passes
    count = 0
    if FLAKY_COUNTER_FILE.exists():
        try:
            count = int(FLAKY_COUNTER_FILE.read_text().strip())
        except Exception:
            pass
            
    count += 1
    FLAKY_COUNTER_FILE.write_text(str(count))
    
    if count < 3:
        assert False, f"Simulated flaky failure (Run {count}/3)"
    else:
        try:
            FLAKY_COUNTER_FILE.unlink()
        except Exception:
            pass
        assert True

# 🟢 Clean Passing Tests using real POM on live Sauce Demo site
def test_login_standard_user_pass(setup_teardown):
    """
    Verifies successful user authentication using Page Object Model.

    Args:
        setup_teardown (HealingPage): Playwright page wrapped with Self-Healing Proxy.
    """
    page = setup_teardown
    login_page = Loginpage(page)
    credentials = {"username": "standard_user", "password": "secret_sauce"}
    inventory_page = login_page.do_login(credentials)
    
    expect(inventory_page.inventory_header).to_be_visible()
    expect(inventory_page.inventory_header).to_contain_text("Products")

def test_inventory_add_item_pass(setup_teardown):
    """
    Verifies adding an item to the shopping cart updates cart badge count.

    Args:
        setup_teardown (HealingPage): Playwright page wrapped with Self-Healing Proxy.
    """
    page = setup_teardown
    login_page = Loginpage(page)
    credentials = {"username": "standard_user", "password": "secret_sauce"}
    inventory_page = login_page.do_login(credentials)
    
    # Use real POM action to add Backpack to cart
    inventory_page.click_addremove_to_cart("Sauce Labs Backpack")
    
    # Verify shopping cart badge is updated to "1"
    expect(page.locator(".shopping_cart_badge")).to_contain_text("1")
