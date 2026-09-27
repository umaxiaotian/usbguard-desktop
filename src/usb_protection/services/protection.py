"""Non-privileged, asynchronous service status and fixed helper invocation."""

import os
from pathlib import Path

from gi.repository import Gio, GLib

HELPER = "/usr/libexec/usbguard-desktop-bootstrap"


class ProtectionService:
    def __init__(self):
        self.closed = False
        self.cancel = Gio.Cancellable()

    def _execute(self, argv, callback):
        try:
            process = Gio.Subprocess.new(
                argv, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
            )
        except GLib.Error as exc:
            callback(None, str(exc))
            return

        def done(source, result):
            try:
                _, output, error = source.communicate_utf8_finish(result)
                if not self.closed:
                    callback(
                        output,
                        None
                        if source.get_successful()
                        else error.strip()
                        or "Authorization was cancelled or the operation failed.",
                    )
            except GLib.Error as exc:
                if not self.closed:
                    callback(None, str(exc))

        process.communicate_utf8_async(None, self.cancel, done)

    def status(self, callback):
        installed = Path("/usr/bin/usbguard").is_file()
        try:
            configured = os.path.lexists("/etc/usbguard/rules.conf")
            # Never interpret an inaccessible parent directory as a missing policy.
            Path("/etc/usbguard").stat() if installed else None
        except OSError:
            configured = True

        def complete(output, error):
            callback(
                {
                    "installed": installed,
                    "configured": configured,
                    "active": bool(output and "ActiveState=active" in output),
                    "error": error,
                }
            )

        self._execute(
            [
                "/usr/bin/systemctl",
                "show",
                "usbguard.service",
                "--property=ActiveState",
                "--property=LoadState",
            ],
            complete,
        )

    def change(self, operation, callback):
        if operation not in {"initialize", "enable", "disable"}:
            raise ValueError("Unsupported protection operation")
        self._execute(["/usr/bin/pkexec", HELPER, operation], callback)

    def close(self):
        self.closed = True
        self.cancel.cancel()


def connected_preview():
    """Read-only sysfs preview before a daemon exists; never writes authorization."""
    devices = []
    for device in sorted(Path("/sys/bus/usb/devices").glob("*")):
        try:
            if not (device / "idVendor").exists():
                continue
            name = (device / "product").read_text().strip() if (device / "product").exists() else ""
            vendor = (device / "idVendor").read_text().strip()
            product = (device / "idProduct").read_text().strip()
            devices.append((name or "USB device", f"{vendor}:{product}"))
        except OSError:
            continue  # Hot unplug during enumeration.
    return devices
