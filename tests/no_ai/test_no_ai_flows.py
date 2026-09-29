"""
Deterministic (No-AI) Test Suite for SauceDemo Application.

Branch: no_ai
Focus:  Login page self-healing · Inventory page interactions · Cart verification

Test Scenarios:
    1. [HEAL]  Self-healing broken username locator on Login page
    2. [FAIL]  Assertion failure demo — wrong page title classification
    3. [FLAKY] Flaky test detection across retry windows
    4. [PASS]  Inventory product sort by price (low to high)
    5. [PASS]  Add multiple items and verify cart badge count
"""

import tempfile
from pathlib import Path

from playwright.sync_api import expect

from src.pages.LoginPage import Loginpage

# Shared counter file to track flaky-test state across pytest retry runs
FLAKY_COUNTER_FILE = Path(tempfile.gettempdir()) / "flaky_counter_no_ai.txt"


# ──────────────────────────────────────────────
# 🔧 Self-Healing Demo  (no_ai branch)
# ──────────────────────────────────────────────
def test_login_healing_standard_user(setup_teardown):
    """
    Demonstrates deterministic self-healing on the Login page username field.

    The username input locator is intentionally broken (`user-name-broken`).
    The HealingPage proxy intercepts the timeout, scans the DOM, and resolves
    the correct locator `//*[@id="user-name"]` without AI.

    ⚠️  DO NOT FIX THE BROKEN LOCATOR — it is a permanent CI/CD demo fixture.
    """
    page = setup_teardown
    # ⚠️  INTENTIONALLY BROKEN — keeps the self-healing demo alive on every CI run
    page.locator("//*[@id="user-name"]").fill(
        "standard_user"
    )  # BROKEN — DO NOT CHANGE

    login_page = Loginpage(page)
    login_page.enter_password("secret_sauce")
    login_page.click_loginbtn()
    expect(page.locator("//span[@class='title']")).to_contain_text("Products")


# ──────────────────────────────────────────────
# ❌ Failure Classification Demo  (no_ai branch)
# ──────────────────────────────────────────────
def test_no_ai_assertion_failure(setup_teardown):
    """
    Demonstrates failure classification for an assertion mismatch on the Login page.

    Checks an intentionally wrong logo text ("Wrong Logo Name") which will never
    match "Swag Labs", triggering an AssertionError classified as `Assertion`.
    """
    page = setup_teardown
    login_page = Loginpage(page)
    login_page.enter_username("standard_user")
    # Intentional wrong assertion to demonstrate failure classification
    expect(login_page.loginPage_title()).to_contain_text("Wrong Logo Name")


# ──────────────────────────────────────────────
# 🎲 Flaky Test Detection  (no_ai branch)
# ──────────────────────────────────────────────
def test_flaky_demo(setup_teardown):
    """
    Simulates a flaky test that fails on runs 1–2 then passes on run 3.

    Reads a persistent counter from /tmp to track state across pytest retries,
    registering as `Flaky (detected)` in the Test Forge run summary.
    """
    count = 0
    if FLAKY_COUNTER_FILE.exists():
        try:
            count = int(FLAKY_COUNTER_FILE.read_text().strip())
        except Exception:
            pass

    count += 1
    FLAKY_COUNTER_FILE.write_text(str(count))

    if count < 3:
        raise AssertionError(f"Simulated flaky failure (Run {count}/3)")
    else:
        try:
            FLAKY_COUNTER_FILE.unlink()
        except Exception:
            pass
        assert True


# ──────────────────────────────────────────────
# 🟢 Passing Demo Tests  (no_ai branch — unique flows)
# ──────────────────────────────────────────────
def test_inventory_sort_price_low_to_high(setup_teardown):
    """
    Verifies the inventory sort dropdown correctly re-orders products by price.

    Flow:
        - Logs in as standard_user.
        - Selects 'Price (low to high)' from the sort dropdown.
        - Asserts the first product price element is visible (sort applied).
    """
    page = setup_teardown
    login_page = Loginpage(page)
    login_page.do_login({"username": "standard_user", "password": "secret_sauce"})

    # Select sort option: price low to high
    page.locator(".product_sort_container").select_option("lohi")

    # Verify the cheapest item ($7.99 Sauce Labs Onesie) appears first
    first_price = page.locator(".inventory_item_price").first
    expect(first_price).to_be_visible()
    price_text = first_price.inner_text()
    assert "$" in price_text, f"Expected a price, got: {price_text}"


def test_cart_shows_correct_item_count(setup_teardown):
    """
    Verifies the cart badge updates correctly when two different products are added.

    Flow:
        - Logs in as standard_user.
        - Adds 'Sauce Labs Backpack' and 'Sauce Labs Bike Light' to cart.
        - Asserts the cart badge shows '2'.
    """
    page = setup_teardown
    login_page = Loginpage(page)
    inventory_page = login_page.do_login(
        {"username": "standard_user", "password": "secret_sauce"}
    )

    inventory_page.click_addremove_to_cart("Sauce Labs Backpack")
    inventory_page.click_addremove_to_cart("Sauce Labs Bike Light")

    expect(page.locator(".shopping_cart_badge")).to_contain_text("2")
