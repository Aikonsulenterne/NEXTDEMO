# Arkitektur

## Flow

```
┌──────────────┐   1. læs rækker    ┌───────────────┐
│ Google Sheet │ ─────────────────► │   run.py      │
│  "Shipments" │ ◄───────────────── │ (orchestrator)│
└──────────────┘   6. skriv tilbage └──────┬────────┘
       ▲                                   │ for hvert BL
       │ 7. append                         ▼
┌──────┴───────┐               ┌────────────────────────┐
│  fane "Log"  │               │ 2. carriers/<rederi>.py│  Playwright: åbn tracking-side,
└──────────────┘               │    → sidetekst + png   │  vent på resultat, hent tekst
                               └──────────┬─────────────┘
                                          ▼
                               ┌────────────────────────┐
                               │ 3. extract.py          │  Claude: tekst → {eta, vessel, …}
                               └──────────┬─────────────┘
                                          ▼
                               ┌────────────────────────┐
                               │ 4. compare.py          │  gammel vs ny → diff + status
                               └──────────┬─────────────┘
                                          ▼
                               5. gem i runs/<ts>/ (til replay + bevis)
```

## Mappestruktur

```
eta-tracker-poc/
├── CLAUDE.md
├── README.md
├── .env.example
├── requirements.txt
├── data/
│   └── seed_bl_list.csv          # de 25 BL-numre fra kundens Excel (renset)
├── docs/
├── eta_tracker/
│   ├── __main__.py               # Typer CLI: setup-sheet, run, reset-sheet
│   ├── config.py                 # læser .env
│   ├── sheet.py                  # gspread: læs rækker, skriv resultater, formatering, log
│   ├── browser.py                # Playwright persistent context, fælles helpers
│   ├── carriers/
│   │   ├── base.py               # interface: lookup(bl) -> PageCapture(text, screenshot_path, url, blocked)
│   │   ├── cma.py
│   │   └── msc.py
│   ├── extract.py                # Claude-kald + Pydantic-model
│   ├── compare.py                # ren funktion: (old_eta, new_eta, threshold) -> (diff_days, status)
│   ├── replay.py                 # indlæs seneste gode resultat pr. BL fra runs/*/results.json
│   ├── run.py                    # orkestrering: vælg BL, slå op, sammenlign, skriv
│   └── ui.py                     # Rich live-tabel
├── tests/
│   ├── test_compare.py           # status-regler og datoparsing
│   └── test_run_helpers.py       # BL-udvælgelse, replay, skrivning via BL
├── runs/                          # gitignored – output pr. kørsel
├── secrets/                       # gitignored – service-account.json
└── .browser-profile/              # gitignored – Playwright-profil (cookies)
```

## Nøglebeslutninger

- **Carrier-moduler er dumme**: de henter kun sidetekst + screenshot. Al fortolkning sker i `extract.py`.
  Nyt rederi = ny fil på ~40 linjer.
- **`compare.py` er en ren funktion** uden I/O, så den kan testes fuldt.
- **Blokering opdages i carrier-modulet** (keyword-tjek på sideteksten), før Claude kaldes. Claude rapporterer desuden
  `page_state`, så "BL findes ikke" og "fejlside" kan skelnes fra "ETA ikke fundet".
- **Skriv til arket efter hvert BL** (ikke til sidst). Så ser publikum arket blive opdateret række for række.
- **Find rækken via BL lige før skrivning**, ikke via rækkenummer fra starten. Så gør det ikke noget, hvis nogen
  sorterer eller filtrerer arket, mens kørslen står på.
- **Batch-skrivning** med `worksheet.batch_update` pr. række (én API-kald) for at undgå Sheets' rate limits (60 skrivninger/min).

## CLI

| Kommando | Hvad |
|---|---|
| `setup-sheet` | Opretter faner, headers, formatering og importerer `data/seed_bl_list.csv` |
| `run` | Slår alle BL op |
| `run --limit N` | De første N rækker (hurtig test) |
| `run --bl COP0305302,MEDUKC776011` | Kun de nævnte BL, i den rækkefølge. Bruges live i demoen |
| `run --skip-checked` | Springer rækker med udfyldt `Sidst tjekket` over. Bruges til at forkøre resten før demoen |
| `run --manual` | Ved captcha: pause og vent på, at brugeren løser den i browseren og trykker Enter. Til spike og opvarmning af profilen, ikke til scenen |
| `run --replay` | Afspiller seneste gode resultat pr. BL (se nedenfor). Kan kombineres med `--bl` |
| `reset-sheet` | Tømmer `Shipments!D2:J`. Rører aldrig A–C og aldrig `Log` |

## Replay

- Hver kørsel gemmer `runs/<timestamp>/results.json` (ét element pr. BL: rå Claude-svar, status, diff, sti til screenshot).
- Replay vælger **pr. BL** det nyeste resultat i `runs/`, hvor status ikke er `Ikke fundet`.
  Så virker det, selvom seneste kørsel kun dækkede nogle af BL'erne (fx morgenens forkørsel). BL uden godt resultat springes over.
- Replay skriver til `Shipments` med samme animation og pauser (kortere, 1–2 sek.), men:
  - `Sidst tjekket` = det **oprindelige** opslagstidspunkt, ikke nu
  - `Note` får præfikset "Afspillet: "
  - Der skrives **ikke** til `Log` (det er ikke et nyt opslag)
- Replay kræver kun adgang til Google Sheets, ikke til rederierne eller Claude.

## Fejlhåndtering

| Situation | Handling | Status i ark |
|---|---|---|
| Siden loader ikke / timeout (30 s) | 1 retry, så videre | `Ikke fundet` + note "Timeout" |
| Captcha / "access denied" (keyword-tjek i carrier-modulet) | Stop dette BL, fortsæt med næste. Med `--manual`: vent på Enter og prøv siden igen | `Ikke fundet` + note "Blokeret af rederiets side" (hvis stadig blokeret) |
| BL findes ikke hos rederiet (`page_state: not_found`) | – | `Ikke fundet` + note fra siden |
| Claude returnerer `eta: null` eller `confidence: low` | – | `Tjek manuelt` |
| `Current ETA` tom eller ikke en dato | Slå op alligevel, skriv `Ny ETA` | `Tjek manuelt` + note "Mangler gyldig Current ETA" |
| Claude-svar består ikke Pydantic-validering | 1 retry, så videre | `Tjek manuelt` + note "Uventet svar fra AI" |
| Ukendt carrier-kode i arket | Spring over | `Ikke understøttet` |
| Google Sheets-fejl | Retry med backoff (3 forsøg), ellers tydelig fejl og kørslen fortsætter kun i terminalen (Rich-tabellen). Kan arket ikke åbnes ved start, læses BL-listen fra `data/seed_bl_list.csv` | – |
