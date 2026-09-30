# Datamodel: Google Sheet som database

Vi bruger **ingen database**. Google Sheet er både input, output og historik.
Det er et bevidst valg: kunden arbejder allerede i regneark, og i demoen er arket "skærmen".

## Fane 1: `Shipments` (input + seneste status)

| Kol | Header | Type | Hvem skriver | Beskrivelse |
|---|---|---|---|---|
| A | `Carrier` | tekst | Kunde | `CMA` eller `MSC` |
| B | `BL` | tekst | Kunde | Fragtbrevsnummer (trimmes ved læsning) |
| C | `Current ETA` | dato | Kunde | **Baseline.** Overskrives aldrig af scriptet |
| D | `Ny ETA` | dato | Script | ETA fundet hos rederiet |
| E | `Forskel (dage)` | heltal | Script | `Ny ETA − Current ETA`. Positiv = forsinket |
| F | `Status` | tekst | Script | Se status-regler |
| G | `Skib` | tekst | Script | Skibsnavn, hvis fundet |
| H | `Destination` | tekst | Script | Losningshavn (POD), hvis fundet |
| I | `Sidst tjekket` | dato-tid | Script | Tidspunkt for opslag |
| J | `Note` | tekst | Script | Fejlbeskrivelse eller AI-note |

Frys række 1. Datoformat `dd-mm-yyyy` (dansk), arkets locale `da_DK`.
Datoer skrives med `value_input_option="USER_ENTERED"` som ISO-streng, så de bliver rigtige datoer og ikke tekst.
Det gælder også `Current ETA` ved import af seed-data.

## Fane 2: `Log` (historik, kun append)

| Kol | Header |
|---|---|
| A | `Kørsel` (timestamp for kørslen, samme for alle rækker i én kørsel) |
| B | `Carrier` |
| C | `BL` |
| D | `Current ETA` |
| E | `Ny ETA` |
| F | `Forskel (dage)` |
| G | `Status` |
| H | `Confidence` |
| I | `Rådata` (relativ sti til rederiets rå data i `runs/`) |

Bruges til at vise "ETA har rykket sig 3 gange på 2 uger" senere. Ikke nødvendigt for demoen, men gratis at have.

## Fane 3: `Config` (valgfri)

| Nøgle | Default | Betydning |
|---|---|---|
| `DELAY_THRESHOLD_DAYS` | `1` | Mindste antal dage, før noget tæller som forsinket |

Hvis fanen ikke findes, bruges værdien fra `.env`. `setup-sheet` opretter den ikke; tilføj den i hånden, hvis kunden vil kunne ændre tærsklen selv.

## Status-regler (`compare.py`)

`compare.py` får carrier-modulets resultat (evt. blokeret/timeout) og Claude-svaret og returnerer `(diff_days, status)`.
Reglerne tjekkes **i denne rækkefølge**; første match vinder.

Givet `diff = ny_eta − current_eta` i hele dage og `T = DELAY_THRESHOLD_DAYS`:

| # | Betingelse | Status | Farve |
|---|---|---|---|
| 1 | ukendt rederi i kolonne A | `Ikke understøttet` | ⚪ grå `#EFEFEF` |
| 2 | opslag fejlede (timeout, blokeret) eller `page_state` ≠ `ok` | `Ikke fundet` | ⚪ grå `#EFEFEF` |
| 3 | `eta` mangler, `confidence = low`, eller `Current ETA` er tom/ugyldig | `Tjek manuelt` | 🟡 gul `#FFF2CC` |
| 4 | `diff >= T` | `Forsinket` | 🔴 rød `#F4C7C3`, fed rød tekst i `Forskel` |
| 5 | `diff <= -T` | `Tidligere` | 🟢 grøn `#D9EAD3` |
| 6 | ellers (`-T < diff < T`) | `Uændret` | ingen farve |

Ved regel 3 med gyldig `eta` men ugyldig `Current ETA` skrives `Ny ETA` stadig, men `Forskel` efterlades tom.

**Særtilfælde, som prompten håndterer (ingen ekstra statusser):**

- **Allerede ankommet:** `arrived = true`, `eta` = faktisk ankomstdato. Status beregnes som normalt; `Note` starter med "Ankommet".
- **Flere containere på samme BL:** `eta` = den **seneste** ETA (den forsendelsen venter på). Øvrige datoer nævnes i `Note`.

**Farver** sættes som conditional formatting med brugerdefineret formel på området `D2:F`, fx `=$F2="Forsinket"`
(én regel pr. status, samme mønster). Ikke som hardcodet format pr. celle.
Så er arket stadig korrekt, hvis nogen retter en værdi i hånden.

## Seed-data

`data/seed_bl_list.csv` indeholder de 25 BL-numre fra kundens `Active_BL_List.xlsx`:
17 × CMA (`COP…`, én `CGK…`) og 8 × MSC (`MEDU…`). Mellemrum er fjernet, og datoer er ISO.
