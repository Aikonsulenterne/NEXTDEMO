"""Replay: newest good result per BL from runs/<timestamp>/results.json (docs/ARCHITECTURE.md, "Replay")."""

import json
from pathlib import Path

from .compare import IKKE_FUNDET


def save_results(run_dir: Path, run_ts: str, records: list[dict]) -> None:
    """Rewritten after every BL, so a crash still leaves a usable file."""
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {"run": run_ts, "results": records}
    tmp = run_dir / "results.json.tmp"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(run_dir / "results.json")


def load_best(runs_dir: Path) -> dict[str, dict]:
    """BL (upper case) -> newest record whose status is not 'Ikke fundet'."""
    best: dict[str, dict] = {}
    if not runs_dir.exists():
        return best
    for results_file in sorted(runs_dir.glob("*/results.json"), reverse=True):
        try:
            data = json.loads(results_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for record in data.get("results", []):
            key = str(record.get("bl", "")).strip().upper()
            if key and key not in best and record.get("status") != IKKE_FUNDET:
                best[key] = record
    return best
