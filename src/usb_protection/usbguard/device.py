from dataclasses import dataclass

from ..i18n import _
from .rule import Rule, clean_text


@dataclass(frozen=True)
class Device:
    rule: Rule

    @property
    def id(self):
        return self.rule.id

    @property
    def name(self):
        return self.rule.name

    @property
    def identity(self):
        # Pair with the D-Bus unique owner: numeric IDs can be reused after restart.
        return self.rule.attributes.get("hash", "")

    @property
    def kind(self):
        interfaces = self.rule.attributes.get("with-interface", "")
        if "03:" in interfaces:
            return _("Keyboard, mouse or other input device")
        if "08:" in interfaces:
            return _("USB storage")
        if "09:" in interfaces:
            return _("USB hub")
        return _("USB device")

    def metadata(self):
        return [
            (label, clean_text(self.rule.attributes.get(key, "")) or _("Unknown"))
            for label, key in (
                (_("Device ID"), "id"),
                (_("Serial"), "serial"),
                (_("Port"), "via-port"),
                (_("Interfaces"), "with-interface"),
                (_("Fingerprint"), "hash"),
            )
        ]
