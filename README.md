# USB Protection

A simple desktop interface for managing USB device access with USBGuard.

**Development preview — not yet cleared for production installation.** The
application and Debian package are implemented, but Ubuntu's USBGuard dependency
starts protection during package installation, before our first-run wizard.
A single dependent `.deb` cannot prevent that earlier maintainer-script action.
See [installation safety findings](docs/environment.md). Test fresh installation
only in a disposable VM with non-USB input and recovery access.

## Features

- Native GTK4 / Libadwaita interface with real service status.
- Connected device details, Allow Once, Always Allow, and Block.
- Saved rules with confirmation before forgetting a decision.
- Background notifications with working allow actions.
- First-run policy generation using USBGuard's own generator and validator.
- System authentication; no passwords handled by the application.
- Existing policies preserved, including on removal and purge.
- No telemetry, cloud service, independent filtering engine, or root GUI.

## Screenshots

Release screenshots are not published yet. The UI contains Protection,
Connected Devices, a device detail window, and a Rules window. The AppStream
file includes a commented screenshot template; no fabricated screenshots or
nonexistent image URLs are shipped.

## Requirements

- Ubuntu Desktop 24.04 LTS or later; GNOME, Wayland or X11.
- Python 3.12+, GTK 4.12+, Libadwaita 1.5+, PyGObject.
- USBGuard with its D-Bus bridge and rule parser (included in Ubuntu's
  `usbguard` package), systemd, Polkit, and a desktop authentication agent.
- A graphical user session: neither GUI nor agent runs as root.

Development and packaging were verified on Ubuntu 26.04.1. Ubuntu 24.04 is the
compatibility baseline and CI target; a full 24.04 desktop install still needs
manual validation. App Center's ability to open local `.deb` files varies by
Ubuntu version; the supported command-line installation is below.

## Installation

### Ubuntu

