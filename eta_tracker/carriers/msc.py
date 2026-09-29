"""MSC. URLs and flow: docs/CARRIERS.md. Verify in the phase 0 spike."""

import re
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from ..browser import Browser, accept_cookies, capture, fill_search, wait_for_result
from .base import PageCapture

TRACKING_URL = "https://www.msc.com/en/track-a-shipment"
DONE = re.compile(r"\b(POD ETA|ETA|estimated time of arrival|port of discharge|no results?|not found)\b", re.IGNORECASE)
SEARCH_FIELD = re.compile(r"(container|bill of lading|booking|\bBL\b|track)", re.IGNORECASE)
DETAILS_BUTTON = re.compile(r"(show|more|view) details", re.IGNORECASE)


class MscCarrier:
    code = "MSC"
    name = "MSC"

    def lookup(self, browser: Browser, bl: str, run_dir: Path) -> PageCapture:
        page = browser.page
        found = False
        try:
            page.goto(TRACKING_URL, wait_until="domcontentloaded")
            accept_cookies(page)
            if fill_search(page, bl, SEARCH_FIELD):
                found = wait_for_result(page, bl, browser.timeout_ms, DONE)
                if found:
                    _expand_details(page)
        except PlaywrightError:
            found = False
        return capture(page, bl, run_dir, timed_out=not found)


def _expand_details(page) -> None:
    try:
        buttons = page.get_by_role("button", name=DETAILS_BUTTON)
        for i in range(min(buttons.count(), 5)):
            buttons.nth(i).click(timeout=3000)
        page.wait_for_timeout(1000)
    except PlaywrightError:
        pass
