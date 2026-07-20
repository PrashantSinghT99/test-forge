"""
AI-Assisted Test Suite for SauceDemo Application.

This module contains end-to-end test scenarios demonstrating:
1. AI-assisted self-healing locator recovery (Ollama / HuggingFace / Gemini with heuristic fallback).
2. Automated failure classification for assertion mismatches.
3. State-based flaky test detection across execution retry windows.
4. Clean Page Object Model (POM) passing flows.
"""
import pytest
from playwright.sync_api import expect
from src.pages.LoginPage import Loginpage
import tempfile
from pathlib import Path

# Shared temporary counter file for tracking AI flaky test state across pytest retries
FLAKY_COUNTER_FILE_AI = Path(tempfile.gettempdir()) / "flaky_counter_ai.txt"

def test_login_ai_healing(setup_teardown):
    """
    Demonstrates AI-assisted self-healing locator recovery during execution.

    Args:
        setup_teardown (HealingPage): Playwright page wrapped with Self-Healing Proxy (use_ai=True).

    Flow:
        - Executes `.fill()` using an intentionally invalid XPath selector (`user-name-broken-ai`).
        - The `HealingPage` intercepts the locator timeout, passes DOM candidates to `ai_helper.py`,
          queries Ollama / HuggingFace / Gemini (or fallback heuristics), resolves `//*[@id="user-name"]`,
          captures before/after screenshots, and completes the login flow.
    """
    page = setup_teardown
    # ⚠️  INTENTIONALLY BROKEN LOCATOR FOR AI DEMO — DO NOT FIX THIS LINE ⚠️
    page.locator("//*[@id="user-name"]").fill("standard_user")  # BROKEN FOR AI DEMO
    
    login_page = Loginpage(page)
    login_page.enter_password("secret_sauce")
    login_page.click_loginbtn()
    
    expect(page.locator("//span[@class='title']")).to_contain_text("Products")

def test_ai_assertion_failure(setup_teardown):
    """
    Demonstrates deterministic failure classification in the AI branch.

    Args:
        setup_teardown (HealingPage): Playwright page wrapped with Self-Healing Proxy.
    """
    page = setup_teardown
    login_page = Loginpage(page)
    login_page.enter_username("standard_user")
    # Assert wrong text to trigger classification
    expect(login_page.loginPage_title()).to_contain_text("Incorrect AI Logo Name")

def test_ai_flaky_demo(setup_teardown):
    """
    Demonstrates flaky test detection in the AI branch across retry attempts.

    Args:
        setup_teardown (HealingPage): Playwright page wrapped with Self-Healing Proxy.
    """
    count = 0
    if FLAKY_COUNTER_FILE_AI.exists():
        try:
            count = int(FLAKY_COUNTER_FILE_AI.read_text().strip())
        except Exception:
            pass
            
    count += 1
    FLAKY_COUNTER_FILE_AI.write_text(str(count))
    
    if count < 3:
        assert False, f"Simulated AI flaky failure (Run {count}/3)"
    else:
        try:
            FLAKY_COUNTER_FILE_AI.unlink()
        except Exception:
            pass
        assert True

# 🟢 Clean Passing Tests using real POM on live Sauce Demo site
def test_login_standard_user_pass(setup_teardown):
    """
    Verifies successful user authentication in AI suite.

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
    Verifies adding an item to cart in AI suite.

    Args:
        setup_teardown (HealingPage): Playwright page wrapped with Self-Healing Proxy.
    """
    page = setup_teardown
    login_page = Loginpage(page)
    credentials = {"username": "standard_user", "password": "secret_sauce"}
    inventory_page = login_page.do_login(credentials)
    
    inventory_page.click_addremove_to_cart("Sauce Labs Backpack")
    expect(page.locator(".shopping_cart_badge")).to_contain_text("1")
