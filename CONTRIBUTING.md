# Contributing

Use Python 3.12 or newer with system PyGObject, GTK4 and Libadwaita 1.5+.
Run `./scripts/install-dev.sh`, then `.venv/bin/ruff check .` and
`.venv/bin/pytest`. Use `dbus-run-session -- xvfb-run -a .venv/bin/pytest`
for the UI smoke test without opening windows on your desktop.

Never exercise real USB allow/block operations in automated tests. Never start
an unconfigured USBGuard daemon on a development workstation. Keep all mock
policies in pytest's temporary directories. Use a disposable VM for installation
and first-run integration testing, with non-USB input and recovery access.

The protocol belongs in `usbguard/client.py`; UI and agent share that client.
Do not implement a second policy engine. Rule parsing in Python is only for
presentation. Bootstrap syntax validation must use USBGuard's own parser.
Changes to privileged code require tests for failure paths and no-clobber writes.

User-facing Python text must use `usb_protection.i18n._`. Update all required
catalogs in `po/`, run `./po/update-pot.sh`, and preserve named placeholders
such as `{name}`. Desktop and AppStream strings have their localized forms in
the source metadata. Run `msgfmt --check --check-format po/*.po` before review.

Submit focused conventional commits. Do not include tokens, device serial
numbers, personal policies or authentication material in issues or screenshots.

The project is GPL-3.0-or-later. Contributions use the same license; AppStream
metadata is CC0-1.0. No contributor license agreement is required.
