import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://login.personifyhealth.com/auth/realms/platform/protocol/openid-connect/auth?client_id=platform-ui&redirect_uri=https%3A%2F%2Fapp.personifyhealth.com%2F&state=ae4eab78-2a78-4382-82ad-95ba2249dc16&response_mode=fragment&response_type=code&scope=openid&nonce=1c582fbd-577a-43d9-9814-cf003f695205&code_challenge=d4AugjMIk_BP5MOJtuByga2ykvw-vlEwzz64KiYkhsk&code_challenge_method=S256")
    page.get_by_placeholder("Enter your email or username").click()
    page.get_by_placeholder("Enter your email or username").fill("ayusharyan_singh@intuit.com")
    page.get_by_label("Continue").click()
    page.get_by_placeholder("Enter your password").click()
    page.get_by_placeholder("Enter your password").click()
    page.get_by_placeholder("Enter your password").click()
    page.get_by_placeholder("Enter your password").fill("Ayush@17082003")
    page.get_by_label("Sign In").click()
    page.goto("https://app.personifyhealth.com/#/home")
    page.get_by_role("heading", name="Stats").click()
    page.get_by_label("Track Steps").click()
    page.get_by_placeholder("Enter number of steps").click()
    page.get_by_placeholder("Enter number of steps").fill("10372")
    page.get_by_text("Cancel Save").click()
    page.get_by_role("button", name="Save").click()
    page.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
