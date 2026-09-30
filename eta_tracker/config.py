"""Settings loaded from .env (see .env.example)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    claude_model: str
    sheet_id: str
    service_account_file: Path
    tab_shipments: str
    tab_log: str
    delay_threshold_days: int
    apify_token: str
    actor_cma: str
    actor_msc: str
    apify_timeout_seconds: int
    reveal_delay_seconds: float
    runs_dir: Path
    seed_csv: Path


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env")
    return Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        claude_model=os.getenv("CLAUDE_MODEL", "claude-haiku-4-5"),
        sheet_id=os.getenv("GOOGLE_SHEET_ID", ""),
        service_account_file=_path(os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "./secrets/service-account.json")),
        tab_shipments=os.getenv("SHEET_TAB_SHIPMENTS", "Shipments"),
        tab_log=os.getenv("SHEET_TAB_LOG", "Log"),
        delay_threshold_days=_int("DELAY_THRESHOLD_DAYS", 1),
        apify_token=os.getenv("APIFY_TOKEN", ""),
        actor_cma=os.getenv("APIFY_ACTOR_CMA", "muhammetakkurtt/cma-cgm-cargo-tracking-scraper"),
        actor_msc=os.getenv("APIFY_ACTOR_MSC", "muhammetakkurtt/msc-cargo-tracking-scraper"),
        apify_timeout_seconds=_int("APIFY_TIMEOUT_SECONDS", 300),
        reveal_delay_seconds=_float("REVEAL_DELAY_SECONDS", 1.0),
        runs_dir=ROOT / "runs",
        seed_csv=ROOT / "data" / "seed_bl_list.csv",
    )
