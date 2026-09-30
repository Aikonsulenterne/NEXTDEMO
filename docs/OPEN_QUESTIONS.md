# Åbne spørgsmål

Afklares med kusinen før fase 1. Default-svaret bruges, hvis vi ikke hører andet.

| # | Spørgsmål | Default |
|---|---|---|
| 1 | Hvor mange dages forsinkelse før det er **rødt**? 1 dag eller fx 3+? | 1 dag (`DELAY_THRESHOLD_DAYS` i `.env`, eller en `Config`-fane) |
| 2 | Skal en **tidligere** ETA markeres (grøn)? | Ja, grøn |
| 3 | Hvilken ETA er "den rigtige": ankomst til havn (POD) eller levering til endelig destination? | POD |
| 4 | Er de 25 BL-numre ægte og aktive, så vi kan vise rigtige data live? Må de vises på storskærm? | Ja/ja. Ellers anonymisér kolonne B |
| 5 | Hvor lang tid bruger en medarbejder på det i dag pr. uge? (til "før/efter"-slide) | ca. 1 time/uge |
| 6 | Andre rederier i brug end CMA og MSC? | Kun CMA + MSC i POC |
| 7 | Skal demoen køre fra din laptop eller fra kundens egne skærme? | Din laptop |
| 8 | Hvornår er oplægget? | Ukendt, sæt dato på |
| 9 | Er det ok, at BL-numrene sendes til Apify (tredjepart), og at tracking-data evt. sendes til Anthropic (Claude) og gemmes lokalt i `runs/`? | Ja til POC; `runs/` slettes efter demoen |
| 10 | Står BL-numrene `MEDUAEO13818`, `MEDUAFO34490` og `MEDUAAO53495` med bogstavet **O** i kundens system, eller er det et **0**? | Tjekkes i spiken hos MSC |
| 11 | Hvis ét BL dækker flere containere med forskellige ETA'er: skal vi vise den seneste? | Ja, den seneste; de andre i `Note` |

## Bekræftede fakta

- Transit 6–8 uger. ETA rykker sig ofte undervejs.
- I dag slås det op manuelt på rederiernes hjemmesider.
- Rederier i kildedata: CMA CGM (17 BL) og MSC (8 BL).
- Ifølge kusinen har alle shippingvirksomheder den her udfordring.
