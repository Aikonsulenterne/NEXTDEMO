# Opsætning, trin for trin

Forventet tid: ca. 30 min første gang.

## 1. Google Sheet

1. Opret et nyt Google Sheet, fx **"ETA Tracker – Demo"**.
2. Kopiér sheet-ID fra URL'en: `https://docs.google.com/spreadsheets/d/`**`<SHEET_ID>`**`/edit`
3. Lad det være tomt. `setup-sheet` opretter faner, headers og formatering.

## 2. Google service account (så scriptet kan skrive i arket)

1. Gå til https://console.cloud.google.com/ → opret projekt **eta-tracker-poc**.
2. *APIs & Services → Library* → aktivér **Google Sheets API** (og **Google Drive API**).
3. *IAM & Admin → Service Accounts* → **Create service account** (navn: `eta-tracker`). Ingen roller nødvendige.
4. Åbn service account → *Keys* → **Add key → JSON**. Gem filen som `./secrets/service-account.json`.
5. Kopiér service account-mailen (`eta-tracker@<projekt>.iam.gserviceaccount.com`).
6. I Google Sheet: **Del** → indsæt mailen → **Editor**.

## 3. Anthropic API-nøgle

1. https://console.anthropic.com/ → *API Keys* → opret nøgle.
2. Sæt et lille månedligt loft (fx 10 USD). POC'en bruger langt under det.

## 4. Lokalt miljø

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium   # fallback; har du Chrome installeret, bruges den
cp .env.example .env
```

Udfyld `.env` (se `.env.example`).

## 5. Første kørsel

```bash
python -m eta_tracker setup-sheet     # opretter faner + importerer 25 BL
python -m eta_tracker run --bl COP0305302,MEDUKC776011 --manual   # test med 1 CMA + 1 MSC
```

Første gang åbner browseren, og du kan få cookie-bannere eller captcha. Acceptér/løs dem manuelt; med `--manual` venter scriptet på dig.
Profilen gemmes i `.browser-profile/`, så det kun sker én gang.

## Tjekliste

- [ ] Sheet oprettet og delt med service account-mailen
- [ ] `secrets/service-account.json` ligger på plads
- [ ] `.env` udfyldt
- [ ] Testkørslen skriver 2 rækker med farve
