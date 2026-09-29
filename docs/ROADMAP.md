# Roadmap

## Fase 0: Afklaring (½ dag)

- [ ] Svar på `OPEN_QUESTIONS.md` fra kusinen
- [ ] **Spike:** slå 2 CMA + 2 MSC BL op manuelt i en almindelig browser. Notér præcis flow, URL'er og hvor ETA står. Tag et af MSC-BL'erne med bogstavet O med
- [ ] **Spike:** samme 4 via Playwright headed (prøv `channel="chrome"`). Kommer vi forbi bot-beskyttelsen? *Det er projektets største risiko, så gør det først*
- [ ] **Spike:** tag tid på ét opslag pr. rederi. Bestemmer, hvor mange BL der kan køres live

## Fase 1: POC (1–2 dage)

| # | Opgave | Estimat |
|---|---|---|
| 1 | Projektskelet, config, CLI (`--limit`, `--bl`, `--skip-checked`, `--manual`, `--replay`) | 1 t |
| 2 | `sheet.py`: læs, skriv, `setup-sheet`, conditional formatting | 2 t |
| 3 | `compare.py` + tests | 1 t |
| 4 | `browser.py` + `carriers/msc.py` | 2–3 t |
| 5 | `carriers/cma.py` | 2 t |
| 6 | `extract.py` (Claude + Pydantic) | 1 t |
| 7 | `run`-orkestrering, Rich-UI, `runs/`-lagring | 2 t |
| 8 | `--replay` + `reset-sheet` | 1 t |
| 9 | Fuld kørsel på 25 BL, fejlret. Lås versioner (`pip freeze > requirements.lock`) når det virker | 2 t |
| 10 | Generalprøve efter `DEMO_SCRIPT.md` | 1 t |

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
| Bot-beskyttelse blokerer Playwright | Middel | Headed + `channel="chrome"` + persistent profil (varmet op med `--manual`) + langsomt tempo. Ellers `--replay` eller Claude in Chrome |
| Siden viser flere ETA'er (omladning) | Høj | Prompt beder om POD-ETA. Lav confidence → `Tjek manuelt` |
| BL er leveret/arkiveret og findes ikke længere | Middel | Status `Ikke fundet` med note |
| Rederiets side er nede på demodagen | Lav | `--replay` + videobackup |
| Live-kørslen tager længere end demo-slottet | Høj | Kun 4–5 BL live via `--bl`, resten forkørt. Tages tid på ved generalprøven |
