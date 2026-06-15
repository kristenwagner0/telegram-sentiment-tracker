# Portfolio talking points

<!-- Purpose: Demo script, mobile notes, and talking points for resume interviews. -->

## One-liner

> I built a community sentiment intelligence tool that turns raw Telegram chat exports into weekly mood trends, complaint themes, and escalation signals — so community teams can spot issues before they blow up.

## What to show in the dashboard

1. **Dashboard** — summary cards, real complaint quotes, recent messages
2. **Trends** — sentiment over time with time-range pills (3 months, 1 year, etc.)
3. **Complaints** — weekly themes and most active voices (fictional members)
4. **English toggle** — live translation for non-Korean readers
5. **Get the tool** (hosted demo) — how to run locally or load your own CSV

## Live demo script (2 minutes)

1. Open the hosted demo (or double-click `bin/Open Dashboard.command` locally)
2. "This is an illustrative demo — ~135k synthetic messages for a fictional Helix Protocol community. Real analysis runs locally from GitHub."
3. Show Trends → weekly view at 6 months, toggle net sentiment line
4. Complaints → real negative message quotes for a spike week
5. "Sentiment runs locally with HuggingFace KoELECTRA; the website is the viewer"

## Deploy for a resume link

See [DEPLOY.md](DEPLOY.md) for full steps:

1. Generate synthetic CSV → import to Google Sheet → set `DEMO_SHEET_URL` (see SYNTHETIC_DEMO.md)
2. Deploy `server.py` on Render (free tier) with `PORTFOLIO_MODE=1`
3. iframe embed on your static resume site with `?embed=1`

## Mobile

- **Bottom tab bar** appears at viewports ≤900px (sidebar hidden). Tabs mirror visible sidebar items: Dashboard, Trends, Complaints, Get the tool, Settings in portfolio mode.
- **Default landing** stays Dashboard on mobile; use bottom tabs to reach Trends and Complaints.
- **Deep link:** append `&panel=trends` (or `complaints`, `gettool`, etc.) to open a specific panel after load, e.g. `?embed=1&panel=trends`.
- **Resume embed snippet** ([`portfolio/resume-embed-snippet.html`](../portfolio/resume-embed-snippet.html)): on screens ≤768px, iframe height drops to 680px and **Open full demo** + **GitHub** buttons appear above the iframe for thumb-friendly access.

## Tech stack

| Layer | Choice |
|-------|--------|
| NLP | HuggingFace KoELECTRA-NSMC (Korean) / DistilBERT (English) |
| Keywords | scikit-learn TF-IDF on negative messages |
| Dashboard | HTML/CSS/JS + Chart.js |
| Server | Flask (Sheets proxy + translation API) |
| Data | Google Sheets CSV or client-side CSV upload |
