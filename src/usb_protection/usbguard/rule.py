"""Lossless rule display model; USBGuard remains the policy parser and engine.

We extract only unambiguous scalar attributes. Complex sets/conditions remain
available in Advanced and are never interpreted as an authorization decision.
"""

import re
from dataclasses import dataclass

from .errors import USBGuardError

TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|[{}]|[^\s{}"]+')
SCALARS = {"id", "name", "serial", "hash", "parent-hash", "via-port", "with-connect-type"}


def clean_text(value):
    return "".join(c if c.isprintable() else "�" for c in value)[:512]


def decode(value):
    if value.startswith('"'):
        return re.sub(r'\\([\\"])', r"\1", value[1:-1])
    return value


@dataclass(frozen=True)
class Rule:
    id: int
    raw: str
    target: str
    attributes: dict

    @classmethod
    def parse(cls, identifier, raw):
        if type(identifier) is not int or not 0 < identifier < 2**32:
            raise USBGuardError("Invalid rule identifier in USBGuard response.")
        if not isinstance(raw, str) or len(raw) > 65536 or "\x00" in raw:
            raise USBGuardError("Invalid rule in USBGuard response.")
        tokens = TOKEN.findall(raw)
        # Reject incomplete strings, but preserve all valid complex syntax verbatim.
        if not tokens:
            raise USBGuardError("Empty rule in USBGuard response.")
        quoted = False
        escaped = False
        for char in raw:
            if escaped:
                escaped = False
            elif char == "\\" and quoted:
                escaped = True
            elif char == '"':
                quoted = not quoted
        if quoted or tokens[0] not in {"allow", "block", "reject", "match", "device"}:
            raise USBGuardError("Malformed rule in USBGuard response.")
        attrs = {}
        depth = 0
        for index, token in enumerate(tokens[1:], 1):
            if token == "{":
                depth += 1
            elif token == "}":
                depth -= 1
            elif depth == 0 and token in SCALARS and index + 1 < len(tokens):
                value = tokens[index + 1]
                if value not in {"{", "}", "one-of", "all-of", "none-of", "equals"}:
                    attrs[token] = decode(value)
        if "with-interface" in tokens:
            start = tokens.index("with-interface") + 1
            attrs["with-interface"] = " ".join(
                t
                for t in tokens[start:]
                if re.fullmatch(r"[0-9a-fA-F*]{2}:[0-9a-fA-F*]{2}:[0-9a-fA-F*]{2}", t)
            )
        return cls(identifier, raw, tokens[0], attrs)

    @property
    def name(self):
        return clean_text(
            self.attributes.get("name") or self.attributes.get("id") or "Unknown device"
        )

    @property
    def status(self):
        return {"allow": "Allowed", "block": "Blocked", "reject": "Rejected"}.get(
            self.target, "Custom rule"
        )

    def serialize(self):
        return self.raw


def parse_response(response):
    if not isinstance(response, tuple) or len(response) != 1:
        raise USBGuardError("Invalid USBGuard response.")
    rows = response[0]
    if not isinstance(rows, (tuple, list)):
        raise USBGuardError("Invalid USBGuard device list.")
    result = []
    seen = set()
    for row in rows:
        if not isinstance(row, (tuple, list)) or len(row) != 2:
            raise USBGuardError("Invalid USBGuard list entry.")
        rule = Rule.parse(*row)
        if rule.id in seen:
            raise USBGuardError("Duplicate identifier in USBGuard response.")
        seen.add(rule.id)
        result.append(rule)
    return result
