# CLAUDE.md – instruktioner til Claude Code

Du bygger en **lille, robust POC** til en live-demo foran shipping-folk. Den skal virke på scenen.
Den skal ikke være smuk kode eller klar til produktion.

## Mål (i prioriteret rækkefølge)

1. **Virker live**: opslag hos CMA CGM og MSC lykkes, og resultatet lander i Google Sheet med farver.
2. **Ser overbevisende ud**: synlig browser, pæn terminal-output (Rich), arket opdaterer sig mens man kigger.
3. **Fejler pænt**: et BL der ikke kan slås op giver status `Ikke fundet` + note. Programmet crasher aldrig.
4. **Kan afspilles**: `--replay` genbruger seneste gode resultat pr. BL, hvis nettet eller rederiets side driller på dagen.

## Læs først

- `docs/ARCHITECTURE.md`: moduler og flow
- `docs/DATA_MODEL.md`: præcist sheet-layout og status-regler (følg dem nøjagtigt)
- `docs/CARRIERS.md`: URL'er og faldgruber per rederi

## Regler

- **Python 3.12**, afhængigheder kun fra `docs/TECH_STACK.md`. Spørg før du tilføjer nye.
- **Overskriv aldrig kolonnen `Current ETA`** (baseline). Nye data skrives kun i output-kolonnerne.
- **Ét BL ad gangen**, med 3–8 sek. tilfældig pause imellem. Ingen parallelle opslag mod rederierne.
- **Headed browser** (`headless=False`) med persistent profil i `./.browser-profile/`. Det ligner et menneske og ser godt ud i demoen.
  Brug `channel="chrome"` (installeret Chrome), hvis den findes; fald tilbage til Playwrights Chromium. Den er sværere at genkende som bot.
- **Blokering tjekkes i carrier-modulet**, før Claude kaldes: simpelt keyword-tjek på sideteksten
  (fx "captcha", "access denied", "verify you are human") → `Ikke fundet` + note "Blokeret af rederiets side". Spar Claude-kaldet.
- **Ekstraktion via Claude**: send sidens synlige tekst (ikke HTML) til `claude-haiku-4-5` og tving struktureret svar
  via et tool-/JSON-schema (ikke kun "returnér JSON" i prompten):
  `{"page_state": "ok|not_found|blocked|error", "eta": "YYYY-MM-DD" | null, "arrived": bool, "vessel": str|null, "pod": str|null, "confidence": "high|medium|low", "note": str}`.
  Validér med Pydantic. Status-mapping står i `docs/DATA_MODEL.md`.
- **Skriv til arket via BL-opslag**, ikke via rækkenummer fundet ved start. Find rækken med BL'et lige før hver skrivning,
  så en sortering/filtrering undervejs ikke sender resultatet til den forkerte forsendelse.
- **Datoer skrives som rigtige datoer** (`value_input_option="USER_ENTERED"`, ISO-streng), og arket sættes til locale `da_DK`.
  Ellers bliver de tekst, og sortering + conditional formatting virker ikke.
- **Gem bevis** for hvert opslag: screenshot til `./runs/<timestamp>/<BL>.png` og rå sidetekst til `<BL>.txt`.
  Det bruges af `--replay` og til fejlsøgning.
- **Trim BL-numre** (der er mindst ét med mellemrum til sidst i kildedata).
- Hemmeligheder kun i `.env` og `./secrets/`. Begge er i `.gitignore`.
- Dansk i al brugervendt tekst (terminal, sheet, statusser). Kode, variabler og kommentarer på engelsk.

## Definition of done for POC

- [ ] `setup-sheet` opretter faner, headers, formatering og importerer seed-data
- [ ] `run --bl <CMA-BL>,<MSC-BL>` slår netop de valgte BL op og skriver korrekt tilbage
- [ ] `run --skip-checked` springer rækker over, der allerede har `Sidst tjekket` (bruges til demo-forberedelse)
- [ ] `run` på alle 25 gennemføres uden crash; fejlede opslag er markeret, ikke tavse
- [ ] Rød/grøn/gul/neutral/grå formatering virker via conditional formatting (ikke hardcodede farver per celle)
- [ ] `Log`-fanen får én række per BL per kørsel
- [ ] `run --replay` virker uden netadgang til rederierne og markerer rækkerne som afspillet (se `docs/ARCHITECTURE.md`)
- [ ] `reset-sheet` tømmer kolonne D–J (rører aldrig A–C)
- [ ] Test af `compare.py` (status-logik inkl. `page_state`, manglende/ugyldig `Current ETA`) med pytest
- [ ] Generalprøve: én live-kørsel med 4–5 BL er timet og passer i demo-slottet

## Ikke i scope

Webapp/UI, database, brugere, planlagte kørsler, e-mail-notifikationer, flere rederier end CMA og MSC.
Det står i `docs/ROADMAP.md` som næste skridt. Byg det ikke nu.
