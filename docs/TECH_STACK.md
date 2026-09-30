# Tech stack

Princip: **færrest mulige bevægelige dele**. Alt kører lokalt på én laptop.

| Del | Valg | Hvorfor |
|---|---|---|
| Sprog | **Python 3.12** | Gode biblioteker til Google Sheets og API-kald |
| Datakilde / "database" | **Google Sheet** | Kunden kender det, det er live på skærmen, og der er ingen database at drifte |
| Sheets-adgang | **gspread** + **google-auth** (service account) | Simpelt, stabilt, ingen OAuth-login-flow under demoen |
| Tracking-data | **Apify** (to scrapere, kaldt med **httpx**) | Henter rederiernes egne data for alle BL på sekunder, uden browser og uden bot-beskyttelse på vores side. Ca. 0,01 USD pr. BL |
| AI | **Anthropic SDK**, model `claude-haiku-4-5` | Læser rå tracking-data, når de har en uventet form. Hurtig og billig |
| Validering | **Pydantic v2** | Samme model bruges som schema i Claude-kaldet og til validering, før noget skrives i arket |
| Terminal-output | **Rich** | Live-tabel med fremdrift. Ser godt ud på storskærm |
| CLI | **Typer** | `setup-sheet`, `run` (+ `--limit`, `--bl`, `--skip-checked`, `--replay`), `reset-sheet` |
| Konfiguration | **python-dotenv** | `.env` til nøgler og indstillinger |
| Test | **pytest** | Status-logik, parsere (på rigtige data) og en hel kørsel med falsk Apify |

Efter første fulde kørsel: `pip freeze > requirements.lock` og installér fra den på demo-laptoppen, så en ny version ikke overrasker på dagen.

## Fravalgt, og hvorfor

| Fravalg | Grund |
|---|---|
| Browser-automatisering (Playwright) | Første version. Langsom (~25 sek. pr. BL), mere opsætning og risiko for bot-blokering. Erstattet af Apify efter test |
| Apify's Python-klient | Ét HTTP-kald er nok; `httpx` holder afhængighederne nede |
| Database (Postgres, SQLite) | Google Sheet + `Log`-fane dækker behovet i en POC. Se `DATA_MODEL.md` |
| n8n / Make | Endnu et system at vise frem og vedligeholde |
| Rederiernes officielle API'er | Den rigtige løsning til drift. CMA: selvbetjening; MSC: via salg. Se `CARRIERS.md` og `ROADMAP.md` |
| Tracking-aggregatorer (Vizion, Terminal49, ShipsGo m.fl.) | God produktionsvej, men betalt abonnement |

## Omkostning

Apify: 25 BL × 0,01 USD + opstart ≈ 0,26 USD (ca. 2 kr.) pr. kørsel på gratis-niveauet.
Claude: kun når data har uventet form, få øre pr. gang.
