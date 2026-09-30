# Rederier: sådan henter vi data

Vi slår ikke op i en browser. Vi henter rederiernes egne tracking-data via to **Apify-scrapere**
(lavet af en uafhængig udvikler, ikke rederierne). Én kørsel pr. rederi med alle BL-numre; ca. 5–10 sek. og 0,01 USD pr. BL.

| | CMA CGM | MSC |
|---|---|---|
| Apify-actor | `muhammetakkurtt/cma-cgm-cargo-tracking-scraper` | `muhammetakkurtt/msc-cargo-tracking-scraper` |
| Input | `{"trackingNumbers": ["COP0305302", ...]}` | `{"trackingNumbers": ["MEDUKC776011", ...]}` |
| Output | DCSA Track & Trace-events (samme standard som rederiets API) | MSC's egne felter, som på msc.com |
| BL-formater i vores data | `COP0305302`, `CGK0409397` | `MEDUKC776011`, `MEDUAAM80238` |

Actor-navnene kan ændres i `.env` (`APIFY_ACTOR_CMA`, `APIFY_ACTOR_MSC`).

## Sådan finder vi ETA (`eta_tracker/carriers.py`)

**MSC:** `bill_of_ladings[0].GeneralTrackingInfo.FinalPodEtaDate` (dd/mm/yyyy), dvs. "POD ETA" som på msc.com.
Har containerne forskellige `PodEtaDate`, bruges den seneste, og alle nævnes i `Note`. `Delivered = true` → ankommet.

**CMA CGM:** events, hvor `eventType = TRANSPORT`, `transportEventTypeCode = ARRI` og
`carrierSpecificData.shipmentLocationType = POD` (skibets ankomst til losningshavnen).
- Faktisk ankomst (`eventClassifierCode = ACT`) vinder over planlagt (`PLN`) → ankommet.
- Blandt planlagte vinder den senest opdaterede (`eventCreatedDateTime`).
- Datoen er den lokale dato i havnen (`eventDateTime[:10]`), som rederiets side viser den.
- Andre ankomster ignoreres, fx lastbilens ankomst til depot efter losning.

**Ingen data** (tom liste) → `Ikke fundet`. **Uventet form** (fx intet POD-event) → parseren giver op, og Claude læser rå-JSON'en
(`extract.py`). Uden Anthropic-nøgle bliver det `Tjek manuelt`.

## Verificeret mod rederiernes sider

| BL | Apify / vores læsning | Rederiets side |
|---|---|---|
| `MEDUKC776011` (MSC) | POD ETA 03-10-2026, Maputo, via Coega | ✅ 03/10/2026, samme rute, container og skibe |
| `COP0305302` (CMA) | Vessel arrival 03-10-2026, Mombasa, via Colombo | ⏳ ikke kontrolleret endnu |

## Risici

- **Uofficiel kilde.** Scraperne kan gå i stykker, når rederierne ændrer deres sider. Tjek før demoen, og hav `--replay` klar.
- **Data til tredjepart.** BL-numrene sendes til Apify. Kunden skal sige ja (`OPEN_QUESTIONS.md` #9).

## Officielle API'er (til drift)

- **CMA CGM:** API-portal med DCSA Track & Trace: https://api-portal.cma-cgm.com/ – selvbetjening med API-nøgle.
  Offentlig adgang giver planlagte ankomstdatoer; mere kræver, at man står på bookingen.
- **MSC:** https://developerportal.msc.com/ – ikke selvbetjening; adgang via MSC's salgsafdeling, evt. mod betaling.
- Begge følger **DCSA Track & Trace**, så én integration dækker flere rederier.
