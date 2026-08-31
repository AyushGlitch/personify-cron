#!/bin/bash
# Install macOS reminders at 11:00 AM, 2:00 PM, and 3:30 PM (local time).

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
REMIND_SCRIPT="$REPO/scripts/remind.sh"
PLIST="$HOME/Library/LaunchAgents/com.personify.reminder.plist"

chmod +x "$REMIND_SCRIPT"
mkdir -p "$HOME/Library/LaunchAgents"

launchctl bootout "gui/$(id -u)/com.personify.reminder" 2>/dev/null || \
  launchctl unload "$PLIST" 2>/dev/null || true

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.personify.reminder</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$REMIND_SCRIPT</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
    <dict>
      <key>Hour</key><integer>11</integer>
      <key>Minute</key><integer>0</integer>
    </dict>
    <dict>
      <key>Hour</key><integer>14</integer>
      <key>Minute</key><integer>0</integer>
    </dict>
    <dict>
      <key>Hour</key><integer>15</integer>
      <key>Minute</key><integer>30</integer>
    </dict>
    <dict>
      <key>Hour</key><integer>15</integer>
      <key>Minute</key><integer>45</integer>
    </dict>
  </array>
  <key>StandardOutPath</key>
  <string>/tmp/personify-reminder.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/personify-reminder.err</string>
</dict>
</plist>
EOF

launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || launchctl load "$PLIST"

echo "Installed reminders for 11:00 AM, 2:00 PM, and 3:30 PM (local time)."
echo "Plist: $PLIST"
echo ""
echo "Test now: $REMIND_SCRIPT"
echo "Uninstall: $REPO/scripts/uninstall-reminders.sh"
