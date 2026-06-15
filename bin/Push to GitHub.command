#!/bin/bash
# Purpose: Push local commits to GitHub (origin/main) with interactive credential prompt.
# Usage:   Double-click after committing. Opens the repo page on success.
cd "$(dirname "$0")/.."

echo "============================================"
echo "  Push SentimentTrack to GitHub"
echo "  $(pwd)"
echo "============================================"
echo ""

if [ ! -d .git ]; then
  osascript -e 'display alert "Not a git repo" message "This script must run from telegram-sentiment-tracker folder."'
  read -p "Press Enter to close..."
  exit 1
fi

git status -sb
echo ""

AHEAD=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo "unknown")
if [ "$AHEAD" = "0" ]; then
  echo "Nothing to push — already up to date with origin/main."
  open "https://github.com/kristenwagner0/telegram-sentiment-tracker"
  read -p "Press Enter to close..."
  exit 0
fi

echo "Pushing to origin/main…"
echo "(GitHub may ask for your username and Personal Access Token.)"
echo ""

if git push -u origin main; then
  echo ""
  echo "Push succeeded."
  open "https://github.com/kristenwagner0/telegram-sentiment-tracker"
else
  echo ""
  echo "Push failed. Create a token at: https://github.com/settings/tokens"
  echo "Use the token as your password when prompted."
fi

read -p "Press Enter to close..."
