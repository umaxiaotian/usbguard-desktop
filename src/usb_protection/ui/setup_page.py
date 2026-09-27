from ..services.protection import connected_preview
from ..usbguard.rule import clean_text
from .widgets import Adw, button, row


def setup_group(window):
    group = Adw.PreferencesGroup(
        title="Welcome to USB Protection",
        description=(
            "Before protection is enabled, all devices connected at that moment will be trusted. "
            "Unplug devices you do not trust, and keep your keyboard and mouse connected."
        ),
    )
    for name, identifier in connected_preview():
        group.add(row(clean_text(name), identifier))
    action = row("Ready to protect this computer?")
    action.add_suffix(button("Enable USB Protection", lambda: window.change("initialize")))
    group.add(action)
    return group
