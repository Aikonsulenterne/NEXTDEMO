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
    manual: bool = typer.Option(False, "--manual", help="Ved captcha: vent på at du løser den og trykker Enter."),
    replay: bool = typer.Option(False, "--replay", help="Afspil seneste gode resultat pr. BL fra runs/."),
) -> None:
    """Slå BL op hos rederierne og skriv resultatet i arket."""
    from .run import run

    bls = [b for b in (bl or "").split(",") if b.strip()] or None
    run(load_settings(), limit=limit, bls=bls, skip_checked=skip_checked, manual=manual, replay=replay)


@app.command("reset-sheet")
def reset_sheet() -> None:
    """Tøm output-kolonnerne D–J. Rører aldrig A–C eller Log."""
    try:
        _sheet().reset()
    except SheetError as exc:
        console.print(f"[bold red]{exc}[/]")
        raise typer.Exit(1)
    console.print("[green]Kolonne D–J er tømt.[/]")


if __name__ == "__main__":
    app()
