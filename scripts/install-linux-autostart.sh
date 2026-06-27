#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
SERVICE_DIR="$CONFIG_HOME/systemd/user"
AUTOSTART_DIR="$CONFIG_HOME/autostart"
SERVICE_FILE="$SERVICE_DIR/tikflow.service"
DESKTOP_FILE="$AUTOSTART_DIR/tikflow-gui.desktop"

mkdir -p "$SERVICE_DIR" "$AUTOSTART_DIR"

cat > "$SERVICE_FILE" <<SERVICE
[Unit]
Description=TikFlow Flask web GUI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$ROOT_DIR
ExecStart=/usr/bin/env python3 $ROOT_DIR/app.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
SERVICE

cat > "$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=TikFlow GUI
Comment=Open TikFlow web GUI
Exec=$ROOT_DIR/scripts/open-linux-gui.sh
Terminal=false
X-GNOME-Autostart-enabled=true
DESKTOP

chmod +x "$ROOT_DIR/scripts/open-linux-gui.sh"
chmod +x "$DESKTOP_FILE"

systemctl --user daemon-reload
systemctl --user enable --now tikflow.service

cat <<EOF
TikFlow autostart installed.

Service: tikflow.service
URL:     http://localhost:8080
Browser: opens automatically on graphical login

Check status:
  systemctl --user status tikflow.service

View logs:
  journalctl --user -u tikflow.service -f

If you want the server to start at boot before you log in, run:
  sudo loginctl enable-linger "$USER"
EOF
