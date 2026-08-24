#!/bin/bash
set -euo pipefail

LABEL="dev.cyberai.8bit-buddy.sit-stand"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/8bit-buddy/config.toml"
EXECUTABLE="$(command -v 8bit-sit-stand || true)"

if [[ -z "$EXECUTABLE" ]]; then
  echo "8bit-sit-stand is not on PATH. Install the project first: python3 -m pip install ." >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$EXECUTABLE</string>
    <string>--config</string>
    <string>$CONFIG</string>
    <string>--timezone</string>
    <string>Australia/Melbourne</string>
  </array>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>ProcessType</key>
  <string>Background</string>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/8bitBuddy-sit-stand.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/8bitBuddy-sit-stand.error.log</string>
</dict>
</plist>
EOF

DOMAIN="gui/$(id -u)"
launchctl bootout "$DOMAIN" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "$DOMAIN" "$PLIST"

echo "Installed $PLIST"
echo "Schedule: Monday-Friday, 09:00-17:30 Australia/Melbourne"

if [[ "${1:-}" == "--start-now" ]]; then
  launchctl kickstart -k "$DOMAIN/$LABEL"
  echo "Started sit/stand cycle now."
fi
