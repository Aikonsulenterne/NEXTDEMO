# ETA-tavlen (dashboard) og morgenjobbet

Dashboardet er en Claude-artifact: https://claude.ai/artifact/WjBCMzQyJNXzusiVUYNFF5
Siden (`dashboard/index.html`) læser `data.json`, der ligger ved siden af den. Kortet er `dashboard/land-110m.json`.
Hver hverdag udskifter morgenjobbet kun `data.json`.

## Funktioner på siden

- **Kør nu:** henter friske data via seerens egen Apify-connector (`call-actor`, `get-actor-run`, `get-dataset-items`),
  læser dem med de samme regler som `carriers.py` (portet til JavaScript, tjekket mod Python på alle 25) og opdaterer siden.
  Resultatet gemmes ikke for andre seere; det gør morgenjobbet.
- **Informér kunden:** færdig besked pr. forsendelse på dansk, engelsk eller fransk (fransk foreslås for fransktalende
  destinationer). "Omskriv med Claude" skriver den om live i valgt tone. Beskeden kopieres; den sendes ikke fra siden.
- **Det skal I holde øje med:** nyheder om havne og ruter (fra `news.json`), koblet til de forsendelser, der endnu skal forbi
  havnen. Klik fremhæver dem på kortet; trekanter på kortet markerer havnene.
- **Eksportér til Excel:** .xlsx med fanerne Oversigt, Forsendelser (farvet status, rigtige datoer, filtre), Havnenyheder
  (med links) og Kundebeskeder (danske skabeloner). Bygges i browseren med `xlsx-js-style` (hentes først ved klik) og gemmes
  via `downloads`-kapabiliteten, så seeren bekræfter filen.
- **Nyheder** vises som små kort; et klik åbner hele nyheden i en popup med berørte BL, kilde og "Vis på kortet".
- **Manglende svar:** springer et rederi en BL over en dag, beholdes sidst kendte data med en note ("Rederiet svarede ikke i dag …"),
  i stedet for at rækken skifter til "Ikke fundet".
- **Gennemgå kundebeskeder:** bladr gennem alle forsinkede, tidligere og udaterede forsendelser én ad gangen.
- Siden erklærer `mcp` (Apify) og `sample`. Knapperne vises kun, når seeren har adgang til dem.

## Morgenjobbets trin (følges af den planlagte Claude-session)

1. Hent repoet `Aikonsulenterne/nextdemo` og opret venv: `python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
2. Læs BL-listen fra Google-arket "Active BL List" (fil-id `1PoG4ljFHCGiktp9R0EOa1fT07MRRqqJQWcV8grpy6gs`) via Google Drive-connectoren
   og skriv den til `data/seed_bl_list.csv` (Carrier, BL, Current ETA; datoer dd/mm/yy → yyyy-mm-dd, mellemrum fjernes).
   Så er "Jeres ETA" altid den, der står i arket. Er Google Drive ikke forbundet, bruges `data/seed_bl_list.csv` som den er.
   Del BL-numrene i CMA og MSC.
3. Kør Apify-actorerne via Apify-connectoren (`call-actor`), én kørsel pr. rederi, med `{"trackingNumbers": [...]}` og
   `maxTotalChargeUsd` 0,5:
   - CMA: `muhammetakkurtt/cma-cgm-cargo-tracking-scraper`
   - MSC: `muhammetakkurtt/msc-cargo-tracking-scraper`
4. Hent resultaterne med `get-dataset-items` (hele datasættet). Store svar gemmes som fil; brug filstien direkte.
5. Hent gårsdagens data: læs artifactens `data.json` (Artifact `read` med `path: "data.json"`) og gem den som `prev.json`.
6. Nyheder: find havnene på ruterne (`route[].name` i `prev.json`, ellers `dashboard/news.json`s eksisterende havne) og søg på nettet
   efter aktuelle forhold, der kan forsinke: trængsel/ventetid, strejker, vejr, toldregler, ruteomlægninger (Rødehavet/Suez).
   Skriv `dashboard/news.json` i samme format som den nuværende: `checked_at`, og `items` med `id`, `severity`
   (høj ≥ 5 dages ventetid eller stop, middel 2–5 dage, lav < 2 dage, info = generelt), `ports` (UN/LOCODE, fx LKCMB),
   `title`, `summary` (2–3 sætninger på dansk, kun det kilden siger, med tal), `as_of` og `source` (`name`, `url`).
   Kun nyheder fra de seneste ca. 3 uger og kun med en kilde. Hellere færre end gættede.
7. Byg ny data: `.venv/bin/python -m eta_tracker snapshot <cma-fil> <msc-fil> --previous prev.json --news dashboard/news.json --out dashboard/data.json`
8. Læs `dashboard/data.json` og skriv en kort morgenbrief på dansk (3–5 sætninger): hvor mange er forsinket, hvilke 2–3 skal man
   ringe om først, hvad har ændret sig siden i går (`changed_since_last`), hvilke mangler dato, og hvilke havne med høj risiko
   flest forsendelser skal igennem (`news.items[].affected`). Kun fakta fra filen. Kør trin 7 igen med `--summary "<brief>"`.
9. Publicér: Artifact `publish` med `url` = artifactens URL, `file_path` = `dashboard/index.html` og
   `files` = `{"data.json": "dashboard/data.json"}`.
10. Fejler Apify, så publicér ikke. Dashboardet viser så gårsdagens data med gårsdagens dato, hvilket er ærligt.

## Omkostning

Apify ca. 0,26 USD pr. kørsel (25 BL). Claude-sessionen bruger kontoens forbrug.
