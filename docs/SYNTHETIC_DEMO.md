# Synthetic portfolio demo data

The public hosted demo uses **entirely fictional data** — not real Telegram messages or any real crypto project.

## Generate the CSV

```bash
cd telegram-sentiment-tracker
python generate_synthetic_demo.py
```

Output: `output/synthetic_demo.csv` (~135k rows, Mar 2020 – Jun 2026 timeline).

- **Chat name:** Helix Protocol Community (fictional)
- **Sentiment:** ~50% positive overall, improving over time
- **Names & messages:** randomly generated; no Stacks or real-community references

Optional small sample for inspection:

```bash
python generate_synthetic_demo.py -o demo/synthetic_sample.csv --max-rows 500
```

## Publish to Google Sheets (for Render)

1. [Google Sheets](https://sheets.google.com) → new spreadsheet → name it `SentimentTrack Demo (synthetic)`
2. **File → Import → Upload** → `output/synthetic_demo.csv`
3. Share → **Anyone with the link → Viewer**
4. Copy the sheet URL → set as `DEMO_SHEET_URL` on Render

**Never** upload `full_history_v4.csv` or other real exports to a public sheet.

## Env vars (Render)

```
PORTFOLIO_MODE=1
DEMO_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_ID/edit
GITHUB_REPO_URL=https://github.com/kristenwagner0/telegram-sentiment-tracker
```
