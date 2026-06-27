#!/usr/bin/env bash
set -euo pipefail

CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
SERVICE_FILE="$CONFIG_HOME/systemd/user/tikflow.service"
DESKTOP_FILE="$CONFIG_HOME/autostart/tikflow-gui.desktop"

systemctl --user disable --now tikflow.service 2>/dev/null || true
rm -f "$SERVICE_FILE" "$DESKTOP_FILE"
systemctl --user daemon-reload

echo "TikFlow autostart removed."
