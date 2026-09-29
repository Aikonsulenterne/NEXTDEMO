# Tech stack

Princip: **færrest mulige bevægelige dele**. Alt kører lokalt på én laptop.

| Del | Valg | Hvorfor |
|---|---|---|
| Sprog | **Python 3.12** | Bedste biblioteker til både Google Sheets og browser-automatisering |
| Datakilde / "database" | **Google Sheet** | Kunden kender det, det er live på skærmen, og der er ingen database at drifte |
| Sheets-adgang | **gspread** + **google-auth** (service account) | Simpelt, stabilt, ingen OAuth-login-flow under demoen |
| Browser | **Playwright** (installeret Chrome via `channel="chrome"`, ellers Chromium; headed, persistent profil) | Rederiernes sider er JavaScript-tunge og har bot-beskyttelse. En rigtig browser kommer igennem, hvor rå HTTP-kald bliver blokeret |
| AI-ekstraktion | **Anthropic SDK**, model `claude-haiku-4-5` | Læser ETA ud af sidens tekst uanset layout. Hurtig og billig (få øre pr. opslag). Kan skiftes til `claude-sonnet-5-5` ved behov |
| Validering | **Pydantic v2** | Samme model bruges som JSON-schema i Claude-kaldet (tvinger formen) og til validering, før det skrives i arket |
| Terminal-output | **Rich** | Live-tabel med fremdrift. Ser godt ud på storskærm |
| CLI | **Typer** | `setup-sheet`, `run` (+ `--limit`, `--bl`, `--skip-checked`, `--manual`, `--replay`), `reset-sheet` |
| Konfiguration | **python-dotenv** | `.env` til nøgler og indstillinger |
| Test | **pytest** | Kun på sammenligningslogikken (den skal være 100 % korrekt) |

## requirements.txt (forslag)

```
gspread>=6.1
google-auth>=2.30
playwright>=1.47
anthropic>=0.40
pydantic>=2.8
rich>=13.7
typer>=0.12
python-dotenv>=1.0
pytest>=8.3
```

Efter første fulde kørsel: `pip freeze > requirements.lock` og installér fra den på demo-laptoppen, så en ny version ikke overrasker på dagen.

## Fravalgt, og hvorfor

| Fravalg | Grund |
|---|---|
| Database (Postgres, SQLite) | Google Sheet + `Log`-fane dækker behovet i en POC. Se `DATA_MODEL.md` |
| Rå `requests`/`httpx` scraping | Bliver blokeret af bot-beskyttelse hos begge rederier |
| Google Apps Script | Kan ikke køre en browser, så det kan ikke komme forbi bot-beskyttelsen |
| n8n / Make | Samme problem, plus endnu et system at vise frem |
| Rederiernes officielle API'er | Den rigtige løsning til produktion, men kræver onboarding/kundeaftale. Tager uger. Se `ROADMAP.md` |
| Tracking-aggregatorer (Vizion, Terminal49, ShipsGo m.fl.) | Også en god produktionsvej, men betalt og skjuler "AI'en der gør arbejdet", som er pointen i demoen |

## Omkostning

Ca. 25 opslag × ~3.000 tokens ≈ 75k tokens pr. kørsel med Haiku. Det er under 1 kr. pr. kørsel.
