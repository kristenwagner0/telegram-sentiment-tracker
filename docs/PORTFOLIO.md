# Portfolio talking points

## One-liner

> I built a community sentiment intelligence tool that turns raw Telegram chat exports into weekly mood trends, complaint themes, and escalation signals — so community teams can spot issues before they blow up.

## What to show in the dashboard

1. **Dashboard** — summary cards, real complaint quotes, recent messages
2. **Trends** — sentiment over time with time-range pills (3 months, 1 year, etc.)
3. **Complaints** — weekly themes, most active voices (password-protected names)
4. **English toggle** — live translation for non-Korean readers
5. **Get the tool** (hosted demo) — how to run locally or load your own CSV

## Live demo script (2 minutes)

1. Open the hosted demo (or double-click `Open Dashboard.command` locally)
2. "This analyzes a Telegram community — ~135k messages, usernames redacted for the public demo"
3. Show Trends → weekly view at 6 months, toggle net sentiment line
4. Complaints → real negative message quotes for a spike week
5. "Sentiment runs locally with HuggingFace KoELECTRA; the website is the viewer"

## Deploy for a resume link

See [DEPLOY.md](DEPLOY.md) for full steps:

1. Point `DEMO_SHEET_URL` at your existing Google Sheet (or optional redact + upload)
2. Deploy `server.py` on Render (free tier) with `PORTFOLIO_MODE=1`
3. iframe embed on your static resume site with `?embed=1`

## Tech stack

| Layer | Choice |
|-------|--------|
| NLP | HuggingFace KoELECTRA-NSMC (Korean) / DistilBERT (English) |
| Keywords | scikit-learn TF-IDF on negative messages |
| Dashboard | HTML/CSS/JS + Chart.js |
| Server | Flask (Sheets proxy + translation API) |
| Data | Google Sheets CSV or client-side CSV upload |
