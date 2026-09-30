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
Google Sheet  ──►  Hent tracking-data hos rederiet  ──►  Find ETA ved POD  ──►  Sammenlign  ──►  Skriv tilbage + farv
(BL-liste)         (Apify, alle BL på én gang)           (kode, ellers Claude)   (gammel vs ny)    (rød = forsinket)
```

1. Læser listen af forsendelser fra et **Google Sheet** (Carrier, BL, Current ETA).
2. Henter rederiernes egne tracking-data for alle BL-numre via **Apify** (én kørsel pr. rederi, **CMA CGM** og **MSC**).
3. Finder ETA ved losningshavnen (POD). Har dataene en uventet form, læser **Claude** dem i stedet.
4. Sammenligner ny ETA med gammel ETA og regner forskellen ud i dage.
5. Skriver resultatet tilbage i arket, række for række: **rød** = forsinket, **grøn** = tidligere, neutral = uændret, **gul** = tjek manuelt, grå = ikke fundet.
6. Logger hver kørsel i en separat fane, så man kan se udviklingen over tid.

Alle 25 BL tager ca. 20 sekunder og koster ca. 2 kr. i Apify pr. kørsel.

## Hvad POC'en IKKE er

- Ikke et produkt. Ingen login, ingen brugere, ingen server. Den kører lokalt fra en terminal.
- Apify-scraperne er lavet af en uafhængig udvikler, ikke rederierne. Til drift skal man over på rederiernes officielle API'er
  eller en tracking-aggregator (se [`docs/ROADMAP.md`](docs/ROADMAP.md)).

## Kom i gang (kort)

Kør én linje ad gangen (ingen kommentarer bag kommandoerne; zsh på Mac læser dem ikke som kommentarer).

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
cp .env.example .env
```

Udfyld `.env` (Apify-, Anthropic- og Google-nøgler), og læg Google service account-nøglen i `./secrets/service-account.json`.

```bash
python -m eta_tracker setup-sheet
python -m eta_tracker run --bl COP0305302,MEDUKC776011
python -m eta_tracker run
python -m eta_tracker run --replay
python -m eta_tracker reset-sheet
```

Den fulde opsætning står i [`docs/SETUP.md`](docs/SETUP.md).

## Dokumentation

| Fil | Indhold |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Instruktioner til Claude Code, der bygger projektet |
| [`docs/TECH_STACK.md`](docs/TECH_STACK.md) | Valgte værktøjer og hvorfor |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Flow, moduler, fejlhåndtering |
| [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) | Google Sheet-layout (vores "database"), status-regler og farver |
| [`docs/CARRIERS.md`](docs/CARRIERS.md) | Sådan hentes og læses data fra CMA CGM og MSC |
| [`docs/SETUP.md`](docs/SETUP.md) | Trin for trin: Google Sheet, service account, API-nøgler |
| [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) | Sådan vises det live, og hvad plan B er |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Byggeplan og vejen videre til et rigtigt produkt |
| [`docs/OPEN_QUESTIONS.md`](docs/OPEN_QUESTIONS.md) | Det, vi skal have afklaret med kunden |

## Test

```bash
python -m pytest
```

## Status

🟡 **Kode skrevet og testet mod rigtige data, ikke kørt fuldt igennem med nøgler endnu.**

- Afprøvet: Apify-scraperne returnerer samme ETA som rederiernes egne sider (MSC `MEDUKC776011`: 03-10-2026,
  kontrolleret på msc.com). Parserne er testet på de rigtige svar. Hele kæden er testet med falsk Apify og uden ark.
- Ikke afprøvet: en fuld kørsel med rigtig Apify-nøgle og rigtigt Google Sheet.
- Mangler kontrol: CMA `COP0305302` (vores læsning: 03-10-2026 i Mombasa) på cma-cgm.com.
