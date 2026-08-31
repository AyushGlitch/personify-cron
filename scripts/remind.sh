#!/bin/bash
# macOS notification reminder to run Personify automation manually.

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

osascript <<EOF
display notification "Run: python log_health.py --use-auth --headed" with title "Personify Health" subtitle "Log steps & sleep now" sound name "Glass"
EOF
