import os

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("DISPLAY"), reason="Requires Xvfb/display")


def test_native_windows(monkeypatch):
    from test_core import FakeClient

    from usb_protection.application import Application
    from usb_protection.services.protection import ProtectionService
    from usb_protection.ui.device_page import show_device
    from usb_protection.ui.rules_page import show_rules
    from usb_protection.ui.window import MainWindow
    from usb_protection.usbguard.client import USBGuardClient

    monkeypatch.setattr(USBGuardClient, "connect", lambda self, callback: callback(None))
    monkeypatch.setattr(
        ProtectionService,
        "status",
        lambda self, cb: cb(
            {"installed": True, "configured": False, "active": False, "error": None}
        ),
    )
    app = Application()
    app.register(None)
    window = MainWindow(app)
    assert window.get_title() == "USB Protection"
    assert window.groups[0].get_title() == "Welcome to USB Protection"
    window.client = FakeClient()
    detail = show_device(window, window.client.devices[0])
    rules = show_rules(window)
    rules.close()
    detail.close()
    window.closing()
    window.destroy()
