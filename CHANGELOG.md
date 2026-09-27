# Changelog

## 0.1.0 — unreleased

- Native GTK4 / Libadwaita device and rule management.
- Asynchronous USBGuard D-Bus client with system authentication.
- Validated, atomic, no-clobber first-run policy creation.
- Session notifications with working temporary and persistent allow actions.
- Debian packaging and automated CI / tag-based release builds.
- English, Japanese, Korean, Simplified Chinese, and Spanish localization.
- Known release blocker: Ubuntu's USBGuard dependency starts itself during
  installation, before the application's first-run wizard. See README.
