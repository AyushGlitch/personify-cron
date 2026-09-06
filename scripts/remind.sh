#!/bin/bash
# Daily macOS reminder with option to run Personify automation.

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG="/tmp/personify-reminder.log"
PYTHON="$REPO_DIR/.venv/bin/python"
SCRIPT="$REPO_DIR/log_health.py"
RUN_CMD="cd '$REPO_DIR' && '$PYTHON' '$SCRIPT' --headed"

echo "$(date '+%Y-%m-%d %H:%M:%S') reminder fired" >> "$LOG"

afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || true

CHOICE=$(osascript <<'APPLESCRIPT'
display dialog "Time to log steps & sleep to Personify Health." with title "Personify Health" buttons {"Later", "Run"} default button "Run" with icon note giving up after 300
APPLESCRIPT
)

if echo "$CHOICE" | grep -q "Run"; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') user chose Run" >> "$LOG"
  osascript <<EOF
tell application "Terminal"
  activate
  do script "$RUN_CMD"
end tell
EOF
else
  echo "$(date '+%Y-%m-%d %H:%M:%S') dismissed" >> "$LOG"
fi
