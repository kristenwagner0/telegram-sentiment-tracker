# Deploy SentimentTrack for portfolio embed

## Prerequisites

- [ ] Synthetic demo sheet ready — see [docs/SYNTHETIC_DEMO.md](SYNTHETIC_DEMO.md)
- [ ] Project pushed to a GitHub repository

## Deploy on Render (free tier)

### Option A — Blueprint (recommended)

1. Push this repo to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com) → **New → Blueprint**
3. Connect the repo → Render reads [`render.yaml`](render.yaml)
4. When prompted, set secret env vars:
   - `DEMO_SHEET_URL` — synthetic demo sheet URL (see SYNTHETIC_DEMO.md)
   - `GITHUB_REPO_URL` — e.g. `https://github.com/yourusername/telegram-sentiment-tracker`
   - `CONTACT_EMAIL` — optional, shown on Get the tool page
5. Click **Apply** → wait for deploy (~2 min)

### Option B — Manual Web Service

| Setting | Value |
|---|---|
| **Runtime** | Python 3 |
| **Build command** | `pip install -r requirements-dashboard.txt` |
| **Start command** | `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 120` |

**Environment variables:**

| Key | Value |
|---|---|
| `PORTFOLIO_MODE` | `1` |
| `DEMO_SHEET_URL` | Synthetic demo Google Sheet URL |
| `GITHUB_REPO_URL` | Your GitHub repo URL |
| `CONTACT_EMAIL` | Your email (optional) |

## Verify deployment

1. Open `https://YOUR-SERVICE.onrender.com`
2. Loading overlay → synthetic Helix Protocol demo loads
3. Banner: **Illustrative demo** · GitHub link visible
4. Trends defaults to **Weekly · 1 year**
5. Complaints → sample themes from fictional negative messages

## Embed on your resume site

Copy [`portfolio/resume-embed-snippet.html`](../portfolio/resume-embed-snippet.html) into your static site. Replace `YOUR-APP.onrender.com` with your Render URL.

## Cold starts

Render free tier sleeps after ~15 minutes idle. First visit after sleep may take 30–60 seconds. Mention this on your portfolio page or link **Open full screen** so visitors can retry.

## Local test with portfolio mode

```bash
export PORTFOLIO_MODE=1
export DEMO_SHEET_URL="https://docs.google.com/spreadsheets/d/YOUR_ID/edit"
export GITHUB_REPO_URL="https://github.com/yourusername/telegram-sentiment-tracker"
python server.py
```

Set `HOST=127.0.0.1` (default) and open http://127.0.0.1:8080
