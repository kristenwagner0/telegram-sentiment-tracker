# Publish redacted demo data to Google Sheets

Run this **once** before deploying to Render. Do not upload raw `full_history_v4.csv`.

## 1. Generate redacted CSV

```bash
cd telegram-sentiment-tracker
python redact_for_demo.py -i output/full_history_v4.csv --dry-run   # spot-check
python redact_for_demo.py -i output/full_history_v4.csv -o output/demo_public.csv
```

Output: `output/demo_public.csv` (~33 MB, 134k rows, pseudonymized senders).

## 2. Import into a new Google Sheet

1. Go to [Google Sheets](https://sheets.google.com) → **Blank spreadsheet**
2. Name it e.g. `SentimentTrack Demo (redacted)`
3. **File → Import → Upload** → select `output/demo_public.csv`
4. Import location: **Replace current sheet**
5. Wait for import to finish (~1–2 min)

## 3. Share as view-only

1. **Share** (top right)
2. **General access → Anyone with the link → Viewer**
3. Copy the sheet URL

## 4. Get the export URL for Render

Paste the edit URL into Render as `DEMO_SHEET_URL`. Examples that work:

```
https://docs.google.com/spreadsheets/d/SHEET_ID/edit#gid=0
https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv&gid=0
```

The dashboard server converts edit links to CSV export automatically.

## 5. Verify before deploy

Open this in a browser (replace `SHEET_ID`):

```
https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv&gid=0
```

You should see plain CSV text, not a Google login page.

---

**Security:** Use a **separate** sheet from your raw data. Never commit `demo_public.csv` or unredacted CSVs to GitHub.
