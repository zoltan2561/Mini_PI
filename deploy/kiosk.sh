#!/bin/sh
set -eu
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
# The ILI9486 advertises 0.007 Hz; this mode fixes the black Wayland surface.
wlr-randr --output SPI-1 --custom-mode 480x320@60Hz --on
while ! curl --fail --silent --max-time 3 http://127.0.0.1:8080/health >/dev/null; do sleep 2; done
python3 /home/zoli/mini-pi/tools/configure_browser.py
exec chromium --ozone-platform=wayland --kiosk --no-first-run --noerrdialogs \
  --lang=hu-HU --disable-features=Translate,TranslateUI \
  --disable-session-crashed-bubble --password-store=basic \
  --user-data-dir="$HOME/.config/mini-pi-browser" http://127.0.0.1:8080/