When a reviewed release is available, download the latest `.deb` from
[GitHub Releases](https://github.com/umaxiaotian/usbguard-desktop/releases).
Verify the downloaded checksum file in the same directory:

```bash
sha256sum -c SHA256SUMS
sudo apt install ./usbguard-desktop_0.1.0-1_all.deb
```

APT resolves USBGuard and all runtime dependencies automatically. Launch
**USB Protection** from the application menu. Do not use sudo to launch it.

Until the installation safety issue above is resolved, these instructions are
for a disposable test VM or an administrator-reviewed existing installation.
The application's package scripts never start or enable protection, but the
upstream dependency does. Never assume that downloading this preview and
installing it on a USB-dependent workstation is harmless.

To remove the application:

```bash
sudo apt remove usbguard-desktop
```

This does not remove your USBGuard policy or disable the existing system
protection. Log out and back in to end any currently running notification agent cleanly.
USBGuard remains a separately managed package. Do not purge USBGuard itself
unless you intend to remove its configuration.

## First Run

If no policy exists and protection is stopped, the welcome page previews
currently connected devices. Unplug anything you do not trust. Keep your
keyboard and mouse connected, then select **Enable USB Protection** and approve
the system authentication prompt. Devices connected at the moment you approve
setup become trusted; the preview is not a fixed snapshot.

Setup creates a private temporary file, invokes USBGuard's syntax validator,
checks it is nonempty, and atomically publishes it without replacing an existing
file. The file is root:root, mode 0600. Only after validation and publication does
setup start protection, verify its connection, and enable startup at boot.
An existing policy, even an empty or corrupt file, is never regenerated.
A custom or invalid configuration requires administrator review instead.

A configured but stopped installation offers an On switch. If protection is
already running, the application uses its existing policy unchanged. Ubuntu's
package usually creates this existing configuration during installation, so
its first-run experience may skip our wizard entirely.

## How It Works

New unmatched devices remain blocked while you decide what to do. Notifications
are the **Ask** behavior; existing saved rules still take priority. This version
does not add an automatic-allow preference or silently change existing defaults.
If an existing installation uses a different default, the UI reports it.

- **Allow Once** permits this connection without writing a rule. Existing saved
  rules still apply on later connections; it does not erase a preexisting allow.
- **Always Allow** asks USBGuard to create or update its persistent device rule.
- **Block** blocks this connection. Blocking a hub can also disconnect children.
- **Forget Rule** removes a saved decision after confirmation. It does not
  retroactively change already connected devices.

The session agent starts at login through XDG Autostart, and immediately when
you open the installed GUI. GNOME notification preferences can silence it.
An administrator authentication prompt may appear after a notification action.
Notifications are withdrawn on removal or restart; stale actions are rejected.

Turning protection off stops management and disables startup. USBGuard's
existing controller-restoration setting is preserved, so devices may remain
unauthorized until reconnect or reboot. A failed service operation is reported;
a successfully saved policy remains intact if a later service start fails.

## Security Model

The kernel and USBGuard enforce access. GUI and agent share an asynchronous
`Gio.DBusProxy` client on the system bus, with upstream Polkit authorization.
They never auto-activate USBGuard merely to display status.

`/usr/libexec/usbguard-desktop-bootstrap` is a one-shot, root-owned helper,
authorized by `pkexec`. It accepts only `initialize`, `enable`, `disable`, or
`status`, no arbitrary path or command. Its isolated Python interpreter ignores
user Python import paths. Subprocess arguments are fixed lists without a shell.
The helper's module is installed under root-owned system Python directories.

Bootstrap uses USBGuard's parser, not the UI display parser, for syntax
validation. Concurrent policy creation fails without overwriting the new file.
No broad Polkit allow rule is added. Existing USBGuard IPC permissions are
preserved; Ubuntu's package may grant privileges to members of `plugdev`.
Device names and serials are untrusted display text and are never commands.
USB identity matching is USBGuard's responsibility and is not cryptographic
proof that a physical device is trustworthy.

## Development

```bash
sudo apt install python3-venv python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
./scripts/install-dev.sh
.venv/bin/usb-protection
```

System bootstrap and autostart integration require the Debian package.
`./scripts/uninstall-dev.sh` removes only the editable Python installation.
See [CONTRIBUTING.md](CONTRIBUTING.md) for safety and contribution guidelines.

## Build Debian Package

Install build-only dependencies; these do not install or start USBGuard:

```bash
sudo apt install debhelper dh-python pybuild-plugin-pyproject python3-all \
  python3-setuptools python3-build python3-installer python3-pytest python3-gi \
  gir1.2-gtk-4.0 gir1.2-adw-1 lintian appstream desktop-file-utils xvfb dbus-x11
./scripts/build-deb.sh
dpkg-deb --info dist/*.deb
dpkg-deb --contents dist/*.deb
lintian --fail-on error dist/*.deb
```

Output: `dist/usbguard-desktop_0.1.0-1_all.deb`. The script uses standard
debhelper/pybuild in a temporary staging directory. For a reviewed test machine:

```bash
sudo apt install ./dist/usbguard-desktop_0.1.0-1_all.deb
```

A Python wheel alone does not install desktop integration or system packages.

## Testing

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
dbus-run-session -- xvfb-run -a .venv/bin/pytest -q
appstreamcli validate --no-net data/*.metainfo.xml
desktop-file-validate data/*.desktop data/autostart/*.desktop
```

Tests use fake devices, temporary files, an isolated session-bus service, and
Xvfb. They never block real USB devices, write `/etc/usbguard`, or stop services.
Without a display or session bus, the corresponding integration tests skip.
See [manual acceptance checks](docs/manual-testing.md) for tests that still
require a disposable Ubuntu desktop VM and actual notification/authentication UI.

## Releasing

Do not tag a release until the installation safety blocker and manual acceptance
checks are resolved, tests pass, the Debian build succeeds, and lintian has no
errors. No release has been created by the development scripts.

Once those gates are met, a maintainer can explicitly publish:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The workflow validates a strict `vMAJOR.MINOR.PATCH` tag, synchronizes Python,
Debian and AppStream versions in its build checkout, tests and builds the
package, then publishes `.deb` and `SHA256SUMS` using GitHub CLI. Checksums contain
relative filenames. Reruns update the same release assets with `--clobber`.
CI uploads build artifacts using `actions/upload-artifact@v4` on pushes and PRs.

## Architecture

```text
GTK4 / Libadwaita GUI        Gio session notification agent
            \                 /
           shared USBGuardClient
          asynchronous system D-Bus
                    |
        upstream USBGuard D-Bus / Polkit
                    |
             USBGuard daemon
                    |
               Linux kernel
```

The independent one-shot bootstrap helper handles initial setup and service
lifecycle. It is not a daemon. `src/usb_protection/usbguard` contains protocol
and display models; `ui`, `agent`, and `services` keep their responsibilities
separate. Exact package/API evidence is in [docs/environment.md](docs/environment.md).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE). AppStream metadata is CC0-1.0.
