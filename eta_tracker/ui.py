"""Rich live table for the terminal (and the stage)."""

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

from .compare import FORSINKET, IKKE_FUNDET, IKKE_UNDERSTOETTET, TIDLIGERE, TJEK_MANUELT, UAENDRET

STATUS_STYLE = {
    FORSINKET: "bold white on red3",
    TIDLIGERE: "bold black on green3",
    UAENDRET: "default",
    TJEK_MANUELT: "black on yellow3",
    IKKE_FUNDET: "black on grey70",
    IKKE_UNDERSTOETTET: "black on grey70",
}

console = Console()


def _date(iso: str | None) -> str:
    if not iso:
        return "–"
    y, m, d = iso[:10].split("-")
    return f"{d}-{m}-{y}"


class RunView:
    def __init__(self, title: str, shipments: list):
        self._title = title
        self._rows: dict[str, dict] = {s.bl: {"carrier": s.carrier, "bl": s.bl} for s in shipments}
        self._active: str | None = None
        self._live = Live(self._render(), console=console, refresh_per_second=4)

    def __enter__(self) -> "RunView":
        self._live.__enter__()
        return self

    def __exit__(self, *exc) -> None:
        self._live.__exit__(*exc)

    def working(self, bl: str, text: str = "Slår op …") -> None:
        self._active = bl
        self._rows[bl]["working"] = text
        self._refresh()

    def done(self, record: dict) -> None:
        self._rows[record["bl"]] = {**record, "working": None}
        self._active = None
        self._refresh()

    def ask(self, prompt: str) -> str:
        """Pause the live table to read input from the keyboard."""
        self._live.stop()
        try:
            return console.input(prompt)
        finally:
            self._live.start()

    def _refresh(self) -> None:
        self._live.update(self._render())

    def _render(self) -> Table:
        table = Table(title=self._title, title_style="bold", expand=True)
        for name, kw in (
            ("Rederi", {"no_wrap": True}), ("BL", {"no_wrap": True}), ("Current ETA", {"no_wrap": True}),
            ("Ny ETA", {"no_wrap": True}), ("Forskel", {"justify": "right", "no_wrap": True}),
            ("Status", {"no_wrap": True}), ("Note", {"ratio": 1, "min_width": 20, "overflow": "fold"}),
        ):
            table.add_column(name, **kw)
        for row in self._rows.values():
            status = row.get("status")
            if row.get("working"):
                status_cell = Text(row["working"], style="bold cyan")
            elif status:
                status_cell = Text(f" {status} ", style=STATUS_STYLE.get(status, "default"))
            else:
                status_cell = Text("")
            diff = row.get("diff_days")
            table.add_row(
                row.get("carrier", ""),
                Text(row["bl"], style="bold" if row["bl"] == self._active else ""),
                _date(row.get("current_eta")) if status else "",
                _date(row.get("new_eta")) if status else "",
                (f"{diff:+d}" if diff else "0") if diff is not None else "",
                status_cell,
                row.get("note") or "",
            )
        return table


def summary(records: list[dict]) -> None:
    counts: dict[str, int] = {}
    for r in records:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    parts = [Text(f" {s}: {n} ", style=STATUS_STYLE.get(s, "default")) for s, n in counts.items()]
    console.print()
    console.print(Text("Resultat: ").append_text(Text("  ").join(parts)) if parts else "Ingen BL blev slået op.")
