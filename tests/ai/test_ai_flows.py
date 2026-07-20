"""
AI-Assisted Test Suite for SauceDemo Application.

Branch: ai
Focus:  Inventory page AI self-healing · Cart page assertions · Full checkout flow

Test Scenarios:
    1. [HEAL]  AI-assisted healing of broken 'Add to Cart' locator on Inventory page
    2. [FAIL]  Assertion failure demo — wrong cart page title classification
    3. [FLAKY] Flaky test detection across retry windows
    4. [PASS]  Full checkout flow: login → add item → cart → checkout → complete
    5. [PASS]  Logout flow: verify redirect back to login after hamburger menu logout
"""

import tempfile
from pathlib import Path

from playwright.sync_api import expect

from src.pages.LoginPage import Loginpage

# Shared counter file for AI flaky-test state across pytest retry runs
FLAKY_COUNTER_FILE_AI = Path(tempfile.gettempdir()) / "flaky_counter_ai.txt"


# ──────────────────────────────────────────────
# 🤖 AI Self-Healing Demo  (ai branch)
# ──────────────────────────────────────────────
def test_inventory_add_to_cart_ai_healing(setup_teardown):
    """
    Demonstrates AI-assisted healing on the Inventory page 'Add to Cart' button.

    Flow:
        - Logs in as standard_user (login locators are correct).
        - Attempts to click 'Add to Cart' using a broken data-test attribute locator.
        - AI HealingPage proxy resolves the correct button via DOM scoring.
        - Verifies cart badge shows '1' after the healed click.

    ⚠️  INTENTIONALLY BROKEN LOCATOR — permanent AI healing demo fixture.
    """
    page = setup_teardown
    login_page = Loginpage(page)
    login_page.do_login({"username": "standard_user", "password": "secret_sauce"})

    # ⚠️  BROKEN locator for Backpack Add-to-Cart button — DO NOT FIX
    page.locator(
        "[data-test='add-to-cart-sauce-labs-backpack-broken']"
    ).click()  # BROKEN — DO NOT CHANGE

    # After AI healing resolves correct button, cart badge should update
    expect(page.locator(".shopping_cart_badge")).to_contain_text("1")


# ──────────────────────────────────────────────
# ❌ Failure Classification Demo  (ai branch)
# ──────────────────────────────────────────────
def test_ai_cart_assertion_failure(setup_teardown):
    """
    Demonstrates AI-branch failure classification for a cart page assertion mismatch.

    Flow:
        - Logs in, adds an item, navigates to the Cart page.
        - Asserts an incorrect cart title ("My Basket") instead of "Your Cart".
        - Triggers AssertionError classified as `Assertion` in failure summary.
    """
    page = setup_teardown
    login_page = Loginpage(page)
    inventory_page = login_page.do_login(
        {"username": "standard_user", "password": "secret_sauce"}
    )

    inventory_page.click_addremove_to_cart("Sauce Labs Backpack")
    cart_page = inventory_page.click_cart_btn()

    # Intentional wrong assertion on cart page title
    expect(cart_page.get_cart_page_title()).to_contain_text("My Basket")


# ──────────────────────────────────────────────
# 🎲 Flaky Test Detection  (ai branch)
# ──────────────────────────────────────────────
def test_ai_flaky_demo(setup_teardown):
    """
    Simulates a flaky test in the AI branch that fails on runs 1–2, passes on run 3.

    Reads a persistent counter from /tmp to track state across pytest retries,
    registering as `Flaky (detected)` in the Test Forge run summary.
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
        raise AssertionError(f"Simulated AI flaky failure (Run {count}/3)")
    else:
        try:
            FLAKY_COUNTER_FILE_AI.unlink()
        except Exception:
            pass
        assert True


# ──────────────────────────────────────────────
# 🟢 Passing Demo Tests  (ai branch — unique flows)
# ──────────────────────────────────────────────
def test_full_checkout_flow(setup_teardown):
    """
    Verifies the complete e-commerce checkout flow from login to order completion.

    Flow:
        - Logs in as standard_user.
        - Adds 'Sauce Labs Fleece Jacket' to cart.
        - Navigates to Cart → Checkout → fills in details → continues to overview.
        - Clicks Finish and asserts the success message "Thank you for your order!".
    """
    page = setup_teardown
    login_page = Loginpage(page)
    inventory_page = login_page.do_login(
        {"username": "standard_user", "password": "secret_sauce"}
    )

    inventory_page.click_addremove_to_cart("Sauce Labs Fleece Jacket")
    cart_page = inventory_page.click_cart_btn()

    expect(cart_page.get_cart_page_title()).to_contain_text("Your Cart")
    expect(cart_page.get_cart_product_text()).to_contain_text(
        "Sauce Labs Fleece Jacket"
    )

    checkout_page = cart_page.click_on_checkout()
    checkout_page.enter_checkout_details("John", "Forge", "10001")
    checkout_page.click_checkout_continue()

    expect(checkout_page.get_checkout_overview()).to_contain_text("Checkout: Overview")

    checkout_page.click_checkout_finish_btn()
    expect(checkout_page.get_checkout_sucess()).to_contain_text(
        "Thank you for your order!"
    )


def test_logout_redirects_to_login(setup_teardown):
    """
    Verifies that logging out via the hamburger menu redirects back to the Login page.

    Flow:
        - Logs in as standard_user.
        - Opens the hamburger menu and clicks Logout.
        - Asserts the login logo ("Swag Labs") is visible on the redirected page.
    """
    page = setup_teardown
    login_page = Loginpage(page)
    inventory_page = login_page.do_login(
        {"username": "standard_user", "password": "secret_sauce"}
    )

    inventory_page.logout()

    # Should be back on login page
    expect(page.locator("//div[@class='login_logo']")).to_contain_text("Swag Labs")
    expect(page.locator("//input[@id='user-name']")).to_be_visible()
