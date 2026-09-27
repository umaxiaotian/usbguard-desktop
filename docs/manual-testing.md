# Manual acceptance checks — not yet completed

Use disposable Ubuntu Desktop 24.04 and 26.04 VMs with non-USB input and console
recovery. Never run fresh installation or block/input tests on the host machine.

1. Inspect the distribution's USBGuard maintainer scripts and resolve the
   install-before-wizard service-start blocker before production release.
2. Install the `.deb` with APT and verify all dependencies and entry points.
3. Verify Wayland launch, native layout, keyboard navigation and system theme.
4. Verify existing configured/running, configured/stopped, missing, empty,
   malformed, custom RuleFile, and additional RuleFolder configurations.
5. Test first-run initialization in a VM whose USBGuard package was installed
   under an administrator-controlled no-start policy. Check owner/mode,
   parser failure, start failure, no-clobber behavior and next boot.
6. Verify temporary allow, persistent allow/reconnect/reboot, block and forget
   using a sacrificial device. Do not block the VM's only input/network path.
7. Verify notifications after login and immediately after opening the GUI,
   authentication accept/cancel, GNOME notification suppression, unplug while
   authenticating, duplicate clicks, daemon restart and stale notifications.
8. Stop protection and record kernel behavior with the distribution's existing
   RestoreControllerDeviceState setting; verify UI wording matches reality.
9. Uninstall and purge **usbguard-desktop only**, checking policy preservation.
10. Run GitHub CI and validate a maintainer-authorized release in a test fork,
    including rerun behavior, version consistency and SHA256SUMS.

Local automated evidence does not substitute for these acceptance checks.
