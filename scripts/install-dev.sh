#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -e . pytest ruff build
printf '%s\n' 'Run .venv/bin/usb-protection as your ordinary desktop user.' \
    'System bootstrap integration requires the Debian package.'
