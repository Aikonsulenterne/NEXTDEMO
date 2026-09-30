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
- **Gennemgå kundebeskeder:** bladr gennem alle forsinkede, tidligere og udaterede forsendelser én ad gangen.
- Siden erklærer `mcp` (Apify) og `sample`. Knapperne vises kun, når seeren har adgang til dem.

## Morgenjobbets trin (følges af den planlagte Claude-session)

1. Hent repoet `Aikonsulenterne/nextdemo` og opret venv: `python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt`.
2. Læs BL-listen i `data/seed_bl_list.csv` (Carrier, BL, Current ETA). Del BL-numrene i CMA og MSC.
3. Kør Apify-actorerne via Apify-connectoren (`call-actor`), én kørsel pr. rederi, med `{"trackingNumbers": [...]}` og
   `maxTotalChargeUsd` 0,5:
   - CMA: `muhammetakkurtt/cma-cgm-cargo-tracking-scraper`
   - MSC: `muhammetakkurtt/msc-cargo-tracking-scraper`
4. Hent resultaterne med `get-dataset-items` (hele datasættet). Store svar gemmes som fil; brug filstien direkte.
5. Hent gårsdagens data: læs artifactens `data.json` (Artifact `read` med `path: "data.json"`) og gem den som `prev.json`.
6. Byg ny data: `.venv/bin/python -m eta_tracker snapshot <cma-fil> <msc-fil> --previous prev.json --out dashboard/data.json`
7. Læs `dashboard/data.json` og skriv en kort morgenbrief på dansk (3–5 sætninger): hvor mange er forsinket, hvilke 2–3 skal man
   ringe om først, hvad har ændret sig siden i går (`changed_since_last`), og hvilke mangler dato. Kun fakta fra filen.
   Kør trin 6 igen med `--summary "<brief>"`.
8. Publicér: Artifact `publish` med `url` = artifactens URL, `file_path` = `dashboard/index.html` og
   `files` = `{"data.json": "dashboard/data.json"}`.
9. Fejler Apify, så publicér ikke. Dashboardet viser så gårsdagens data med gårsdagens dato, hvilket er ærligt.

## Omkostning

Apify ca. 0,26 USD pr. kørsel (25 BL). Claude-sessionen bruger kontoens forbrug.
