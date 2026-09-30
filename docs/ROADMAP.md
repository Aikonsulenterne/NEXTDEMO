# Roadmap

## Fase 0: Afklaring

- [ ] Svar på `OPEN_QUESTIONS.md` fra kusinen (især #9: data til Apify)
- [x] **Spike:** browser-opslag vs. API vs. Apify. Apify valgt: samme data som rederiernes sider, ~5 sek. og 0,01 USD pr. BL
- [x] MSC `MEDUKC776011` kontrolleret mod msc.com: POD ETA 03/10/2026 matcher
- [ ] CMA `COP0305302` kontrolleres mod cma-cgm.com (vores læsning: 03-10-2026, Mombasa)

## Fase 1: POC

| # | Opgave | Status |
|---|---|---|
| 1 | Projektskelet, config, CLI (`--limit`, `--bl`, `--skip-checked`, `--replay`) | ✅ |
| 2 | `sheet.py`: læs, skriv, `setup-sheet`, conditional formatting | ✅ (ikke kørt mod rigtigt ark endnu) |
| 3 | `compare.py` + tests | ✅ |
| 4 | `apify.py` + `carriers.py` (parsere testet på rigtige svar) | ✅ |
| 5 | `extract.py` (Claude-fallback + Pydantic) | ✅ |
| 6 | `run`-orkestrering, Rich-UI, `runs/`-lagring, `--replay`, `reset-sheet` | ✅ |
| 7 | Fuld kørsel på 25 BL med rigtige nøgler, fejlret. Lås versioner (`pip freeze > requirements.lock`) | ⏳ |
| 8 | Generalprøve efter `DEMO_SCRIPT.md` | ⏳ |

## Fase 2: Hvis kunden vil have det rigtigt (efter demoen)

Det her er **tilbuddet**. POC'en viser værdien, og produktet bygges ordentligt:

- **Officielle datakilder:** CMA CGM API-portal (DCSA Track & Trace), MSC via kunde-onboarding, eller én aggregator-API, der dækker 20+ rederier
- **Flere rederier:** Maersk, Hapag-Lloyd, Evergreen, ONE (samme DCSA-standard)
- **Planlagt kørsel** hver morgen (cloud-job) i stedet for manuelt
- **Notifikation:** mail/Teams med "3 forsendelser forsinket siden i går"
- **Historik og mønstre:** hvilke ruter/rederier forsinker oftest
- **Acceptér ny ETA:** en måde at gøre den nye ETA til baseline, når kunden har handlet på den (i POC'en ændres `Current ETA` aldrig)
- **Integration** til kundens ERP/indkøbssystem i stedet for Google Sheet
- **Copilot/Excel-vinkel:** samme data i Excel + Copilot til spørgsmål som "hvilke kunder rammes af forsinkelserne?"

## Risici

| Risiko | Sandsynlighed | Afbødning |
|---|---|---|
| Apify-scraperne holder op med at virke (uofficielle, én udvikler) | Middel | Kør aftenen før, `--replay` på dagen. Til drift: officielle API'er |
| Data har flere ETA'er (omladning, flere containere) | Høj | Parser vælger ankomst ved POD og seneste container-ETA. Uventet form → Claude → evt. `Tjek manuelt` |
| BL er leveret/arkiveret og findes ikke længere | Middel | Status `Ikke fundet` med note |
| Apify eller nettet er nede på demodagen | Lav | `--replay` + videobackup |
| Kunden vil ikke sende BL-numre til tredjepart | Middel | Spørg nu (#9). Alternativ: CMA's officielle API (selvbetjening) |
