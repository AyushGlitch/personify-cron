#!/usr/bin/env python3
"""Log daily steps and sleep to Personify Health."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout, sync_playwright

from config import Config
from locators import first_matching_locator, locator_from_spec


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Log steps and sleep to Personify Health")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run with a visible browser window (recommended for local testing)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Same as --headed, plus save screenshots at each step",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip selector validation (login-only smoke test)",
    )
    parser.add_argument(
        "--manual-login",
        action="store_true",
        help="You complete login + 2FA in the browser, then press Enter to continue",
    )
    parser.add_argument(
        "--steps-only",
        action="store_true",
        help="Log steps only (skip sleep)",
    )
    parser.add_argument(
        "--sleep-only",
        action="store_true",
        help="Log sleep only (skip steps — useful when steps already logged today)",
    )
    parser.add_argument(
        "--save-auth",
        action="store_true",
        help="Save browser session to auth.json after login (reuse with --use-auth)",
    )
    parser.add_argument(
        "--use-auth",
        action="store_true",
        help="Reuse saved session from auth.json (skip login / 2FA)",
    )
    return parser.parse_args()


def screenshot(page: Page, directory: Path, name: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"Screenshot saved: {path}")


def _describe_page(page: Page) -> str:
    return f"URL={page.url!r}  title={page.title()!r}"


def _is_security_code_page(page: Page) -> bool:
    for spec in (
        "placeholder:Enter Security Code",
        "label:Security Code",
        "text:Enter Security Code",
    ):
        try:
            locator_from_spec(page, spec).wait_for(state="visible", timeout=2_000)
            return True
        except Exception:
            continue
    return False


def _is_login_page(page: Page, config: Config) -> bool:
    try:
        first_matching_locator(page, config.selector_continue)
        return True
    except Exception:
        pass
    try:
        first_matching_locator(page, config.selector_sign_in)
        return True
    except Exception:
        return False


def wait_for_app(page: Page, config: Config) -> None:
    """Wait until login succeeded and the Personify app loaded."""
    print(f"Waiting for app... ({_describe_page(page)})")

    if _is_security_code_page(page):
        screenshot(page, config.screenshot_dir, "02fa-security-code")
        raise RuntimeError(
            "Stuck on 2FA Security Code page.\n"
            "Save session after manual login:\n"
            "  python log_health.py --headed --manual-login --save-auth"
        )

    if _is_login_page(page, config):
        screenshot(page, config.screenshot_dir, "login-failed")
        raise RuntimeError(
            "Still on the login page — check email/password in .env.\n"
            f"Screenshot: {config.screenshot_dir / 'login-failed.png'}"
        )

    page.wait_for_url("**/app.personifyhealth.com/**", timeout=60_000)

    for spec in ("role:heading:Stats", "text:Stats", "role:link:Home", "text:Steps"):
        try:
            first_matching_locator(page, spec)
            print(f"Logged in. ({_describe_page(page)})")
            page.wait_for_timeout(1000)
            return
        except RuntimeError:
            continue

    screenshot(page, config.screenshot_dir, "app-timeout")
    raise RuntimeError(
        "Login may have succeeded but app content did not load.\n"
        f"  {_describe_page(page)}\n"
        f"  Screenshot: {config.screenshot_dir / 'app-timeout.png'}"
    )


def ensure_stats_page(page: Page, config: Config) -> None:
    stats_url = config.stats_page_url
    if "#/stats-page" not in page.url:
        print(f"Navigating to stats page: {stats_url}")
        page.goto(stats_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

    first_matching_locator(page, "role:heading:Stats, text:Stats")
    print(f"On stats page. ({_describe_page(page)})")


def open_tracker(page: Page, nav_selectors: str, metric: str) -> bool:
    """Click a Track link on the stats page. Returns False if already logged today."""
    for spec in (part.strip() for part in nav_selectors.split(",") if part.strip()):
        try:
            track = locator_from_spec(page, spec)
            track.wait_for(state="visible", timeout=3_000)
            track.scroll_into_view_if_needed()
            print(f"Opening {metric} tracker: {spec}")
            track.click()
            page.wait_for_timeout(1500)
            return True
        except Exception:
            continue

    print(
        f"Track {metric} link not found — {metric.lower()} may already be logged for today. Skipping."
    )
    return False


def open_steps_tracker(page: Page, config: Config) -> bool:
    return open_tracker(page, config.selector_steps_nav, "Steps")


def open_sleep_tracker(page: Page, config: Config) -> bool:
    return open_tracker(page, config.selector_sleep_nav, "Sleep")


def _session_expired_message(config: Config) -> str:
    return (
        "Saved session expired or invalid.\n"
        "Re-save with:\n"
        "  python log_health.py --headed --manual-login --save-auth"
    )


def save_auth_state(context, config: Config) -> None:
    context.storage_state(path=str(config.auth_file))
    print(f"Session saved: {config.auth_file}")


def session_login(page: Page, config: Config, debug: bool) -> None:
    if not config.auth_file.is_file():
        raise RuntimeError(
            f"No session file at {config.auth_file}\n"
            "Create one with:\n"
            "  python log_health.py --headed --manual-login --save-auth"
        )

    print(f"Using saved session: {config.auth_file}")
    page.goto(config.stats_page_url, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    if debug:
        screenshot(page, config.screenshot_dir, "00-session-load")

    if _is_security_code_page(page) or _is_login_page(page, config):
        screenshot(page, config.screenshot_dir, "session-expired")
        raise RuntimeError(_session_expired_message(config))

    wait_for_app(page, config)


def authenticate(
    page: Page,
    config: Config,
    debug: bool,
    *,
    use_auth: bool,
    manual_login: bool,
) -> None:
    if use_auth and manual_login:
        raise ValueError("Use either --use-auth or --manual-login, not both")

    if use_auth:
        session_login(page, config, debug)
    elif manual_login:
        complete_manual_login(page, config)
    else:
        login(page, config, debug)


def complete_manual_login(page: Page, config: Config) -> None:
    print(f"Opening login page: {config.login_url}")
    page.goto(config.login_url, wait_until="domcontentloaded")
    print()
    print("=" * 60)
    print("  Complete login in the browser (including 2FA if shown).")
    print("  Wait until you see the Stats page (or Home), then press Enter.")
    print("  Tip: add --save-auth to reuse this session later.")
    print("=" * 60)
    print()
    input("Press Enter when ready... ")
    wait_for_app(page, config)


def login(page: Page, config: Config, debug: bool) -> None:
    print(f"Opening login page: {config.login_url}")
    page.goto(config.login_url, wait_until="domcontentloaded")
    # app.personifyhealth.com redirects to Keycloak OIDC login with fresh state/nonce
    page.wait_for_load_state("networkidle", timeout=30_000)
    page.wait_for_timeout(1500)

    if debug:
        screenshot(page, config.screenshot_dir, "01-login-page")

    email_input = first_matching_locator(page, config.selector_email)
    email_input.fill(config.email)

    if config.selector_continue:
        print("Clicking Continue...")
        first_matching_locator(page, config.selector_continue).click()
        page.wait_for_timeout(1500)
        if debug:
            screenshot(page, config.screenshot_dir, "01b-password-page")

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

    wait_for_app(page, config)


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


def submit_steps(page: Page, config: Config, debug: bool) -> None:
    ensure_stats_page(page, config)

    if debug:
        screenshot(page, config.screenshot_dir, "03-stats-page")

    if not open_steps_tracker(page, config):
        return

    if debug:
        screenshot(page, config.screenshot_dir, "03-steps-modal")

    steps_input = locator_from_spec(page, config.selector_steps_input)
    steps_input.click()
    steps_input.fill(config.daily_steps)

    locator_from_spec(page, config.selector_steps_save).click()
    page.wait_for_timeout(2000)

    # Wait for modal to close before sleep entry
    steps_input.wait_for(state="hidden", timeout=10_000)

    if debug:
        screenshot(page, config.screenshot_dir, "04-steps-saved")

    print(f"Submitted steps: {config.daily_steps}")


def submit_sleep(page: Page, config: Config, debug: bool) -> None:
    ensure_stats_page(page, config)

    if debug:
        screenshot(page, config.screenshot_dir, "05-stats-page")

    if not open_sleep_tracker(page, config):
        return

    if debug:
        screenshot(page, config.screenshot_dir, "05-sleep-modal")

    sleep_hours = config.resolve_sleep_hours()
    sleep_input = first_matching_locator(page, config.selector_sleep_input)
    sleep_input.click()
    sleep_input.fill(sleep_hours)

    locator_from_spec(page, config.selector_sleep_save).click()
    page.wait_for_timeout(2000)

    sleep_input.wait_for(state="hidden", timeout=10_000)

    if debug:
        screenshot(page, config.screenshot_dir, "06-sleep-saved")

    print(f"Submitted sleep: {sleep_hours} hours")


def run(
    config: Config,
    headed: bool,
    debug: bool,
    skip_validation: bool,
    steps_only: bool,
    sleep_only: bool,
    manual_login: bool,
    save_auth_flag: bool,
    use_auth: bool,
) -> None:
    if steps_only and sleep_only:
        raise ValueError("Use only one of --steps-only or --sleep-only")

    if not skip_validation:
        config.validate_selectors(steps_only=steps_only, sleep_only=sleep_only)

    headless = config.headless and not headed

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless, slow_mo=300 if headed else 0)
        context_kwargs: dict = {"viewport": {"width": 1280, "height": 900}}
        if use_auth and config.auth_file.is_file():
            context_kwargs["storage_state"] = str(config.auth_file)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        logged_in = False

        try:
            authenticate(
                page,
                config,
                debug,
                use_auth=use_auth,
                manual_login=manual_login,
            )
            logged_in = True

            if skip_validation:
                print("Login smoke test completed.")
                return

            if not sleep_only:
                submit_steps(page, config, debug)
            if not steps_only:
                submit_sleep(page, config, debug)
            print("Done.")
        except Exception:
            config.screenshot_dir.mkdir(parents=True, exist_ok=True)
            screenshot(page, config.screenshot_dir, "error")
            raise
        finally:
            if save_auth_flag and logged_in:
                save_auth_state(context, config)
            context.close()
            browser.close()


def main() -> None:
    args = parse_args()
    config = Config.from_env()

    headed = args.headed or args.debug

    try:
        run(
            config,
            headed=headed,
            debug=args.debug,
            skip_validation=args.skip_validation,
            steps_only=args.steps_only,
            sleep_only=args.sleep_only,
            manual_login=args.manual_login,
            save_auth_flag=args.save_auth,
            use_auth=args.use_auth,
        )
    except Exception as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
