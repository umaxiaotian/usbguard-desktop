from dataclasses import dataclass

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
            return "Keyboard, mouse or other input device"
        if "08:" in interfaces:
            return "USB storage"
        if "09:" in interfaces:
            return "USB hub"
        return "USB device"

    def metadata(self):
        return [
            (label, clean_text(self.rule.attributes.get(key, "")) or "Unknown")
            for label, key in (
                ("Device ID", "id"),
                ("Serial", "serial"),
                ("Port", "via-port"),
                ("Interfaces", "with-interface"),
                ("Fingerprint", "hash"),
            )
        ]
