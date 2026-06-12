# Telegram Sentiment Tracker

Parse Telegram Desktop `result.json` exports, score message sentiment (Korean or English) with offline HuggingFace models, extract weekly complaint keywords, and explore results in a **visual dashboard** — with optional Google Sheets sync.

## Open the dashboard (matches your Claude design)

1. Go to this folder in **Finder**
2. **Double-click `Open Dashboard.command`**
3. Your browser opens **SentimentTrack** — dark UI, left nav, charts (same look as your Claude HTML)

**All sidebar links are clickable:** Dashboard · Trends · Complaints · Messages · Google Sheets · Upload export · Settings

- **Demo data** loads instantly for portfolio previews
- **Google Sheets** tab: paste your published CSV URL for live data
- **Upload export** explains that full analysis runs locally (for your presentation story)

If macOS blocks the launcher: right-click → **Open** → **Open** (one-time).

See [PORTFOLIO.md](PORTFOLIO.md) for a 2-minute demo script.

## Quick start (Terminal)

```bash
cd telegram-sentiment-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Drop your export at exports/my_chat/result.json, then:
python telegram_sentiment.py --input exports/my_chat/result.json --lang ko
```

First run downloads the model (~500 MB Korean, ~250 MB English) to `~/.cache/huggingface/`.

## Telegram export

1. Open **Telegram Desktop**
2. Open the chat → **⋮** → **Export chat history**
3. Format: **JSON** (produces `result.json` in a folder)
4. Copy the folder into `exports/`

## Usage

```bash
# Korean chat (default)
python telegram_sentiment.py -i exports/my_chat/result.json --lang ko

# English chat
python telegram_sentiment.py -i exports/my_chat/result.json --lang en

# Parse only — no model download
python telegram_sentiment.py -i exports/my_chat/result.json --dry-run

# Smaller batches if you run out of memory
python telegram_sentiment.py -i exports/my_chat/result.json --batch-size 8
```

**Output** (written to `output/` by default):

| File | When |
|------|------|
| `full_history.csv` | Export spans multiple weeks |
| `week_YYYY-MM-DD.csv` | Export is a single week |

### CSV columns

`msg_id`, `date`, `week_start`, `chat_name`, `from`, `from_id`, `text`, `sentiment_label`, `sentiment_score`, `is_reply`, `top_complaints`

- `sentiment_label`: `pos` / `neg` / `neu`
- `week_start`: Monday of each ISO week
- `top_complaints`: top TF-IDF keywords from **negative** messages that week

## Google Sheets — manual import (Path A)

1. Run the script → get `output/full_history_v2.csv`
2. Optional — refresh complaint keywords (fast, no ML re-run):
   ```bash
   python refresh_keywords.py -i output/full_history_v2.csv -o output/full_history_v3.csv
   ```
3. Optional — add English translations for recent messages:
   ```bash
   pip install deep-translator
   python translate_output.py -i output/full_history_v3.csv -o output/full_history_v3_en.csv
   ```
4. Google Sheets → **File → Import → Upload** the CSV
5. **Share** → Anyone with the link → Viewer
6. In the dashboard **Google Sheets** tab, paste your sheet URL (edit links work — auto-converted to CSV export)

### Troubleshooting: "Live" but 0 messages

- Use a **CSV export URL**, not just an HTML page. The dashboard auto-converts `/edit` links to `/export?format=csv`.
- Ensure columns include `msg_id`, `date`, `sentiment_label`.
- Open the URL in a browser — you should see plain CSV text, not a login page.

## Google Sheets — auto-append (Path B)

### One-time Google Cloud setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → enable **Google Sheets API**
3. **IAM & Admin → Service Accounts** → Create service account
4. Create a JSON key → save to e.g. `~/.config/telegram-sentiment/credentials.json`
5. Create a Google Sheet → copy the ID from the URL:
   `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`
6. **Share the sheet** with the service account email (`...@...gserviceaccount.com`) as **Editor**

### Configure

```bash
cp .env.example .env
# Edit .env:
#   GOOGLE_SHEET_ID=your_sheet_id
#   GOOGLE_CREDENTIALS_PATH=~/.config/telegram-sentiment/credentials.json
```

### Run with auto-sync

```bash
python telegram_sentiment.py \
  -i exports/my_chat/result.json \
  --lang ko \
  --push-sheets
```

Creates/updates two tabs:

| Tab | Contents |
|-----|----------|
| `Messages` | One row per message (deduped by `msg_id` on re-run) |
| `WeeklySummary` | Per-week aggregates: counts, % pos/neg/neu, avg score, top complaints |

