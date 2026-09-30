# Opsætning, trin for trin

Forventet tid: ca. 30 min første gang. Kør kommandoerne én linje ad gangen.

## 1. Python 3.12 (Mac)

```bash
brew install python@3.12
```

Har du ikke Homebrew: hent Python 3.12 fra https://www.python.org/downloads/macos/. Luk og åbn terminalen bagefter.

## 2. Google Sheet

1. Brug arket **"Active BL List"** (eller opret et nyt).
2. Kopiér sheet-ID fra URL'en: `https://docs.google.com/spreadsheets/d/`**`<SHEET_ID>`**`/edit`
3. `setup-sheet` opretter fanerne `Shipments` og `Log`. Eksisterende faner røres ikke.

## 3. Google service account (så scriptet kan skrive i arket)

1. Gå til https://console.cloud.google.com/ → opret projekt **eta-tracker-poc**.
2. *APIs & Services → Library* → aktivér **Google Sheets API** (og **Google Drive API**).
3. *IAM & Admin → Service Accounts* → **Create service account** (navn: `eta-tracker`). Ingen roller nødvendige.
4. Åbn service account → *Keys* → **Add key → JSON**. Gem filen som `./secrets/service-account.json`.
5. Kopiér service account-mailen (`eta-tracker@<projekt>.iam.gserviceaccount.com`).
6. I Google Sheet: **Del** → indsæt mailen → **Editor**.

## 4. Apify-nøgle

1. Log ind på https://console.apify.com/ → *Settings → API & Integrations* → kopiér **Personal API token**.
2. Gratis-niveauet rækker langt: en kørsel med 25 BL koster ca. 0,26 USD.

## 5. Anthropic API-nøgle

1. https://console.anthropic.com/ → *API Keys* → opret nøgle.
2. Sæt et lille månedligt loft (fx 10 USD). Claude bruges kun, når data har en uventet form.

## 6. Lokalt miljø

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
cp .env.example .env
open -e .env
```

Udfyld `APIFY_TOKEN`, `ANTHROPIC_API_KEY` og `GOOGLE_SHEET_ID` i `.env` og gem.

## 7. Første kørsel

```bash
python -m eta_tracker setup-sheet
python -m eta_tracker run --bl COP0305302,MEDUKC776011
```

## Tjekliste

- [ ] `python -m pytest` er grøn
- [ ] Sheet delt med service account-mailen, og `secrets/service-account.json` ligger på plads
- [ ] `.env` udfyldt
- [ ] Testkørslen skriver 2 rækker med farve
