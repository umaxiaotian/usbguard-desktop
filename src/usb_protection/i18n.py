"""gettext setup shared by the GUI and notification agent."""

import gettext
import os
from pathlib import Path

DOMAIN = "usbguard-desktop"


def _locale_dir():
    override = os.environ.get("USB_PROTECTION_LOCALEDIR")
    if override:
        return override
    system = Path("/usr/share/locale")
    if Path(__file__).resolve().is_relative_to(Path("/usr/lib")):
        return str(system)
    return str(Path(__file__).resolve().parents[2] / "locale")


gettext.bindtextdomain(DOMAIN, _locale_dir())
gettext.textdomain(DOMAIN)
_ = gettext.translation(DOMAIN, _locale_dir(), fallback=True).gettext
