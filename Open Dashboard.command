#!/bin/bash
cd "$(dirname "$0")"

PYTHON=".venv/bin/python"

if [ ! -f "$PYTHON" ]; then
  osascript -e 'display alert "Setup needed" message "Open Terminal and run: python3 -m venv .venv && pip install -r requirements-dashboard.txt"'
  read -p "Press Enter to close..."
  exit 1
fi

"$PYTHON" -m pip install -q flask requests deep-translator 2>/dev/null

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
echo "============================================"
echo ""
echo "Starting server… (demo load may take 10–20 sec)"
echo "KEEP THIS WINDOW OPEN. Control+C to stop."
echo ""

"$PYTHON" server.py &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null' EXIT INT TERM

READY=0
for _ in $(seq 1 60); do
  if curl -s -o /dev/null --connect-timeout 1 http://127.0.0.1:8080/ 2>/dev/null; then
    READY=1
    break
  fi
  sleep 0.25
done

if [ "$READY" -eq 1 ]; then
  open "http://127.0.0.1:8080"
  echo "Browser opened."
else
  echo "ERROR: Server did not start. Run: .venv/bin/python server.py"
  read -p "Press Enter to close..."
  exit 1
fi

wait "$SERVER_PID"
