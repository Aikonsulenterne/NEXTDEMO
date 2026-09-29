# ETA Tracker – POC

En demo, der viser, at AI kan overtage et kedeligt, manuelt job i shipping:
**at tjekke, om skibe med ens varer er blevet forsinket.**

## Problemet

En container er 6–8 uger undervejs på havet. I den tid rykker den forventede ankomstdato (ETA) sig tit.
I dag sidder en medarbejder og slår hvert fragtbrev (BL-nummer) op manuelt på rederiets hjemmeside
(CMA CGM, MSC, …) for at se, om noget har flyttet sig. Med 25+ forsendelser tager det nemt en time,
og det er dér, man overser den ene forsinkelse, der betyder noget.

## Hvad POC'en gør

```
Google Sheet  ──►  Slå hvert BL op hos rederiet  ──►  AI læser ny ETA  ──►  Sammenlign  ──►  Skriv tilbage + farv
(BL-liste)         (browser, som et menneske)        (fra sidens tekst)    (gammel vs ny)    (rød = forsinket)
```

1. Læser listen af forsendelser fra et **Google Sheet** (Carrier, BL, Current ETA).
2. Åbner rederiets tracking-side for hvert BL-nummer (**CMA CGM** og **MSC**) i en rigtig browser.
3. Lader **Claude** læse sidens indhold og finde den nye ETA. Så er vi ikke afhængige af præcis sidelayout.
4. Sammenligner ny ETA med gammel ETA og regner forskellen ud i dage.
5. Skriver resultatet tilbage i arket: **rød** = forsinket, **grøn** = tidligere, neutral = uændret, **gul** = tjek manuelt, grå = ikke fundet.
6. Logger hver kørsel i en separat fane, så man kan se udviklingen over tid.

## Hvad POC'en IKKE er

- Ikke et produkt. Ingen login, ingen brugere, ingen server. Den kører lokalt fra en terminal.
- Ikke skalerbar scraping. Til produktion skal man bruge rederiernes API'er eller en tracking-aggregator (se [`docs/ROADMAP.md`](docs/ROADMAP.md)).

## Kom i gang (kort)

```bash
# 1. Installér
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 2. Konfigurér
cp .env.example .env              # udfyld nøgler + sheet-id
# læg Google service account-nøglen i ./secrets/service-account.json

# 3. Forbered arket (første gang)
python -m eta_tracker setup-sheet   # importerer data/seed_bl_list.csv + formatering

# 4. Kør
python -m eta_tracker run           # alle BL-numre
python -m eta_tracker run --limit 3 # hurtig test
python -m eta_tracker run --bl COP0305302,MEDUKC776011   # kun udvalgte BL (bruges live)
python -m eta_tracker run --skip-checked                 # spring allerede tjekkede rækker over
python -m eta_tracker run --replay  # demo-sikkerhed: afspil seneste gode resultat pr. BL
python -m eta_tracker reset-sheet   # tøm output-kolonner før demo
```

Den fulde opsætning, inkl. Google Cloud, står i [`docs/SETUP.md`](docs/SETUP.md).

## Dokumentation

| Fil | Indhold |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Instruktioner til Claude Code, der bygger projektet |
| [`docs/TECH_STACK.md`](docs/TECH_STACK.md) | Valgte værktøjer og hvorfor |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Flow, moduler, fejlhåndtering |
| [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) | Google Sheet-layout (vores "database"), status-regler og farver |
| [`docs/CARRIERS.md`](docs/CARRIERS.md) | Sådan slås BL op hos CMA CGM og MSC, og hvad der kan gå galt |
| [`docs/SETUP.md`](docs/SETUP.md) | Trin for trin: Google Sheet, service account, API-nøgle |
| [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) | Sådan vises det live, og hvad plan B er |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Byggeplan for POC'en og vejen videre til et rigtigt produkt |
| [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) | Det, vi skal have afklaret med kunden |

## Test

```bash
python -m pytest
```

## Status

🟡 **Kode skrevet, ikke kørt mod de rigtige sider endnu.**

- Afprøvet: status-logik, BL-udvælgelse, replay og skrivning via BL (pytest), og hele kæden
  browser → skærmbillede → sammenligning → `runs/` → replay mod lokale test-sider.
- Ikke afprøvet: rigtige CMA CGM- og MSC-sider, rigtigt Claude-kald og rigtigt Google Sheet.
  Kræver nøgler og netadgang, altså fase 0-spiken i [`docs/ROADMAP.md`](docs/ROADMAP.md).
- Søgefelter og "resultat klar"-tekster i `eta_tracker/carriers/cma.py` og `msc.py` er gæt ud fra `docs/CARRIERS.md`.
  Justér dem efter spiken.
