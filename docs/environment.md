# Environment and protocol evidence

Inspected on 2026-09-27: Ubuntu 26.04.1 (resolute), Python 3.14.4,
GTK 4.22.4, Libadwaita 1.9.1. Ubuntu 24.04's Libadwaita 1.5 is the UI baseline.
The host had no installed USBGuard and no USBGuard service or bus owner.

APT supplied `usbguard` and `libusbguard1` version `1.1.4+ds-2`.
Packages were downloaded and extracted without running maintainer scripts.
The matching Ubuntu source archive was inspected:
https://archive.ubuntu.com/ubuntu/pool/universe/u/usbguard/usbguard_1.1.4+ds.orig.tar.xz

Authoritative files: `src/DBus/DBusBridge.hpp`, `src/DBus/DBusInterface.xml`,
`src/DBus/DBusBridge.cpp`, and `src/CLI/usbguard-rule-parser.cpp`.
The installed-package layout includes the D-Bus bridge, its system service,
Polkit actions, and `/usr/bin/usbguard-rule-parser` in **usbguard itself**;
there is no separate usbguard-dbus dependency on this Ubuntu release.

Verified protocol:

| Bus name | Object path | Interface |
| --- | --- | --- |
| org.usbguard1 | /org/usbguard1 | org.usbguard1 |
| org.usbguard1 | /org/usbguard1/Devices | org.usbguard.Devices1 |
| org.usbguard1 | /org/usbguard1/Policy | org.usbguard.Policy1 |

- listDevices(s) → a(us); query `match` lists all devices.
- applyDevicePolicy(uub) → u; targets allow=0, block=1, reject=2.
- listRules(s) → a(us); empty label lists all rules.
- removeRule(u) → void.
- DevicePresenceChanged(uuusa{ss}); removal event=3.
- DevicePolicyApplied(uusua{ss}).
- getParameter(s) → s.

Permanent decisions use USBGuard's own applyDevicePolicy implementation,
which updates or creates the device rule. The application does not implement
its own policy matcher. Display parsing is not security validation.
Bootstrap validation uses the packaged `usbguard-rule-parser -f FILE`.

## Installation safety constraint

The Ubuntu `usbguard` postinst generates `/etc/usbguard/rules.conf` if missing
and **enables/starts both services during dependency installation**. It even
ignores failure of policy generation. An ordinary dependent .deb cannot
reliably intercept a dependency's earlier configuration. Our package never
starts the system service from its maintainer scripts, but cannot guarantee
wizard-before-start on a pristine machine using plain `apt install`.

Do not call this distribution path production-ready until the upstream
packaging behavior is resolved or the installer can prevent dependency
service startup before APT runs. Do not test a fresh install on a machine
whose input/network depends on USB. Use a disposable VM with non-USB input.
Existing policy files, including empty files, are never replaced by setup.

Live system-bus introspection and hardware authorization were deliberately
not attempted against a newly started daemon on this development host.
The protocol above is derived from the exact Ubuntu package/source, not
guessed from older online documentation.
