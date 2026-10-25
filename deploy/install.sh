#!/bin/sh
set -eu
cd /home/zoli/mini-pi
mkdir -p instance
chmod 700 instance
python3 -m venv .venv
.venv/bin/pip install --disable-pip-version-check -r requirements.txt
sudo install -m 644 deploy/mini-pi.service /etc/systemd/system/mini-pi.service
mkdir -p "$HOME/.config/systemd/user" "$HOME/.config/labwc"
install -m 644 deploy/mini-pi-kiosk.service "$HOME/.config/systemd/user/mini-pi-kiosk.service"
autostart="$HOME/.config/labwc/autostart"
if ! grep -q 'MINI_PI_KIOSK_START' "$autostart" 2>/dev/null; then
    if [ -f "$autostart" ]; then cp -p "$autostart" "$autostart.before-mini-pi-$(date +%Y%m%d%H%M%S)"; fi
    cat >> "$autostart" <<'EOF'

# MINI_PI_KIOSK_START
# A dedicated appliance session. Existing autostart lines above are preserved.
systemctl --user import-environment WAYLAND_DISPLAY XDG_RUNTIME_DIR
systemctl --user restart mini-pi-kiosk.service
# MINI_PI_KIOSK_END
EOF
fi
chmod u+x "$autostart"
sudo systemctl daemon-reload
sudo systemctl enable --now mini-pi.service
sudo systemctl restart mini-pi.service
systemctl --user daemon-reload
# Started by labwc after the compositor is ready; do not start it before Wayland at boot.
systemctl --user restart mini-pi-kiosk.service
printf '\nMini PI ready: http://192.168.50.246:8080/admin\n'
