# Demo-manuskript

**Mål:** På 3–4 minutter skal salen se, at et kedeligt, manuelt job forsvinder.

## Skærm-layout

- **Venstre halvdel:** Google Sheet (fanen `Shipments`), zoomet så alle 25 rækker kan ses.
- **Højre halvdel:** Terminalen med Rich-tabellen.

## Forløb

| Tid | Hvad du siger | Hvad der sker |
|---|---|---|
| 0:00 | "Her er en helt almindelig liste med 25 forsendelser på vej hjem med skib. I dag sidder nogen og slår dem op én for én." | Vis arket. Kun kolonne A–C er udfyldt |
| 0:30 | "Lad os vise det manuelt én gang." | Slå ét BL op i hånden på MSC's side (~30 sek.) |
| 1:00 | "Forestil jer det 25 gange, hver uge. Nu lader vi AI'en gøre det." | Kør `python -m eta_tracker run` |
| 1:10–2:00 | "Den henter data fra rederierne for alle 25 på én gang og tjekker hver enkelt." | ~10 sek. hentning, derefter fyldes arket række for række (1 sek. pr. række) |
| 2:00 | "Røde er forsinket, og her kan I se med hvor mange dage. Det er dem, I skal ringe om." | **Når kørslen er færdig:** filtrér på `Forsinket` (filtervisning) |
| 2:30 | "Det tog et minut, uden at nogen løftede en finger. Og det kan køre hver morgen kl. 7." | Overgang til tilbud / Copilot-delen |

**Timing:** Hentning tager ca. 10–20 sek. for alle 25. Derefter styrer `REVEAL_DELAY_SECONDS` (standard 1 sek.) tempoet i arket.
Sæt den op eller ned, så det passer til din fortælling.

**Sortér ikke arket, mens kørslen står på.** Scriptet finder rækken via BL, så det går ikke galt, men rækker, der hopper rundt, forvirrer salen.

## Plan B (skal være klar)

| Problem på dagen | Løsning |
|---|---|
| Apify eller rederiernes data er nede | `python -m eta_tracker run --replay`: afspiller seneste gode resultat. Sig det højt: "Nettet driller i dag, så her er min seneste kørsel af de samme forsendelser." Arket viser "Afspillet" i `Note` og det oprindelige tidspunkt |
| Intet internet | `--replay` + skærmoptagelse af en rigtig kørsel (optag aftenen før) |
| Google Sheets-fejl | Vis Rich-tabellen i terminalen, den viser samme resultat |

## Aftenen før

- [ ] Fuld kørsel af alle 25. Tjek at `runs/` har en god kørsel til replay
- [ ] Tjek 1–2 af de røde mod rederiets egen side, så du kan stå inde for dem
- [ ] Optag skærmvideo af en fuld kørsel (backup)

## Samme morgen

- [ ] `python -m eta_tracker reset-sheet`
- [ ] Laptop på strøm, notifikationer slået fra

## Salgshook til sidst

Kusinen spørger om AI-undervisning → platform + rabatkode → "Vil I have sådan en løsning til jeres egne forsendelser? Book en snak."
