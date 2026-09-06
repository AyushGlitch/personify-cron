"""Resolve Playwright locators from .env selector strings."""

from __future__ import annotations

from playwright.sync_api import Locator, Page


def locator_from_spec(page: Page, spec: str) -> Locator:
    """
    Parse a selector spec into a Playwright locator.

    Supported prefixes (match codegen output):
      placeholder:Enter your email or username  -> get_by_placeholder(...)
      label:Password *                          -> get_by_label(...)
      role:button:Sign In                       -> get_by_role("button", name="Sign In")
      text:Submit                               -> get_by_text(...)

    Anything else is passed to page.locator() (CSS, role=button[name="Sign In"], etc.).
    """
    spec = spec.strip()
    if not spec:
        raise ValueError("Empty selector spec")

    if spec.startswith("placeholder:"):
        return page.get_by_placeholder(spec.removeprefix("placeholder:"))

    if spec.startswith("label!:"):
        return page.get_by_label(spec.removeprefix("label!:"), exact=True)

    if spec.startswith("label:"):
        return page.get_by_label(spec.removeprefix("label:"), exact=False)

    if spec.startswith("role:"):
        _, role, name = spec.split(":", 2)
        return page.get_by_role(role, name=name)

    if spec.startswith("text:"):
        return page.get_by_text(spec.removeprefix("text:"))

    return page.locator(spec).first


def first_matching_locator(page: Page, selectors: str) -> Locator:
    """Try comma-separated selector specs; return the first visible match."""
    parts = [part.strip() for part in selectors.split(",") if part.strip()]
    last_error: Exception | None = None

    for part in parts:
        try:
            locator = locator_from_spec(page, part)
            locator.wait_for(state="visible", timeout=5_000)
            return locator
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"No element matched selectors: {selectors}") from last_error
