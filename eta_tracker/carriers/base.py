"""Carrier interface. Carrier modules only fetch page text + screenshot; extract.py interprets it."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ..browser import Browser


@dataclass
class PageCapture:
    text: str
    screenshot_path: Path | None
    url: str
    blocked: bool = False
    error: str | None = None  # Danish, shown in the sheet's Note ("Timeout", ...)


class Carrier(Protocol):
    code: str
    name: str

    def lookup(self, browser: "Browser", bl: str, run_dir: Path) -> PageCapture: ...
