#!/usr/bin/env python3
"""Log daily steps, sleep, mood, and daily cards to Personify Health."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import replace
from pathlib import Path

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeout, expect, sync_playwright

from config import Config
from locators import first_matching_locator, locator_from_spec


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Log health data to Personify Health")
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
        "--flow",
        choices=("home", "stats"),
        default=None,
        help="home = Healthy Habits on dashboard (default); stats = legacy stats-page flow",
    )
    parser.add_argument(
        "--steps-only",
        action="store_true",
        help="Log steps only",
    )
    parser.add_argument(
        "--sleep-only",
        action="store_true",
        help="Log sleep only",
    )
    parser.add_argument(
        "--skip-mood",
        action="store_true",
        help="Skip mood tracking (home flow)",
    )
    parser.add_argument(
        "--skip-cards",
        action="store_true",
        help="Skip daily cards (home flow)",
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

    hints = (
        "role:heading:Stats",
        "text:Stats",
        "role:link:Home",
        "text:Steps",
        "label:Healthy Habits",
        "text:Healthy Habits",
    )
    for spec in hints:
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


def ensure_home_page(page: Page, config: Config) -> None:
    if "#/home" not in page.url:
        print(f"Navigating to home: {config.home_page_url}")
        page.goto(config.home_page_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
    print(f"On home page. ({_describe_page(page)})")


def ensure_stats_page(page: Page, config: Config) -> None:
    stats_url = config.stats_page_url
    if "#/stats-page" not in page.url:
        print(f"Navigating to stats page: {stats_url}")
        page.goto(stats_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

    first_matching_locator(page, "role:heading:Stats, text:Stats")
    print(f"On stats page. ({_describe_page(page)})")


def open_healthy_habits(page: Page, config: Config) -> None:
    ensure_home_page(page, config)
    try:
        habits = first_matching_locator(page, config.selector_healthy_habits)
        habits.scroll_into_view_if_needed()
        print(f"Opening Healthy Habits: {config.selector_healthy_habits}")
        habits.click()
        page.wait_for_timeout(1500)
    except RuntimeError:
        print("Healthy Habits section not found — may already be expanded.")


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
    page.goto(config.post_login_url(), wait_until="domcontentloaded")
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
    print("  Wait until you see the Home or Stats page, then press Enter.")
    print("  Tip: add --save-auth to reuse this session later.")
    print("=" * 60)
    print()
    input("Press Enter when ready... ")
    wait_for_app(page, config)


def login(page: Page, config: Config, debug: bool) -> None:
    print(f"Opening login page: {config.login_url}")
    page.goto(config.login_url, wait_until="domcontentloaded")
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
            "Use --manual-login --save-auth instead."
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


# --- Home flow (primary) ---


def _fill_input(locator: Locator, value: str) -> None:
    """Fill a React-controlled input and ensure the value sticks."""
    locator.scroll_into_view_if_needed()
    locator.click()
    locator.fill("")
    locator.fill(value)

    try:
        current = locator.input_value(timeout=2_000)
    except Exception:
        current = ""

    if current != value:
        locator.fill("")
        locator.press_sequentially(value, delay=40)

    locator.dispatch_event("input")
    locator.dispatch_event("change")
    locator.dispatch_event("blur")


def submit_sleep_home(page: Page, config: Config, debug: bool) -> None:
    open_healthy_habits(page, config)

    if debug:
        screenshot(page, config.screenshot_dir, "03-healthy-habits")

    try:
        hours_input = first_matching_locator(
            page, config.selector_sleep_hours_input, timeout=15_000
        )
        minutes_input = first_matching_locator(
            page, config.selector_sleep_minutes_input, timeout=15_000
        )
    except RuntimeError:
        print("Sleep fields not found — may already be logged for today. Skipping.")
        return

    sleep_hours, sleep_minutes = config.resolve_sleep_hm()
    print(f"Logging sleep: {sleep_hours}h {sleep_minutes}m")

    _fill_input(hours_input, sleep_hours)
    page.wait_for_timeout(300)
    _fill_input(minutes_input, sleep_minutes)
    page.wait_for_timeout(500)

    if debug:
        screenshot(page, config.screenshot_dir, "04-sleep-filled")

    track = first_matching_locator(page, config.selector_track_sleep)
    track.scroll_into_view_if_needed()
    try:
        expect(track).to_be_enabled(timeout=10_000)
    except AssertionError:
        print("Sleep track button still disabled — trying Enter on minutes field.")
        minutes_input.press("Enter")
        page.wait_for_timeout(1500)

    if track.is_visible():
        track.click()
    page.wait_for_timeout(2000)

    if debug:
        screenshot(page, config.screenshot_dir, "05-sleep-saved")

    print(f"Submitted sleep: {sleep_hours}h {sleep_minutes}m")


def submit_steps_home(page: Page, config: Config, debug: bool) -> None:
    open_healthy_habits(page, config)

    try:
        steps_input = first_matching_locator(page, config.selector_steps_input_home)
    except RuntimeError:
        print("Steps field not found — may already be logged for today. Skipping.")
        return

    steps = config.resolve_steps()
    steps_input.click()
    steps_input.fill(steps)

    if debug:
        screenshot(page, config.screenshot_dir, "06-steps-filled")

    first_matching_locator(page, config.selector_track_steps).click()
    page.wait_for_timeout(2000)

    if debug:
        screenshot(page, config.screenshot_dir, "07-steps-saved")

    print(f"Submitted steps: {steps}")


def submit_mood(page: Page, config: Config, debug: bool) -> None:
    open_healthy_habits(page, config)

    mood = config.resolve_mood()
    spec = f"role:button:{mood}"

    try:
        mood_btn = first_matching_locator(page, spec)
        mood_btn.scroll_into_view_if_needed()
        mood_btn.click()
        page.wait_for_timeout(1500)
        print(f"Submitted mood: {mood}")
        if debug:
            screenshot(page, config.screenshot_dir, "08-mood-saved")
    except RuntimeError:
        print(f"Mood button '{mood}' not found — may already be logged for today. Skipping.")


def _try_click_daily_card_ok(page: Page, config: Config) -> bool:
    for spec in (part.strip() for part in config.selector_daily_card_ok.split(",") if part.strip()):
        try:
            if spec.startswith("#") or spec.startswith("."):
                locator = page.locator(spec).first
            else:
                locator = locator_from_spec(page, spec)
            locator.wait_for(state="visible", timeout=2_000)
            locator.scroll_into_view_if_needed()
            locator.click()
            return True
        except Exception:
            continue
    return False


def _try_next_daily_card(page: Page) -> bool:
    try:
        next_btn = page.get_by_label(re.compile(r"go to next card", re.I))
        next_btn.first.wait_for(state="visible", timeout=2_000)
        next_btn.first.scroll_into_view_if_needed()
        next_btn.first.click()
        return True
    except Exception:
        return False


def submit_daily_cards(page: Page, config: Config, debug: bool) -> None:
    print("Checking daily cards...")
    ensure_home_page(page, config)

    if debug:
        screenshot(page, config.screenshot_dir, "09-daily-cards-start")

    any_action = False
    for _ in range(config.daily_cards_max_iterations):
        clicked_ok = _try_click_daily_card_ok(page, config)
        if clicked_ok:
            any_action = True
            print("Clicked daily card OK")
            page.wait_for_timeout(1500)
            if debug:
                screenshot(page, config.screenshot_dir, "10-daily-card-ok")

        if not _try_next_daily_card(page):
            if not clicked_ok:
                break
            page.wait_for_timeout(1000)
            continue

        page.wait_for_timeout(1000)

    if any_action:
        print("Daily cards completed.")
    else:
        print("No daily card OK button available — skipping.")


def run_home_flow(
    page: Page,
    config: Config,
    debug: bool,
    *,
    steps_only: bool,
    sleep_only: bool,
    skip_mood: bool,
    skip_cards: bool,
) -> None:
    ensure_home_page(page, config)

    if not sleep_only:
        submit_sleep_home(page, config, debug)
    if not steps_only:
        submit_steps_home(page, config, debug)
    if not skip_mood and not steps_only and not sleep_only:
        submit_mood(page, config, debug)
    if not skip_cards and not steps_only and not sleep_only:
        submit_daily_cards(page, config, debug)


# --- Stats flow (secondary / legacy) ---


def submit_steps_stats(page: Page, config: Config, debug: bool) -> None:
    ensure_stats_page(page, config)

    if debug:
        screenshot(page, config.screenshot_dir, "03-stats-page")

    if not open_tracker(page, config.selector_steps_nav, "Steps"):
        return

    if debug:
        screenshot(page, config.screenshot_dir, "03-steps-modal")

    steps = config.resolve_steps()
    steps_input = locator_from_spec(page, config.selector_steps_input)
    steps_input.click()
    steps_input.fill(steps)

    locator_from_spec(page, config.selector_steps_save).click()
    page.wait_for_timeout(2000)
    steps_input.wait_for(state="hidden", timeout=10_000)

    if debug:
        screenshot(page, config.screenshot_dir, "04-steps-saved")

    print(f"Submitted steps: {steps}")


def submit_sleep_stats(page: Page, config: Config, debug: bool) -> None:
    ensure_stats_page(page, config)

    if debug:
        screenshot(page, config.screenshot_dir, "05-stats-page")

    if not open_tracker(page, config.selector_sleep_nav, "Sleep"):
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


def run_stats_flow(
    page: Page,
    config: Config,
    debug: bool,
    *,
    steps_only: bool,
    sleep_only: bool,
) -> None:
    if not sleep_only:
        submit_steps_stats(page, config, debug)
    if not steps_only:
        submit_sleep_stats(page, config, debug)


def run(
    config: Config,
    headed: bool,
    debug: bool,
    skip_validation: bool,
    steps_only: bool,
    sleep_only: bool,
    skip_mood: bool,
    skip_cards: bool,
    manual_login: bool,
    save_auth_flag: bool,
    use_auth: bool,
) -> None:
    if steps_only and sleep_only:
        raise ValueError("Use only one of --steps-only or --sleep-only")

    flow_name = "home" if config.is_home_flow() else "stats"
    print(f"Using {flow_name} flow")

    if not skip_validation:
        config.validate_selectors(
            steps_only=steps_only,
            sleep_only=sleep_only,
            skip_mood=skip_mood,
            skip_cards=skip_cards,
        )

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

            if config.is_home_flow():
                run_home_flow(
                    page,
                    config,
                    debug,
                    steps_only=steps_only,
                    sleep_only=sleep_only,
                    skip_mood=skip_mood,
                    skip_cards=skip_cards,
                )
            else:
                run_stats_flow(
                    page,
                    config,
                    debug,
                    steps_only=steps_only,
                    sleep_only=sleep_only,
                )
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
    if args.flow:
        config = replace(config, flow=args.flow)

    headed = args.headed or args.debug

    try:
        run(
            config,
            headed=headed,
            debug=args.debug,
            skip_validation=args.skip_validation,
            steps_only=args.steps_only,
            sleep_only=args.sleep_only,
            skip_mood=args.skip_mood,
            skip_cards=args.skip_cards,
            manual_login=args.manual_login,
            save_auth_flag=args.save_auth,
            use_auth=args.use_auth,
        )
    except Exception as exc:
        print(f"Failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
