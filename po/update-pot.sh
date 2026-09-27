#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
xgettext --language=Python --keyword=_ --from-code=UTF-8 \
  --package-name='USB Protection' --package-version=0.1.0 \
  --msgid-bugs-address='https://github.com/umaxiaotian/usbguard-desktop/issues' \
  --output=po/usbguard-desktop.pot $(find src -name '*.py' -print | sort)
