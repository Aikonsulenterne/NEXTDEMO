"""Playwright persistent context (headed, real Chrome when available) and shared page helpers."""

import re
import time
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright

# Lowercase snippets that mean the carrier blocked us. Tune after the spike (docs/CARRIERS.md, "Blokering").
BLOCK_MARKERS = (
    "captcha",
    "access denied",
    "verify you are human",
    "verifying you are human",
    "unusual traffic",
    "request unsuccessful",
    "are you a robot",
    "please enable js and disable any ad blocker",
)

# Cookie banners: OneTrust button id first, then common button texts.
COOKIE_SELECTORS = ("#onetrust-accept-btn-handler",)
COOKIE_BUTTON_TEXT = re.compile(
    r"^\s*(accept all( cookies)?|accept( cookies)?|allow all( cookies)?|i agree|agree|tillad alle|accepter( alle)?)\s*$",
    re.IGNORECASE,
)


def is_blocked(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in BLOCK_MARKERS)


class Browser:
    def __init__(self, profile_dir: Path, headless: bool, timeout_seconds: int):
        self._profile_dir = profile_dir
        self._headless = headless
        self.timeout_ms = timeout_seconds * 1000
        self._playwright = None
        self._context = None
        self.channel = "chromium"

    def __enter__(self) -> "Browser":
        self._profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        options = dict(
            user_data_dir=str(self._profile_dir),
            headless=self._headless,
            viewport={"width": 1280, "height": 900},
            locale="en-GB",
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            # Installed Chrome looks less like a bot than Playwright's bundled Chromium.
            self._context = self._playwright.chromium.launch_persistent_context(channel="chrome", **options)
            self.channel = "chrome"
        except PlaywrightError:
            self._context = self._playwright.chromium.launch_persistent_context(**options)
        self._context.set_default_timeout(self.timeout_ms)
        return self

    def __exit__(self, *exc) -> None:
        try:
            if self._context:
                self._context.close()
        finally:
            if self._playwright:
                self._playwright.stop()

    @property
    def page(self) -> Page:
        pages = self._context.pages
        return pages[0] if pages else self._context.new_page()


def accept_cookies(page: Page) -> None:
    """Click a cookie banner if one is visible. The persistent profile remembers it afterwards."""
    for selector in COOKIE_SELECTORS:
        try:
            button = page.locator(selector)
            if button.is_visible(timeout=1500):
                button.click(timeout=3000)
                return
        except PlaywrightError:
            pass
    try:
        button = page.get_by_role("button", name=COOKIE_BUTTON_TEXT).first
        if button.is_visible(timeout=1500):
            button.click(timeout=3000)
    except PlaywrightError:
        pass


def body_text(page: Page) -> str:
    try:
        return page.inner_text("body", timeout=5000)
    except PlaywrightError:
        return ""


def wait_for_result(page: Page, bl: str, timeout_ms: int, done: re.Pattern) -> bool:
    """Poll the visible text until the result for this BL (or a clear 'not found') shows. False on timeout."""
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        text = body_text(page)
        if is_blocked(text):
            return True
        if bl.upper() in text.upper() and done.search(text):
            page.wait_for_timeout(1500)  # let late widgets finish rendering
            return True
        page.wait_for_timeout(1000)
    return False


def capture(page: Page, bl: str, run_dir: Path, *, timed_out: bool) -> "PageCapture":  # noqa: F821
    from .carriers.base import PageCapture

    run_dir.mkdir(parents=True, exist_ok=True)
    screenshot = run_dir / f"{bl}.png"
    try:
        page.screenshot(path=str(screenshot), full_page=True)
    except PlaywrightError:
        screenshot = None
    text = body_text(page)
    (run_dir / f"{bl}.txt").write_text(text, encoding="utf-8")
    blocked = is_blocked(text)
    error = "Blokeret af rederiets side" if blocked else ("Timeout" if timed_out else None)
    return PageCapture(text=text, screenshot_path=screenshot, url=page.url, blocked=blocked, error=error)


def fill_search(page: Page, bl: str, placeholder: re.Pattern) -> bool:
    """Type the BL into the first visible search field matching the placeholder/label, then press Enter."""
    candidates = (
        page.get_by_placeholder(placeholder),
        page.get_by_label(placeholder),
        page.locator("input[type='search'], input[type='text']"),
    )
    for locator in candidates:
        try:
            field = locator.first
            if field.is_visible(timeout=2000):
                field.fill(bl)
                field.press("Enter")
                return True
        except PlaywrightError:
            continue
    return False
