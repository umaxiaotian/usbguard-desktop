#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ -x .venv/bin/pip ]; then
    .venv/bin/pip uninstall -y usbguard-desktop
fi
printf '%s\n' 'System USBGuard configuration was not changed.'
