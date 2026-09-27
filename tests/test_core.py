import pytest

from usb_protection.usbguard.client import USBGuardClient
from usb_protection.usbguard.device import Device
from usb_protection.usbguard.errors import USBGuardError
from usb_protection.usbguard.rule import Rule, parse_response

RAW = 'block id 0781:5583 serial "abc" name "USB Disk" hash "fingerprint" with-interface 08:06:50'


class FakeClient(USBGuardClient):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.devices = [Device(Rule.parse(7, RAW))]
        self.rules = [Rule.parse(9, RAW.replace("block", "allow", 1))]
        self.current_owner = ":1.42"

    @property
    def owner(self):
        return self.current_owner

    def list_devices(self, callback):
        callback(self.devices, None)

    def list_rules(self, callback):
        callback(self.rules, None)

    def _call(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        args[4](9, None)


def test_model_roundtrip():
    rule = Rule.parse(7, RAW)
    assert rule.name == "USB Disk"
    assert rule.serialize() == RAW
    assert Device(rule).kind == "USB storage"
    assert Device(rule).identity == "fingerprint"


def test_complex_rule_lossless():
    raw = "allow id one-of { 1234:5678 1111:2222 } if !localtime(09:00-17:00)"
    rule = Rule.parse(8, raw)
    assert rule.serialize() == raw
    assert "id" not in rule.attributes


@pytest.mark.parametrize("raw", ["", 'bogus name "x"', 'allow name "unterminated', "allow\x00"])
def test_invalid_rule(raw):
    with pytest.raises(USBGuardError):
        Rule.parse(7, raw)


@pytest.mark.parametrize(
    "response", [None, (), ("bad",), ([(1,)],), ([(True, RAW)],), ([(7, RAW), (7, RAW)],)]
)
def test_invalid_response(response):
    with pytest.raises(USBGuardError):
        parse_response(response)


def test_dbus_response():
    assert parse_response(([(7, RAW)],))[0].id == 7


@pytest.mark.parametrize(
    "action,target,permanent",
    [
        ("allow-once", 0, False),
        ("always-allow", 0, True),
        ("block", 1, False),
    ],
)
def test_actions(action, target, permanent):
    client = FakeClient()
    client.apply(client.devices[0], action, lambda *_: None)
    args, kwargs = client.calls[0]
    assert args[:4] == ("devices", "applyDevicePolicy", "(uub)", (7, target, permanent))
    assert kwargs["interactive"]


def test_repeated_permanent_uses_upstream_upsert():
    client = FakeClient()
    for _ in range(2):
        client.apply(client.devices[0], "always-allow", lambda *_: None)
    assert all(call[0][1] == "applyDevicePolicy" for call in client.calls)


def test_forget():
    client = FakeClient()
    client.forget(client.rules[0], lambda *_: None)
    assert client.calls[0][0][:4] == ("policy", "removeRule", "(u)", (9,))


def test_disappeared_and_restarted():
    client = FakeClient()
    device = client.devices.pop()
    errors = []
    client.apply(device, "allow-once", lambda _, error: errors.append(error))
    client.devices.append(device)
    client.apply(device, "allow-once", lambda _, error: errors.append(error), ":1.older")
    assert len(errors) == 2 and all(errors)
    assert not client.calls


def test_unavailable():
    errors = []
    USBGuardClient().list_devices(lambda _, error: errors.append(error))
    assert isinstance(errors[0], USBGuardError)


def test_unknown_metadata():
    device = Device(Rule.parse(1, 'block name "\n"'))
    assert device.name == "�"
    assert all(value == "Unknown" for _, value in device.metadata())


@pytest.mark.parametrize("response", [(), (None,), (1,), ("block", "allow")])
def test_invalid_parameter_response(response):
    with pytest.raises(USBGuardError):
        USBGuardClient._parameter(response)