Re-exporting the same chat and re-running **will not duplicate** messages already in the sheet.

## Charting in Google Sheets

On the `WeeklySummary` tab:

1. Insert → Chart
2. X-axis: `week_start`
3. Series: `pct_neg` or `avg_sentiment_score`
4. Filter by `chat_name` if you track multiple chats

## Models

| Language | Default model | Best for |
|----------|---------------|----------|
| Korean (`--lang ko`) | `monologg/koelectra-base-finetuned-nsmc` | **Telegram community chat** (informal Korean) |
| Korean legacy (`--model finbert`) | `snunlp/KR-FinBert-SC` | Financial news / earnings text only |
| English (`--lang en`) | `distilbert-base-uncased-finetuned-sst-2-english` | English chats |

### Why FinBert was inaccurate for Telegram

The original Korean model (KR-FinBert-SC) is trained on **formal financial text**. It labeled ~96% of a crypto community chat as "neutral" because informal complaints ("답답해요", "찝찝합니다") don't look like financial statements to that model. Only explicit loss language ("손실", "하락") scored negative.

The default model is now **KoELECTRA-NSMC**, trained on informal Naver movie reviews — much closer to Telegram banter. Short messages (&lt;8 chars) and low-confidence scores are bucketed as neutral.

### Calibrate before a long run

Compare old vs new model on 200 sample messages (~2 min after models are cached):

```bash
python calibrate_models.py -i "/path/to/result.json" --samples 200
```

### Re-run with the improved model

```bash
python telegram_sentiment.py -i "/path/to/result.json" --lang ko -o full_history_v2.csv
```

Use `--model finbert` only if you want the old financial model for comparison.

## Dashboard features

- **Trends chart**: Positive / Negative / Neutral % with **Net sentiment** overlay (toggle lines via legend)
- **Monthly labels** include year (e.g. `Jan 2021`)
- **English toggle**: live-translates complaint keywords; shows `text_en` from CSV for messages when available
- **Portfolio aesthetic**: muted sage/rose chart colors matching dark charcoal UI

## Project layout

```
telegram-sentiment-tracker/
  Open Dashboard.command  # double-click to run locally
  server.py               # Flask server (local + Render)
  dashboard/              # SentimentTrack web UI
  telegram_sentiment.py   # main analysis CLI
  refresh_keywords.py     # recompute complaint keywords on CSV
  translate_output.py     # add text_en column
  redact_for_demo.py      # optional: pseudonymize before public demo
  calibrate_models.py     # compare FinBert vs NSMC
  sheets_sync.py          # Google Sheets auto-append
  docs/                   # deploy + portfolio guides
  portfolio/              # resume iframe snippet
  exports/                # Telegram JSON exports (gitignored)
  output/                 # latest CSV output (gitignored)
  archive/                # old Streamlit app + superseded CSVs
  requirements.txt        # full analysis stack
  requirements-dashboard.txt  # Render deploy only
  render.yaml / Procfile
```

## Portfolio demo hosting (Render.com)

**Full guides:** [docs/SHEETS_PUBLISH.md](docs/SHEETS_PUBLISH.md) · [docs/DEPLOY.md](docs/DEPLOY.md) · [portfolio/resume-embed-snippet.html](portfolio/resume-embed-snippet.html)

Host the dashboard for your resume site (iframe embed on a static portfolio page):

### 1. Redact usernames before publishing

```bash
python redact_for_demo.py -i output/full_history_v4.csv --dry-run   # spot-check quotes
python redact_for_demo.py -i output/full_history_v4.csv -o output/demo_public.csv
```

Import `output/demo_public.csv` into a **separate** Google Sheet (view-only). Never upload the raw CSV.

### 2. Deploy dashboard only (no ML on server)

On [Render.com](https://render.com), create a **Web Service**:

- **Build:** `pip install -r requirements-dashboard.txt`
- **Start:** `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120`
- **Environment variables** (see `.env.example`):
  - `PORTFOLIO_MODE=1`
  - `DEMO_SHEET_URL` — export URL of your redacted sheet (server-only, not shown in UI)
  - `GITHUB_REPO_URL` — link on the Get the tool page
  - `CONTACT_EMAIL` — optional

### 3. Embed on your resume site

```html
<iframe
  src="https://your-app.onrender.com?embed=1"
  title="SentimentTrack demo"
  width="100%"
  height="920"
  loading="lazy"
  style="border:0;border-radius:12px;background:#0F0F12"
></iframe>
```

Portfolio mode auto-loads redacted data via `/api/demo`. The **Get the tool** sidebar page explains how others can run analysis locally or drop a pre-processed CSV (parsed in-browser, free).
