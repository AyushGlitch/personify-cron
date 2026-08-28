#!/usr/bin/env python3
"""Log daily steps and sleep to Personify Health."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout, sync_playwright

from config import Config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Log steps and sleep to Personify Health")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run with a visible browser and save screenshots on each step",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip selector validation (login-only smoke test)",
    )
    return parser.parse_args()


def screenshot(page: Page, directory: Path, name: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"Screenshot saved: {path}")


def first_matching_locator(page: Page, selectors: str):
    """Try comma-separated selectors; return the first match."""
    for selector in (part.strip() for part in selectors.split(",") if part.strip()):
        locator = page.locator(selector).first
        if locator.count() > 0:
            return locator
    raise RuntimeError(f"No element matched selectors: {selectors}")


def login(page: Page, config: Config, debug: bool) -> None:
    print(f"Opening login page: {config.login_url}")
    page.goto(config.login_url, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)

    if debug:
        screenshot(page, config.screenshot_dir, "01-login-page")

    email_input = first_matching_locator(page, config.selector_email)
    email_input.fill(config.email)

    password_input = first_matching_locator(page, config.selector_password)
    password_input.fill(config.password)

    sign_in = first_matching_locator(page, config.selector_sign_in)
    sign_in.click()

    try:
        page.wait_for_load_state("networkidle", timeout=30_000)
    except PlaywrightTimeout:
        page.wait_for_load_state("domcontentloaded", timeout=10_000)

    if _looks_like_sso_redirect(page):
        if debug:
            screenshot(page, config.screenshot_dir, "02-sso-redirect")
        raise RuntimeError(
            "Redirected to employer SSO. Direct login automation is not supported. "
            "Use device sync (Fitbit/Apple Health) or configure session cookies manually."
        )

    if debug:
        screenshot(page, config.screenshot_dir, "02-after-login")


def _looks_like_sso_redirect(page: Page) -> bool:
    url = page.url.lower()
    sso_hints = (
        "microsoftonline.com",
        "okta.com",
        "onelogin.com",
        "pingidentity.com",
        "auth0.com",
        "google.com/o/oauth",
        "saml",
        "sso",
    )
    return any(hint in url for hint in sso_hints)


def open_page(page: Page, url: str | None, nav_selector: str | None, label: str) -> None:
    if url:
        print(f"Opening {label} page: {url}")
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        return

    if nav_selector:
        print(f"Navigating to {label} via: {nav_selector}")
        page.locator(nav_selector).first.click()
        page.wait_for_load_state("domcontentloaded", timeout=20_000)
        page.wait_for_timeout(1500)
        return

    raise RuntimeError(
        f"No navigation configured for {label}. Set {label.upper()}_PAGE_URL or SELECTOR_{label.upper()}_NAV in .env"
    )


def submit_steps(page: Page, config: Config, debug: bool) -> None:
    open_page(page, config.steps_page_url or None, config.selector_steps_nav or None, "steps")

    if debug:
        screenshot(page, config.screenshot_dir, "03-steps-page")

    steps_input = page.locator(config.selector_steps_input).first
    steps_input.click()
    steps_input.fill(config.daily_steps)

    page.locator(config.selector_steps_save).first.click()
    page.wait_for_timeout(2000)

    if debug:
        screenshot(page, config.screenshot_dir, "04-steps-saved")

    print(f"Submitted steps: {config.daily_steps}")


def submit_sleep(page: Page, config: Config, debug: bool) -> None:
    open_page(page, config.sleep_page_url or None, config.selector_sleep_nav or None, "sleep")

    if debug:
        screenshot(page, config.screenshot_dir, "05-sleep-page")

    if config.selector_sleep_hours_input:
        hours_input = page.locator(config.selector_sleep_hours_input).first
        hours_input.click()
        hours_input.fill(config.sleep_hours)

    if config.selector_sleep_minutes_input:
        minutes_input = page.locator(config.selector_sleep_minutes_input).first
        minutes_input.click()
        minutes_input.fill(config.sleep_minutes)

    page.locator(config.selector_sleep_save).first.click()
    page.wait_for_timeout(2000)

    if debug:
        screenshot(page, config.screenshot_dir, "06-sleep-saved")

    print(f"Submitted sleep: {config.sleep_hours}h {config.sleep_minutes}m")


def run(config: Config, debug: bool, skip_validation: bool) -> None:
    if not skip_validation:
        config.validate_selectors()

    headless = config.headless and not debug

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        try:
            login(page, config, debug)

            if skip_validation:
                print("Login smoke test completed.")
                return

            submit_steps(page, config, debug)
            submit_sleep(page, config, debug)
            print("Done.")
        except Exception:
            config.screenshot_dir.mkdir(parents=True, exist_ok=True)
            screenshot(page, config.screenshot_dir, "error")
            raise
        finally:
            context.close()
            browser.close()


def main() -> None:
    args = parse_args()
    config = Config.from_env()

    try:
        run(config, debug=args.debug, skip_validation=args.skip_validation)
    except Exception as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
