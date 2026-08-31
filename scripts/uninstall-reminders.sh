#!/bin/bash
# Remove Personify reminder launchd job.

PLIST="$HOME/Library/LaunchAgents/com.personify.reminder.plist"

launchctl bootout "gui/$(id -u)/com.personify.reminder" 2>/dev/null || \
  launchctl unload "$PLIST" 2>/dev/null || true

rm -f "$PLIST"

echo "Personify reminders uninstalled."
