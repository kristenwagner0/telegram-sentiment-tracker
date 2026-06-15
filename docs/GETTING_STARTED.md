# Getting Started — run SentimentTrack on your own machine

<!-- Purpose: Complete walkthrough for downloading, installing, exporting Telegram data, and running analysis + dashboard. -->

This guide assumes **no prior experience** with the project. Follow it top to bottom the first time. Total setup time: **30–60 minutes** (mostly waiting on Telegram export and model download).

---

## What you are installing

SentimentTrack has two parts:

| Part | What it does | Runs where |
|------|----------------|------------|
| **Analysis CLI** (`telegram_sentiment.py`) | Reads a Telegram export, scores sentiment with AI, writes a CSV | Your computer (offline) |
| **Dashboard** (`server.py` + `dashboard/`) | Charts, trends, complaints, message search | Browser at `http://127.0.0.1:8080` |

**Important:** The HuggingFace sentiment models run **locally on your machine**. They are **not** uploaded to any server. Your chat data never leaves your computer unless you explicitly publish a CSV to Google Sheets.

---

## What you need before you start

### Hardware & software

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **OS** | macOS, Windows 10+, or Linux | macOS or Linux |
| **Python** | 3.9 or newer | 3.11 |
| **RAM** | 8 GB | 16 GB |
| **Free disk** | 3 GB | 5 GB |
| **Internet** | First run only (model download) | — |

Check Python:

```bash
python3 --version
# or on Windows: py --version
```

If Python is missing:

