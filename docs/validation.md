# Validation record — 2026-09-27

Environment: Ubuntu Desktop 26.04.1, Python 3.14.4, GTK 4.22.4, Libadwaita 1.9.1.

| Check | Result |
| --- | --- |
| pytest, isolated session bus and Xvfb | 64 passed |
| ruff check / format check | Passed |
| Python wheel and sdist build | Passed |
| Standard debhelper/pybuild binary build | Passed |
| dpkg-deb info and contents inspection | Passed; Architecture all, runtime dependencies present |
| APT local-package dependency simulation | Passed; USBGuard and runtime libraries resolved |
| lintian --fail-on error | Exit 0; no errors, 3 warnings |
| AppStream validation, offline | Passed; one pedantic notice |
| Desktop entry validation | Passed |
| SHA256SUMS verification | Passed |
| Actual Ubuntu bridge introspection on isolated session bus | Passed, no daemon attached |
| Ubuntu 24.04 archive package layout inspection | Passed |

Lintian warnings: two `groff-message` pipeline failures in this environment,
and `initial-upload-closes-no-bugs` (there is no Debian ITP bug for this personal
package). Direct `man --warnings -l` rendering succeeds. Tests also report
PyGObject/Python 3.14 deprecation warnings; these are not test failures.

Built output: `dist/usbguard-desktop_0.1.0-1_all.deb`, alongside SHA256SUMS,
Python distributions and Debian build metadata. Build artifacts are ignored by
Git and will be uploaded by CI or an explicitly triggered Release workflow.

## Not verified / release blockers

- Fresh APT installation was simulated, not performed on the USB-dependent host.
- Ubuntu's USBGuard maintainer scripts start services during dependency setup,
  before the application wizard can obtain consent. Both inspected Ubuntu
  package versions contain this behavior. The requested safe single-deb first
  install flow is therefore **not yet achieved**.
- No real USB allow/block, first-run root setup, notification button plus Polkit
  desktop interaction, reboot, or uninstall acceptance tests were performed.
- Ubuntu 24.04 runtime and full Wayland/GNOME acceptance remain to be checked.
- GitHub Actions and Release workflows are implemented but not run remotely.
- Git push to `origin/main` failed because HTTPS authentication is unavailable
  (`could not read Username for 'https://github.com'`). Local commits remain.
- No release tag or GitHub Release was created.

See [manual-testing.md](manual-testing.md) for the outstanding acceptance plan.
