"""CLI: python -m eta_tracker setup-sheet | run | reset-sheet"""

from typing import Optional

import typer

from .config import load_settings
from .sheet import Sheet, SheetError, load_seed
from .ui import console

app = typer.Typer(add_completion=False, help="ETA Tracker POC: tjek rederiernes ETA og skriv til Google Sheet.")


def _sheet() -> Sheet:
    s = load_settings()
    try:
        return Sheet(s.service_account_file, s.sheet_id, s.tab_shipments, s.tab_log)
    except SheetError as exc:
        console.print(f"[bold red]{exc}[/]")
        raise typer.Exit(1)


@app.command("setup-sheet")
def setup_sheet() -> None:
    """Opret faner, headers og formatering, og importér seed-data hvis arket er tomt."""
    settings = load_settings()
    try:
        imported = _sheet().setup(load_seed(settings.seed_csv))
    except SheetError as exc:
        console.print(f"[bold red]{exc}[/]")
        raise typer.Exit(1)
    if imported:
        console.print(f"[green]Arket er klar. {imported} BL importeret.[/]")
    else:
        console.print("[green]Arket er klar.[/] Der lå allerede data i A–C, så seed-data blev ikke importeret.")


@app.command("run")
def run_cmd(
    limit: Optional[int] = typer.Option(None, "--limit", help="Kun de første N rækker."),
    bl: Optional[str] = typer.Option(None, "--bl", help="Kun disse BL, kommasepareret, i denne rækkefølge."),
    skip_checked: bool = typer.Option(False, "--skip-checked", help="Spring rækker med 'Sidst tjekket' over."),
    replay: bool = typer.Option(False, "--replay", help="Afspil seneste gode resultat pr. BL fra runs/."),
) -> None:
    """Slå BL op hos rederierne og skriv resultatet i arket."""
    from .run import run

    bls = [b for b in (bl or "").split(",") if b.strip()] or None
    run(load_settings(), limit=limit, bls=bls, skip_checked=skip_checked, replay=replay)


@app.command("reset-sheet")
def reset_sheet() -> None:
    """Tøm output-kolonnerne D–J. Rører aldrig A–C eller Log."""
    try:
        _sheet().reset()
    except SheetError as exc:
        console.print(f"[bold red]{exc}[/]")
        raise typer.Exit(1)
    console.print("[green]Kolonne D–J er tømt.[/]")


@app.command("snapshot")
def snapshot_cmd(
    raw: list[str] = typer.Argument(..., help="Rå Apify-resultater (JSON), fx cma.json msc.json."),
    out: str = typer.Option("dashboard/data.json", "--out", help="Hvor data.json skrives."),
    previous: Optional[str] = typer.Option(None, "--previous", help="Gårsdagens data.json (til historik)."),
    baseline: str = typer.Option("data/seed_bl_list.csv", "--baseline", help="Listen med Current ETA."),
    summary: Optional[str] = typer.Option(None, "--summary", help="Erstat standard-opsummeringen."),
) -> None:
    """Byg dashboardets data.json ud fra rå Apify-data."""
    from pathlib import Path

    from .snapshot import main as build_snapshot

    doc = build_snapshot([Path(r) for r in raw], Path(baseline), Path(previous) if previous else None,
                         Path(out), summary)
    console.print(f"[green]{out}[/] skrevet: {doc['counts']}")


if __name__ == "__main__":
    app()