- **macOS:** install from [python.org](https://www.python.org/downloads/) or `brew install python`
- **Windows:** install from [python.org](https://www.python.org/downloads/) — check **“Add Python to PATH”**
- **Linux:** `sudo apt install python3 python3-venv python3-pip`

### Accounts (optional)

- **Telegram Desktop** — required to export chat history (mobile app cannot export JSON)
- **Google account** — only if you want to load data via Google Sheets instead of uploading a CSV

---

## Step 1 — Download the project from GitHub

Repository: **https://github.com/kristenwagner0/telegram-sentiment-tracker**

### Option A — Git clone (recommended)

If you have [Git](https://git-scm.com/downloads) installed:

```bash
cd ~/Documents   # or wherever you keep projects
git clone https://github.com/kristenwagner0/telegram-sentiment-tracker.git
cd telegram-sentiment-tracker
```

To update later:

```bash
cd telegram-sentiment-tracker
git pull
```

### Option B — Download ZIP (no Git required)

1. Open **https://github.com/kristenwagner0/telegram-sentiment-tracker**
2. Click the green **Code** button
3. Click **Download ZIP**
4. Unzip the file (e.g. to `~/Documents/telegram-sentiment-tracker`)
5. Open Terminal (macOS/Linux) or PowerShell (Windows) and go into that folder:

```bash
cd ~/Documents/telegram-sentiment-tracker
```

### Option C — GitHub Desktop

1. Install [GitHub Desktop](https://desktop.github.com/)
2. **File → Clone repository → URL**
3. Paste: `https://github.com/kristenwagner0/telegram-sentiment-tracker.git`
4. Choose a local path → **Clone**

### Verify the download

You should see these folders and files:

```
telegram-sentiment-tracker/
  bin/                      ← macOS launchers
  dashboard/                ← web UI
  docs/                     ← guides (you are here)
  scripts/                  ← optional utilities
  server.py                 ← dashboard server
  telegram_sentiment.py     ← main analysis script
  requirements.txt          ← full install (analysis + dashboard)
  requirements-dashboard.txt ← dashboard-only install
```

---

## Step 2 — Create a Python virtual environment

Always use a virtual environment so dependencies do not conflict with other projects.

**macOS / Linux:**

```bash
cd telegram-sentiment-tracker
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` at the start of your terminal prompt.

**Windows (PowerShell):**

```powershell
cd telegram-sentiment-tracker
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If Windows blocks the script: run PowerShell as Administrator once and execute `Set-ExecutionPolicy RemoteSigned`, then try again.

---

## Step 3 — Install dependencies

Choose **one** path depending on what you want to do.

### Path 1 — Full install (analysis + dashboard) ← most users

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs PyTorch, HuggingFace Transformers, Flask, and everything needed to **analyze Telegram exports** and **view the dashboard**.

First analysis run downloads a sentiment model (~250–500 MB) to `~/.cache/huggingface/`.

**Time:** 5–15 minutes depending on internet speed.

### Path 2 — Dashboard only (view CSV / Google Sheets, no ML)

If you only want to explore the UI with data someone else already analyzed:

```bash
pip install --upgrade pip
pip install -r requirements-dashboard.txt
```

You **cannot** run `telegram_sentiment.py` with this install — there is no PyTorch. You can still open the dashboard and load an existing CSV.

---

## Step 4 — Export your Telegram chat

You must use **Telegram Desktop**. The phone app cannot export JSON.

### 4.1 Install Telegram Desktop

Download from **https://desktop.telegram.org/** and sign in with your account.

### 4.2 Export chat history

1. Open **Telegram Desktop**
2. Open the **group or channel** you want to analyze
3. Click the **⋮** menu (top right on macOS, or chat header menu on Windows)
4. Choose **Export chat history**
5. Configure the export:

| Setting | Recommended value | Why |
|---------|---------------------|-----|
| **Format** | **JSON** | Required — the tool reads `result.json` |
| **Time range** | All time (or pick a range) | Larger exports take longer |
| **Media** | Uncheck photos/videos/files | Faster export, smaller file — text is all you need |

6. Click **Export**
7. Choose a save location (e.g. `~/Downloads/Telegram Export/`)
8. Wait — large community chats can take **10–30+ minutes**

### 4.3 What the export looks like

Telegram creates a folder like:

```
Telegram Export/
  ChatExport_2026-06-15/
    result.json          ← this is the file you need
    (optional media subfolders if you included media)
```

The file you need is always named **`result.json`**.

### 4.4 Copy the export into the project

```bash
# Create a folder for your chat inside exports/
mkdir -p exports/my_community

# Copy result.json (adjust the source path to your export)
cp ~/Downloads/Telegram\ Export/ChatExport_*/result.json exports/my_community/result.json
```

Or drag the entire export folder into `exports/` using Finder / File Explorer and rename it to something memorable, e.g. `exports/stacks_community/`.

**Privacy note:** Everything in `exports/` is **gitignored** — it will never be uploaded to GitHub if you commit changes.

### 4.5 Quick sanity check (optional)

```bash
python telegram_sentiment.py -i exports/my_community/result.json --dry-run
```

This parses the JSON and prints message counts **without** downloading the AI model. If you see errors here, fix the export path before continuing.

---

## Step 5 — Run sentiment analysis

Activate your virtual environment if you closed Terminal:

```bash
cd telegram-sentiment-tracker
source .venv/bin/activate          # macOS/Linux
# .\.venv\Scripts\Activate.ps1     # Windows
```

### Korean community chat (default)

```bash
python telegram_sentiment.py -i exports/my_community/result.json --lang ko
```

### English community chat

```bash
python telegram_sentiment.py -i exports/my_community/result.json --lang en
```

### What happens during the run

1. Parses all messages from `result.json`
2. Downloads the sentiment model on first run (one-time)
3. Scores each message as **positive**, **negative**, or **neutral**
4. Computes weekly complaint keywords (TF-IDF on negative messages)
5. Writes a CSV to `output/`

Progress bar shows batch processing. A 100k-message chat typically takes **15–45 minutes** on a modern laptop.

### Output files

| File | When created |
|------|----------------|
| `output/full_history.csv` | Export spans multiple weeks |
| `output/week_YYYY-MM-DD.csv` | Export covers a single week |

### Useful flags

```bash
# Custom output name
python telegram_sentiment.py -i exports/my_community/result.json -o my_chat_v1.csv

# Reduce memory use if you get out-of-memory errors
python telegram_sentiment.py -i exports/my_community/result.json --batch-size 8

# Compare models before a long run (~2 min)
python scripts/calibrate_models.py -i exports/my_community/result.json --samples 200
```

### Optional post-processing

```bash
# Refresh complaint keywords without re-running ML
python scripts/refresh_keywords.py -i output/full_history.csv -o output/full_history_refreshed.csv

# Add English translations for Korean messages (slow — uses Google Translate)
python scripts/translate_output.py -i output/full_history.csv -o output/full_history_en.csv
```

---

## Step 6 — Open the dashboard

The dashboard turns your CSV into charts: sentiment trends, weekly complaints, message search, and more.

### macOS — double-click launcher

1. In Finder, open the `telegram-sentiment-tracker` folder
2. Open the `bin` folder
3. Double-click **`Open Dashboard.command`**
4. Your browser opens **http://127.0.0.1:8080**

If macOS blocks it: right-click → **Open** → **Open** (one-time security approval).

**Note:** The launcher starts in **portfolio demo mode** (synthetic sample data). To view **your** data, use one of the load methods below.

### All platforms — Terminal

**View your own analyzed data (recommended):**

```bash
cd telegram-sentiment-tracker
source .venv/bin/activate
python server.py
```

Then open **http://127.0.0.1:8080** in your browser.

Keep the Terminal window open while using the dashboard. Press **Ctrl+C** to stop the server.

---

## Step 7 — Load your CSV into the dashboard

Three ways to get your analyzed data on screen:

### Method A — Upload CSV in the browser (easiest, stays local)

1. Open the dashboard
2. Sidebar → **Upload export** (or use the CSV drop zone on **Get the tool** in portfolio mode)
3. Drop your `output/full_history.csv` (or drag-select it)
4. Data is parsed **entirely in your browser** — nothing is sent to a server

### Method B — Google Sheets (good for sharing with a team)

1. Open [Google Sheets](https://sheets.google.com) → **Blank spreadsheet**
2. **File → Import → Upload** → select your CSV
3. **Share → General access → Anyone with the link → Viewer**
4. Copy the sheet URL
5. In the dashboard sidebar → **Google Sheets**
6. Paste the URL → **Connect**

The dashboard converts `/edit` links to CSV export URLs automatically.

### Method C — Auto-sync on analysis (advanced)

Set up a Google Cloud service account and `.env` file, then run:

```bash
cp .env.example .env
# Edit .env with GOOGLE_SHEET_ID and GOOGLE_CREDENTIALS_PATH

python telegram_sentiment.py \
  -i exports/my_community/result.json \
  --lang ko \
  --push-sheets
```

Full service-account setup: see [Google Sheets auto-append in README](../README.md#google-sheets--auto-append-path-b).

---

## Step 8 — Explore the dashboard

| Tab | What to look at |
|-----|-----------------|
| **Dashboard** | Summary stats, top complaints this week, sentiment breakdown |
| **Trends** | Sentiment over time — toggle lines, change range (3 months, 1 year, all) |
| **Complaints** | Weekly negative themes and repeat voices |
| **Messages** | Search and filter individual messages |
| **Settings** | Switch display language (한국어 / English) |

**English mode:** translates complaint keywords live (requires the dashboard server running for API translation).

---

## End-to-end cheat sheet

Copy-paste workflow after initial setup:

```bash
# 1. Go to project
cd ~/Documents/telegram-sentiment-tracker
source .venv/bin/activate

# 2. Analyze (after placing result.json in exports/my_community/)
python telegram_sentiment.py -i exports/my_community/result.json --lang ko

# 3. Start dashboard
python server.py
# Open http://127.0.0.1:8080 → Upload export → drop output/full_history.csv
```

---

## Troubleshooting

### `fatal: not a git repository`

You are in the wrong folder. Make sure you `cd` into `telegram-sentiment-tracker`, not a parent folder like `Documents`.

### `python3: command not found`

Install Python 3.9+ (see [What you need](#what-you-need-before-you-start)). On Windows try `py` instead of `python3`.

### `ModuleNotFoundError: No module named 'torch'`

You skipped the full install. Run:

```bash
pip install -r requirements.txt
```

Or you are not in the virtual environment — run `source .venv/bin/activate` first.

### macOS blocks `Open Dashboard.command`

Right-click the file → **Open** → confirm **Open**. This is a one-time Gatekeeper approval.

### Port 8080 already in use

Another server is running. Stop it:

```bash
# macOS/Linux
kill $(lsof -t -i:8080)

# Windows PowerShell
Get-NetTCPConnection -LocalPort 8080 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

Or start on a different port:

```bash
PORT=9090 python server.py
# Open http://127.0.0.1:9090
```

### Analysis runs out of memory

```bash
python telegram_sentiment.py -i exports/my_community/result.json --batch-size 8
# or --batch-size 4 on 8 GB RAM machines
```

### Dashboard shows 0 messages after connecting Google Sheets

- Sheet must be shared **Anyone with the link → Viewer**
- Open the sheet URL in a browser — you should see raw CSV text, not a login page
- CSV must include columns: `msg_id`, `date`, `sentiment_label`

### Sentiment looks wrong (everything neutral)

The default Korean model (`KoELECTRA-NSMC`) works best for informal chat. Run calibration to compare:

```bash
python scripts/calibrate_models.py -i exports/my_community/result.json --samples 200
```

Do **not** use `--model finbert` unless your chat is formal financial news.

### Telegram export is huge / stuck

- Re-export with **media unchecked**
- Export a shorter date range first to test the pipeline
- Ensure Telegram Desktop is updated to the latest version

### Model download fails (corporate firewall / offline)

Models cache to `~/.cache/huggingface/`. On a machine with internet, run a small dry analysis first, then copy that cache folder to the offline machine.

---

## Privacy & data handling

| Data | Where it goes |
|------|----------------|
| Telegram `result.json` | Stays in `exports/` on your machine (gitignored) |
| Sentiment model | Downloaded once to `~/.cache/huggingface/` |
| Analysis CSV | Written to `output/` on your machine (gitignored) |
| Dashboard CSV upload | Parsed in your **browser** — not uploaded |
| Google Sheets | Only if **you** import and share a sheet |
| Render hosted demo | Uses **synthetic fictional data** only — not your export |

**Never** commit `exports/` or `output/` to GitHub. They are listed in `.gitignore`.

---

## Next steps

| Goal | Guide |
|------|-------|
| Publish a public portfolio demo | [SYNTHETIC_DEMO.md](SYNTHETIC_DEMO.md) |
| Deploy dashboard to Render | [DEPLOY.md](DEPLOY.md) |
| Interview talking points | [PORTFOLIO.md](PORTFOLIO.md) |
| Redact real data before sharing | [SHEETS_PUBLISH.md](SHEETS_PUBLISH.md) |
| All CLI flags and models | [README.md](../README.md) |

---

## Getting help

- **Bug or feature request:** open an issue at https://github.com/kristenwagner0/telegram-sentiment-tracker/issues
- **Check the synthetic demo works:** double-click `bin/Open Dashboard.command` — if the demo loads, your install is fine; the issue is likely export path or CSV format
