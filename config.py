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
    flow: str
    daily_steps: str
    steps_min: str
    steps_max: str
    sleep_hours: str
    sleep_hours_min: str
    sleep_hours_max: str
    moods: tuple[str, ...]
    login_url: str
    headless: bool
    selector_email: str
    selector_continue: str
    selector_password: str
    selector_sign_in: str
    home_page_url: str
    stats_page_url: str
    selector_healthy_habits: str
    selector_sleep_hours_input: str
    selector_sleep_minutes_input: str
    selector_track_sleep: str
    selector_steps_input_home: str
    selector_track_steps: str
    selector_daily_card_ok: str
    daily_cards_max_iterations: int
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
        moods_raw = _optional(
            "MOODS",
            "angry,sad,worried,unsure,happy,excited",
        )
        moods = tuple(m.strip() for m in moods_raw.split(",") if m.strip())

        return cls(
            email=_require("PERSONIFY_EMAIL"),
            password=_require("PERSONIFY_PASSWORD"),
            flow=_optional("FLOW", "home").lower(),
            daily_steps=_optional("DAILY_STEPS", "10000"),
            steps_min=_optional("STEPS_MIN", "7001"),
            steps_max=_optional("STEPS_MAX", "21000"),
            sleep_hours=_optional("SLEEP_HOURS", "8"),
            sleep_hours_min=_optional("SLEEP_HOURS_MIN", "7"),
            sleep_hours_max=_optional("SLEEP_HOURS_MAX", "10"),
            moods=moods,
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
            home_page_url=_optional(
                "HOME_PAGE_URL",
                "https://app.personifyhealth.com/#/home",
            ),
            stats_page_url=_optional(
                "STATS_PAGE_URL",
                "https://app.personifyhealth.com/#/stats-page",
            ),
            selector_healthy_habits=_optional(
                "SELECTOR_HEALTHY_HABITS",
                "label:Healthy Habits",
            ),
            selector_sleep_hours_input=_optional(
                "SELECTOR_SLEEP_HOURS_INPUT",
                "label!:Enter hours of sleep, label:Hours, placeholder:hours",
            ),
            selector_sleep_minutes_input=_optional(
                "SELECTOR_SLEEP_MINUTES_INPUT",
                "label!:Enter minutes of sleep, label:Minutes, placeholder:minutes",
            ),
            selector_track_sleep=_optional(
                "SELECTOR_TRACK_SLEEP",
                "#track-sleep-cmx, [id*='track-sleep']",
            ),
            selector_steps_input_home=_optional(
                "SELECTOR_STEPS_INPUT_HOME",
                "placeholder:Enter number of steps",
            ),
            selector_track_steps=_optional(
                "SELECTOR_TRACK_STEPS",
                "#track-steps-cmx",
            ),
            selector_daily_card_ok=_optional(
                "SELECTOR_DAILY_CARD_OK",
                "#daily-card-actions, role:button:OK",
            ),
            daily_cards_max_iterations=int(_optional("DAILY_CARDS_MAX_ITERATIONS", "8")),
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

    def is_home_flow(self) -> bool:
        return self.flow != "stats"

    def validate_selectors(
        self,
        *,
        steps_only: bool = False,
        sleep_only: bool = False,
        skip_mood: bool = False,
        skip_cards: bool = False,
    ) -> None:
        if self.is_home_flow():
            self._validate_home_selectors(
                steps_only=steps_only,
                sleep_only=sleep_only,
                skip_mood=skip_mood,
                skip_cards=skip_cards,
            )
        else:
            self._validate_stats_selectors(steps_only=steps_only, sleep_only=sleep_only)

    def _validate_home_selectors(
        self,
        *,
        steps_only: bool,
        sleep_only: bool,
        skip_mood: bool,
        skip_cards: bool,
    ) -> None:
        missing = []
        if not self.selector_healthy_habits:
            missing.append("SELECTOR_HEALTHY_HABITS")
        if not sleep_only:
            if not self.selector_sleep_hours_input:
                missing.append("SELECTOR_SLEEP_HOURS_INPUT")
            if not self.selector_sleep_minutes_input:
                missing.append("SELECTOR_SLEEP_MINUTES_INPUT")
            if not self.selector_track_sleep:
                missing.append("SELECTOR_TRACK_SLEEP")
        if not steps_only:
            if not self.selector_steps_input_home:
                missing.append("SELECTOR_STEPS_INPUT_HOME")
            if not self.selector_track_steps:
                missing.append("SELECTOR_TRACK_STEPS")
        if not skip_mood and not self.moods:
            missing.append("MOODS")
        if not skip_cards and not self.selector_daily_card_ok:
            missing.append("SELECTOR_DAILY_CARD_OK")

        if missing:
            print(
                "Missing home-flow selector configuration:\n  - " + "\n  - ".join(missing),
                file=sys.stderr,
            )
            sys.exit(1)

    def _validate_stats_selectors(self, *, steps_only: bool, sleep_only: bool) -> None:
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
                "Missing stats-flow selector configuration:\n  - " + "\n  - ".join(missing),
                file=sys.stderr,
            )
            sys.exit(1)

    def resolve_steps(self) -> str:
        """Return steps to log — random in [min, max] when both are set."""
        if self.steps_min and self.steps_max:
            low = int(self.steps_min)
            high = int(self.steps_max)
            return str(random.randint(low, high))
        return self.daily_steps

    def resolve_sleep_hours(self) -> str:
        """Return sleep hours for stats flow (single field)."""
        if self.sleep_hours_min and self.sleep_hours_max:
            low = float(self.sleep_hours_min)
            high = float(self.sleep_hours_max)
            value = random.uniform(low, high)
            return f"{value:.1f}".rstrip("0").rstrip(".")
        return self.sleep_hours

    def resolve_sleep_hm(self) -> tuple[str, str]:
        """Return (hours, minutes) for home flow — random total in [min, max]."""
        if self.sleep_hours_min and self.sleep_hours_max:
            total_hours = random.uniform(
                float(self.sleep_hours_min),
                float(self.sleep_hours_max),
            )
        else:
            total_hours = float(self.sleep_hours)

        hours = int(total_hours)
        minutes = int(round((total_hours - hours) * 60))
        if minutes == 60:
            hours += 1
            minutes = 0
        return str(hours), str(minutes)

    def resolve_mood(self) -> str:
        return random.choice(self.moods)

    def post_login_url(self) -> str:
        return self.home_page_url if self.is_home_flow() else self.stats_page_url
