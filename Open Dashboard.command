#!/bin/bash
cd "$(dirname "$0")"

PYTHON=".venv/bin/python"

if [ ! -f "$PYTHON" ]; then
  osascript -e 'display alert "Setup needed" message "Open Terminal in the telegram-sentiment-tracker folder and run:\n\npython3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt"'
  echo ""
  echo "ERROR: Virtual environment not found."
  echo "Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  read -p "Press Enter to close..."
  exit 1
fi

"$PYTHON" -m pip install -q flask requests deep-translator 2>/dev/null

# Restart server so code/API updates (e.g. /api/translate) are picked up
if lsof -i :8080 >/dev/null 2>&1; then
  echo "Stopping previous dashboard server…"
  kill $(lsof -t -i:8080) 2>/dev/null
  sleep 1
fi

export PORTFOLIO_MODE=1
export GITHUB_REPO_URL="${GITHUB_REPO_URL:-https://github.com/kristenwagner0/telegram-sentiment-tracker}"

echo "============================================"
echo "  SentimentTrack Dashboard"
echo "  http://127.0.0.1:8080"
export PORTFOLIO_MODE=1
export GITHUB_REPO_URL="${GITHUB_REPO_URL:-https://github.com/kristenwagner0/telegram-sentiment-tracker}"

echo "============================================"
echo ""
echo "KEEP THIS WINDOW OPEN while using the dashboard."
echo "To stop: press Control+C in this window."
echo ""

open "http://127.0.0.1:8080"
exec "$PYTHON" server.py
