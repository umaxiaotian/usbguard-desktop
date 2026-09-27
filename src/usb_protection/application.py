import os
import shutil
import sys

from . import APP_ID
from .ui.widgets import Adw
from .ui.window import MainWindow


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        window = self.get_active_window()
        if window is None:
            window = MainWindow(self)
            if shutil.which("usb-protection-agent"):
                from gi.repository import Gio, GLib

                try:
                    Gio.Subprocess.new(["usb-protection-agent"], Gio.SubprocessFlags.NONE)
                except GLib.Error as exc:
                    window.toast.add_toast(Adw.Toast(title=f"Could not start notifications: {exc}"))
        window.present()


def main():
    if os.geteuid() == 0:
        print("USB Protection must run in your user session, not as root.", file=sys.stderr)
        return 1
    return Application().run(sys.argv)
