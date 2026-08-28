import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    email: str
    password: str
    daily_steps: str
    sleep_hours: str
    sleep_minutes: str
    login_url: str
    headless: bool
    selector_email: str
    selector_password: str
    selector_sign_in: str
    steps_page_url: str
    sleep_page_url: str
    selector_steps_input: str
    selector_steps_save: str
    selector_sleep_hours_input: str
    selector_sleep_minutes_input: str
    selector_sleep_save: str
    selector_steps_nav: str
    selector_sleep_nav: str
    screenshot_dir: Path

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            email=_require("PERSONIFY_EMAIL"),
            password=_require("PERSONIFY_PASSWORD"),
            daily_steps=_optional("DAILY_STEPS", "8000"),
            sleep_hours=_optional("SLEEP_HOURS", "7"),
            sleep_minutes=_optional("SLEEP_MINUTES", "30"),
            login_url=_optional("PERSONIFY_LOGIN_URL", "https://login.personifyhealth.com"),
            headless=_bool("HEADLESS", default=True),
            selector_email=_optional(
                "SELECTOR_EMAIL",
                'input[name="username"], input[type="email"], #username',
            ),
            selector_password=_optional(
                "SELECTOR_PASSWORD",
                'input[name="password"], input[type="password"], #password',
            ),
            selector_sign_in=_optional(
                "SELECTOR_SIGN_IN",
                'button[type="submit"], button:has-text("Sign In")',
            ),
            steps_page_url=_optional("STEPS_PAGE_URL"),
            sleep_page_url=_optional("SLEEP_PAGE_URL"),
            selector_steps_input=_optional("SELECTOR_STEPS_INPUT"),
            selector_steps_save=_optional("SELECTOR_STEPS_SAVE"),
            selector_sleep_hours_input=_optional("SELECTOR_SLEEP_HOURS_INPUT"),
            selector_sleep_minutes_input=_optional("SELECTOR_SLEEP_MINUTES_INPUT"),
            selector_sleep_save=_optional("SELECTOR_SLEEP_SAVE"),
            selector_steps_nav=_optional("SELECTOR_STEPS_NAV"),
            selector_sleep_nav=_optional("SELECTOR_SLEEP_NAV"),
            screenshot_dir=Path(__file__).parent / "screenshots",
        )

    def validate_selectors(self) -> None:
        missing = []
        if not self.selector_steps_input:
            missing.append("SELECTOR_STEPS_INPUT")
        if not self.selector_steps_save:
            missing.append("SELECTOR_STEPS_SAVE")
        if not self.selector_sleep_hours_input and not self.selector_sleep_minutes_input:
            missing.append("SELECTOR_SLEEP_HOURS_INPUT or SELECTOR_SLEEP_MINUTES_INPUT")
        if not self.selector_sleep_save:
            missing.append("SELECTOR_SLEEP_SAVE")

        if missing:
            print(
                "Missing selector configuration. Run `playwright codegen` and copy "
                "selectors into .env:\n  - " + "\n  - ".join(missing),
                file=sys.stderr,
            )
            sys.exit(1)
