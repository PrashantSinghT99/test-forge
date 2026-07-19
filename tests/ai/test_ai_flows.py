import pytest
from playwright.sync_api import expect
from src.pages.LoginPage import Loginpage

def test_login_ai_healing(setup_teardown):
    page = setup_teardown
    # Deliberately use a broken locator to verify AI healing or fallback path
    page.locator("//input[@id='user-name-broken-ai']").fill("standard_user")
    
    login_page = Loginpage(page)
    login_page.enter_password("secret_sauce")
    login_page.click_loginbtn()
    
    expect(page.locator("//span[@class='title']")).to_contain_text("Products")
