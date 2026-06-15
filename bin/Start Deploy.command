#!/bin/bash
# Purpose: Walk through deploy checklist — opens Google Sheets, Render, DEPLOY.md, and demo CSV.
# Usage:   Double-click when ready to publish the portfolio demo after pushing to GitHub.
cd "$(dirname "$0")/.."

CSV="output/synthetic_demo.csv"

echo "============================================"
echo "  SentimentTrack — Deploy checklist"
echo "============================================"
echo ""
echo "1. Push to GitHub (if not done)"
echo "   → Double-click: bin/Push to GitHub.command"
echo ""
echo "2. Upload synthetic demo to Google Sheets"
echo "   → File → Import → Upload → $CSV"
echo "   → Share: Anyone with link → Viewer"
echo "   → Copy sheet URL for DEMO_SHEET_URL"
echo ""
echo "3. Deploy on Render"
echo "   → New → Blueprint → connect this repo"
echo "   → Set DEMO_SHEET_URL, GITHUB_REPO_URL, CONTACT_EMAIL"
echo ""
echo "4. Resume site embed"
echo "   → portfolio/resume-embed-snippet.html"
echo "   → Replace YOUR-APP.onrender.com with your Render URL"
echo ""

if [ -f "$CSV" ]; then
  echo "Opening CSV location in Finder…"
  open -R "$CSV"
else
  echo "WARNING: $CSV not found. Run: python scripts/generate_synthetic_demo.py"
fi

open "https://sheets.google.com/create"
open "https://dashboard.render.com/"
open "file://$(pwd)/docs/DEPLOY.md"

read -p "Press Enter to close..."
