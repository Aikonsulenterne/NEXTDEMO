# Arkitektur

## Flow

```
┌──────────────┐   1. læs rækker    ┌───────────────┐
│ Google Sheet │ ─────────────────► │   run.py      │
│  "Shipments" │ ◄───────────────── │ (orchestrator)│
└──────────────┘   5. skriv tilbage └──────┬────────┘
       ▲             (række for række)     │ én kørsel pr. rederi, alle BL
       │ 6. append                         ▼
┌──────┴───────┐               ┌────────────────────────┐
│  fane "Log"  │               │ 2. apify.py            │  Apify-actor → rederiets tracking-data (JSON)
└──────────────┘               └──────────┬─────────────┘
                                          ▼ for hvert BL
                               ┌────────────────────────┐
                               │ 3. carriers.py         │  JSON → ETA ved POD (ren kode)
                               │    (ellers extract.py) │  uventet form → Claude læser JSON'en
                               └──────────┬─────────────┘
                                          ▼
                               ┌────────────────────────┐
                               │ 4. compare.py          │  gammel vs ny → diff + status
                               └──────────┬─────────────┘
                                          ▼
                               gem rå-JSON + results.json i runs/<ts>/ (til replay + bevis)
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
│   ├── apify.py                  # kør Apify-actor for en liste BL → {BL: rå data}
│   ├── carriers.py               # parse_cma / parse_msc: rå data → Extraction (ETA, skib, POD)
│   ├── extract.py                # Claude-fallback + Pydantic-model (Extraction)
│   ├── compare.py                # ren funktion: (old_eta, new_eta, threshold) -> (diff_days, status)
│   ├── replay.py                 # seneste gode resultat pr. BL fra runs/*/results.json
│   ├── run.py                    # orkestrering: vælg BL, hent, læs, sammenlign, skriv
│   └── ui.py                     # Rich live-tabel
├── tests/
│   ├── fixtures/                 # rigtige Apify-svar (trimmet) for et CMA- og et MSC-BL
│   ├── test_compare.py           # status-regler og datoparsing
│   ├── test_carriers.py          # parsere på rigtige data + Apify-klient
│   ├── test_run_helpers.py       # BL-udvælgelse, replay, skrivning via BL
│   └── test_run_live.py          # hel kørsel med falsk Apify, uden ark
├── runs/                          # gitignored – output pr. kørsel
└── secrets/                       # gitignored – service-account.json
```

## Nøglebeslutninger

- **Data hentes i batch:** én Apify-kørsel pr. rederi med alle BL (ca. 5–10 sek.), ikke ét opslag ad gangen.
- **Kode læser data, Claude er fallback.** De kendte felter læses deterministisk i `carriers.py` (testbart, gratis, hurtigt).
  Har dataene en uventet form, læser Claude rå-JSON'en og svarer i samme `Extraction`-schema.
- **`compare.py` er en ren funktion** uden I/O, så den kan testes fuldt.
- **Skriv til arket efter hvert BL** med en lille pause (`REVEAL_DELAY_SECONDS`), så publikum ser arket fyldes række for række.
- **Find rækken via BL lige før skrivning**, ikke via rækkenummer fra starten. Så gør det ikke noget, hvis nogen
  sorterer eller filtrerer arket, mens kørslen står på.
- **Batch-skrivning** med én `update` pr. række for at holde os under Sheets' rate limits (60 skrivninger/min).

## CLI

| Kommando | Hvad |
|---|---|
| `setup-sheet` | Opretter faner, headers, formatering og importerer `data/seed_bl_list.csv` |
| `run` | Slår alle BL op |
| `run --limit N` | De første N rækker (hurtig test) |
| `run --bl COP0305302,MEDUKC776011` | Kun de nævnte BL, i den rækkefølge |
| `run --skip-checked` | Springer rækker med udfyldt `Sidst tjekket` over |
| `run --replay` | Afspiller seneste gode resultat pr. BL (se nedenfor). Kan kombineres med `--bl` |
| `reset-sheet` | Tømmer `Shipments!D2:J`. Rører aldrig A–C og aldrig `Log` |

## Replay

- Hver kørsel gemmer `runs/<timestamp>/results.json` (ét element pr. BL: status, diff, sti til rå-JSON) og `<BL>.json` (rå data).
- Replay vælger **pr. BL** det nyeste resultat i `runs/`, hvor status ikke er `Ikke fundet`.
- Replay skriver til `Shipments` med samme animation, men:
  - `Sidst tjekket` = det **oprindelige** opslagstidspunkt, ikke nu
  - `Note` får præfikset "Afspillet: "
  - Der skrives **ikke** til `Log` (det er ikke et nyt opslag)
- Replay kræver kun adgang til Google Sheets, ikke til Apify eller Claude.

## Fejlhåndtering

| Situation | Handling | Status i ark |
|---|---|---|
| Apify nede, timeout eller forkert nøgle | Alle BL for det rederi markeres, kørslen fortsætter | `Ikke fundet` + note fra Apify-fejlen |
| BL mangler i Apify-svaret eller har ingen data | – | `Ikke fundet` + note |
| Data har uventet form | Claude læser rå-JSON'en (kræver `ANTHROPIC_API_KEY`) | Som Claude svarer; ellers `Tjek manuelt` |
| Claude returnerer `eta: null` eller `confidence: low` | – | `Tjek manuelt` |
| `Current ETA` tom eller ikke en dato | Slå op alligevel, skriv `Ny ETA` | `Tjek manuelt` + note "Mangler gyldig Current ETA" |
| Claude-svar består ikke Pydantic-validering | 1 retry, så videre | `Tjek manuelt` + note "Uventet svar fra AI" |
| Ukendt carrier-kode i arket | Spring over | `Ikke understøttet` |
| Google Sheets-fejl | Retry med backoff (3 forsøg), ellers tydelig fejl og kørslen fortsætter kun i terminalen. Kan arket ikke åbnes ved start, læses BL-listen fra `data/seed_bl_list.csv` | – |
