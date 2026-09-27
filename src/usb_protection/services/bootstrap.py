"""Fixed-operation privileged bootstrap; never imported by the GUI.

The launcher uses Python isolated mode. Paths accepted by internal functions
exist for unit tests only: the public entry point accepts no path or command.
"""

import fcntl
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ..i18n import _

POLICY = Path("/etc/usbguard/rules.conf")
CONFIG = Path("/etc/usbguard/usbguard-daemon.conf")
UNITS = ("usbguard.service", "usbguard-dbus.service")
ENV = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"}


class BootstrapError(Exception):
    pass


def run(argv, **kwargs):
    return subprocess.run(argv, shell=False, check=True, timeout=45, env=ENV, **kwargs)


def secure_file(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
        raise BootstrapError(_("Configuration must be a root-owned, non-writable regular file."))


def validate_policy(path, runner=run):
    secure_file(path)
    if not any(
        line.strip() and not line.lstrip().startswith("#") for line in path.read_text().splitlines()
    ):
        raise BootstrapError(_("The policy is empty. Protection was not started."))
    runner(
        ["/usr/bin/usbguard-rule-parser", "-f", str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def publish_policy(path, generate, validate, owner=0):
    """Atomic durable publication, with EEXIST protection against concurrent edits.

    Hard-link publication has atomic visibility without os.replace's clobbering.
    """
    if os.path.lexists(path):
        raise BootstrapError(_("A policy already exists. It has not been changed."))
    fd, temporary = tempfile.mkstemp(prefix=".usb-protection-", dir=path.parent)
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            if os.geteuid() == 0:
                os.fchown(stream.fileno(), owner, owner)
            generate(stream)
            stream.flush()
            os.fsync(stream.fileno())
        info = temporary.stat()
        if info.st_uid != owner or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size == 0:
            raise BootstrapError(
                _("Generated policy failed ownership, permission or empty-file checks.")
            )
        validate(temporary)
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError as exc:
            raise BootstrapError(_("A policy already exists. It has not been changed.")) from exc
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def config_values():
    secure_file(CONFIG)
    values = {}
    for line in CONFIG.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def check_setup_config():
    values = config_values()
    expected = {
        "RuleFile": str(POLICY),
        "ImplicitPolicyTarget": "block",
        "PresentDevicePolicy": "apply-policy",
        "InsertedDevicePolicy": "apply-policy",
        "DeviceManagerBackend": "uevent",
    }
    if any(values.get(key) != value for key, value in expected.items()):
        raise BootstrapError(
            _("Existing custom USBGuard configuration needs administrator review.")
        )
    folder = values.get("RuleFolder")
    if folder and (folder != "/etc/usbguard/rules.d/" or any(Path(folder).iterdir())):
        raise BootstrapError(_("Additional rules already exist. They have not been changed."))


def start_protection():
    if config_values().get("RuleFile") != str(POLICY):
        raise BootstrapError(_("A custom policy location requires administrator review."))
    validate_policy(POLICY)
    run(["/usr/bin/systemctl", "start", *UNITS], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # The real bridge connects to the daemon on a one-second retry timer.
    # A registered bus name alone does not mean it is ready for requests.
    wait_for_bridge()
    run(["/usr/bin/systemctl", "enable", *UNITS], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def wait_for_bridge(runner=run, sleep=time.sleep):
    for attempt in range(5):
        try:
            runner(
                [
                    "/usr/bin/busctl",
                    "--system",
                    "--auto-start=no",
                    "--timeout=3",
                    "call",
                    "org.usbguard1",
                    "/org/usbguard1/Devices",
                    "org.usbguard.Devices1",
                    "listDevices",
                    "s",
                    "match",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            return
        except subprocess.CalledProcessError:
            if attempt == 4:
                raise
            sleep(1)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in {"initialize", "enable", "disable", "status"}:
        print(_("Expected one of: initialize, enable, disable, status"), file=sys.stderr)
        return 2
    if os.geteuid() != 0:
        print(_("Administrator authorization is required."), file=sys.stderr)
        return 1
    os.umask(0o077)
    try:
        # /run is root-owned, so an unprivileged process cannot plant this lock.
        with open("/run/usbguard-desktop-bootstrap.lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            action = argv[0]
            if action == "status":
                print(json.dumps({"configured": os.path.lexists(POLICY)}))
                return 0
            if action == "initialize":
                parent = POLICY.parent.lstat()
                if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != 0 or parent.st_mode & 0o022:
                    raise BootstrapError(_("The policy directory is not secure."))
                check_setup_config()

                def generate(stream):
                    run(
                        ["/usr/bin/usbguard", "generate-policy"],
                        stdout=stream,
                        stderr=subprocess.PIPE,
                    )

                def validate(path):
                    validate_policy(path)
                    lines = [
                        s.strip()
                        for s in path.read_text().splitlines()
                        if s.strip() and not s.lstrip().startswith("#")
                    ]
                    if not lines or any(not s.startswith("allow ") for s in lines):
                        raise BootstrapError(
                            _("Initial policy must trust currently connected devices.")
                        )

                publish_policy(POLICY, generate, validate)
                start_protection()
            elif action == "enable":
                start_protection()
            elif action == "disable":
                run(
                    ["/usr/bin/systemctl", "disable", "--now", *UNITS],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
        return 0
    except (BootstrapError, OSError, subprocess.SubprocessError) as exc:
        detail = getattr(exc, "stderr", None)
        if isinstance(detail, bytes):
            detail = detail.decode(errors="replace")
        print(str(detail or exc)[:2000], file=sys.stderr)
        return 1
