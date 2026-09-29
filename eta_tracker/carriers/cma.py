"""CMA CGM. URLs and flow: docs/CARRIERS.md. Verify in the phase 0 spike."""

import re
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError

from ..browser import Browser, accept_cookies, capture, fill_search, wait_for_result
from .base import PageCapture

SEARCH_URL = "https://www.cma-cgm.com/ebusiness/tracking/search?SearchBy=BL&Reference={bl}"
TRACKING_URL = "https://www.cma-cgm.com/ebusiness/tracking"
DONE = re.compile(r"\b(ETA|estimated time of arrival|arrival|POD|no result|not found|no data)\b", re.IGNORECASE)
SEARCH_FIELD = re.compile(r"(reference|container|booking|bill of lading|\bBL\b)", re.IGNORECASE)


class CmaCarrier:
    code = "CMA"
    name = "CMA CGM"

    def lookup(self, browser: Browser, bl: str, run_dir: Path) -> PageCapture:
        page = browser.page
        timeout = browser.timeout_ms
        try:
            page.goto(SEARCH_URL.format(bl=bl), wait_until="domcontentloaded")
            accept_cookies(page)
            found = wait_for_result(page, bl, timeout, DONE)
            if not found:
                # Fallback: the search form on the tracking page.
                page.goto(TRACKING_URL, wait_until="domcontentloaded")
                accept_cookies(page)
                if fill_search(page, bl, SEARCH_FIELD):
                    found = wait_for_result(page, bl, timeout, DONE)
        except PlaywrightError:
            found = False
        return capture(page, bl, run_dir, timed_out=not found)
