# Demo-manuskript

**Mål:** På 3–4 minutter skal salen se, at et kedeligt, manuelt job forsvinder.

## Skærm-layout

- **Venstre halvdel:** Google Sheet (fanen `Shipments`), zoomet så alle 25 rækker kan ses.
- **Højre halvdel:** Browser-vinduet, som Playwright styrer. Terminalen med Rich-tabel nederst eller på skærm 2.

## Forløb

| Tid | Hvad du siger | Hvad der sker |
|---|---|---|
| 0:00 | "Her er en helt almindelig liste med 25 forsendelser på vej hjem med skib. I dag sidder nogen og slår dem op én for én." | Vis arket. 20 rækker er tjekket i morges, 5 er tomme (de live-rækker, du har valgt) |
| 0:30 | "Lad os vise det manuelt én gang." | Slå ét BL op i hånden på MSC's side (~30 sek.) |
| 1:00 | "Forestil jer det 25 gange, hver uge. Nu lader vi AI'en gøre det." | Kør `python -m eta_tracker run --bl <de 5 live-BL>` |
| 1:10–3:00 | "Den åbner rederiets side ligesom jer, læser siden og finder den nye dato." | Browseren skifter side, de 5 rækker fyldes én for én (~20–30 sek. pr. BL) |
| 3:00 | "Røde er forsinket, og her kan I se med hvor mange dage. Det er dem, I skal ringe om." | **Når kørslen er færdig:** filtrér på `Forsinket` (filtervisning) |
| 3:30 | "Det tog et par minutter, uden at nogen løftede en finger. Og det kan køre hver morgen kl. 7." | Overgang til tilbud / Copilot-delen |

**Timing:** Et opslag tager ca. 20–30 sek. (sideload + 3–8 sek. pause + Claude). Alle 25 tager ~10 min, så de køres ikke live.
Live: **4–5 BL**, blandet CMA/MSC, valgt blandt dem der *faktisk har rykket sig* i generalprøven, så der kommer røde rækker på scenen.
Tag tid på live-kørslen ved generalprøven og justér antallet.

**Sortér ikke arket, mens kørslen står på.** Scriptet finder rækken via BL, så det går ikke galt, men rækker, der hopper rundt, forvirrer salen.

## Plan B (skal være klar)

| Problem på dagen | Løsning |
|---|---|
| Rederiets side blokerer eller er nede | `python -m eta_tracker run --replay --bl <samme 5>`: afspiller seneste gode resultat for de 5. Sig det højt: "Siden driller i dag, så her er min seneste kørsel af de samme forsendelser." Arket viser "Afspillet" i `Note` og det oprindelige tidspunkt |
| Intet internet | `--replay` + skærmoptagelse af en rigtig kørsel (optag aftenen før) |
| Google Sheets-fejl | Vis Rich-tabellen i terminalen, den viser samme resultat |

## Aftenen før

- [ ] Fuld kørsel af alle 25 (`run --manual`, så evt. captcha kan løses og profilen varmes op). Tjek at `runs/` har en god kørsel til replay
- [ ] Vælg 4–5 live-BL (mindst 1 CMA + 1 MSC, gerne 2–3 forsinkede). Tag tid på `run --bl <dem>`
- [ ] Optag skærmvideo af live-kørslen (backup)

## Samme morgen

- [ ] `python -m eta_tracker reset-sheet`
- [ ] `python -m eta_tracker run --bl <de 20 andre>` (stopper den undervejs: kør igen med `--skip-checked`)
- [ ] Tjek at live-rækkerne er tomme, og at der ligger et godt resultat for dem i `runs/` (til replay)
- [ ] Laptop på strøm, notifikationer slået fra, browserzoom 90 %

## Salgshook til sidst

Kusinen spørger om AI-undervisning → platform + rabatkode → "Vil I have sådan en løsning til jeres egne forsendelser? Book en snak."
