import os
import random
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
    sleep_hours_min: str
    sleep_hours_max: str
    login_url: str
    headless: bool
    selector_email: str
    selector_continue: str
    selector_password: str
    selector_sign_in: str
    steps_page_url: str
    stats_page_url: str
    sleep_page_url: str
    selector_steps_input: str
    selector_steps_save: str
    selector_sleep_input: str
    selector_sleep_save: str
    selector_steps_nav: str
    selector_sleep_nav: str
    screenshot_dir: Path
    auth_file: Path

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            email=_require("PERSONIFY_EMAIL"),
            password=_require("PERSONIFY_PASSWORD"),
            daily_steps=_optional("DAILY_STEPS", "8000"),
            sleep_hours=_optional("SLEEP_HOURS", "7.5"),
            sleep_hours_min=_optional("SLEEP_HOURS_MIN", "7"),
            sleep_hours_max=_optional("SLEEP_HOURS_MAX", "8"),
            login_url=_optional("PERSONIFY_LOGIN_URL", "https://app.personifyhealth.com"),
            headless=_bool("HEADLESS", default=True),
            selector_email=_optional(
                "SELECTOR_EMAIL",
                "placeholder:Enter your email or username",
            ),
            selector_continue=_optional("SELECTOR_CONTINUE", "role:button:Continue"),
            selector_password=_optional(
                "SELECTOR_PASSWORD",
                "placeholder:Enter your password, label:Password *",
            ),
            selector_sign_in=_optional(
                "SELECTOR_SIGN_IN",
                "role:button:Sign In",
            ),
            steps_page_url=_optional("STEPS_PAGE_URL"),
            stats_page_url=_optional(
                "STATS_PAGE_URL",
                "https://app.personifyhealth.com/#/stats-page",
            ),
            sleep_page_url=_optional("SLEEP_PAGE_URL"),
            selector_steps_input=_optional(
                "SELECTOR_STEPS_INPUT",
                "placeholder:Enter number of steps",
            ),
            selector_steps_save=_optional("SELECTOR_STEPS_SAVE", "role:button:Save"),
            selector_sleep_input=_optional(
                "SELECTOR_SLEEP_INPUT",
                "placeholder:Enter hours of sleep",
            ),
            selector_sleep_save=_optional("SELECTOR_SLEEP_SAVE", "role:button:Save"),
            selector_steps_nav=_optional(
                "SELECTOR_STEPS_NAV",
                "label:Track Steps, role:link:Track Steps, text:Track Steps",
            ),
            selector_sleep_nav=_optional(
                "SELECTOR_SLEEP_NAV",
                "label:Track Sleep, role:link:Track Sleep",
            ),
            screenshot_dir=Path(__file__).parent / "screenshots",
            auth_file=Path(__file__).parent / _optional("AUTH_FILE", "auth.json"),
        )

    def validate_selectors(self, steps_only: bool = False, sleep_only: bool = False) -> None:
        missing = []
        if not sleep_only:
            if not self.selector_steps_nav:
                missing.append("SELECTOR_STEPS_NAV")
            if not self.selector_steps_input:
                missing.append("SELECTOR_STEPS_INPUT")
            if not self.selector_steps_save:
                missing.append("SELECTOR_STEPS_SAVE")
        if not steps_only:
            if not self.selector_sleep_nav:
                missing.append("SELECTOR_SLEEP_NAV")
            if not self.selector_sleep_input:
                missing.append("SELECTOR_SLEEP_INPUT")
            if not self.selector_sleep_save:
                missing.append("SELECTOR_SLEEP_SAVE")

        if missing:
            print(
                "Missing selector configuration. Run `playwright codegen` and copy "
                "selectors into .env:\n  - " + "\n  - ".join(missing),
                file=sys.stderr,
            )
            sys.exit(1)

    def resolve_sleep_hours(self) -> str:
        """Return sleep hours to log — random in [min, max] when both are set."""
        if self.sleep_hours_min and self.sleep_hours_max:
            low = float(self.sleep_hours_min)
            high = float(self.sleep_hours_max)
            value = random.uniform(low, high)
            return f"{value:.1f}".rstrip("0").rstrip(".")
        return self.sleep_hours
