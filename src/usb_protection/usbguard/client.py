"""Only module that speaks the USBGuard D-Bus protocol."""

from gi.repository import Gio, GLib

from ..i18n import _
from .device import Device
from .enums import Target
from .errors import USBGuardError, friendly_error
from .rule import parse_response

BUS_NAME = "org.usbguard1"
ENDPOINTS = {
    "devices": ("/org/usbguard1/Devices", "org.usbguard.Devices1"),
    "policy": ("/org/usbguard1/Policy", "org.usbguard.Policy1"),
    "root": ("/org/usbguard1", "org.usbguard1"),
}


class USBGuardClient:
    def __init__(self, proxies=None):
        self.proxies = proxies or {}
        self.cancel = Gio.Cancellable()
        self.listeners = []
        self.owner_listeners = []
        self.closed = False

    @property
    def owner(self):
        proxy = self.proxies.get("devices")
        return proxy.get_name_owner() if proxy else None

    def connect(self, callback):
        remaining = set(ENDPOINTS)
        failures = []

        def ready(_source, result, key):
            if self.closed:
                return
            try:
                proxy = Gio.DBusProxy.new_for_bus_finish(result)
                self.proxies[key] = proxy
                if key == "devices":
                    proxy.connect("g-signal", self._signal)
                    proxy.connect("notify::g-name-owner", self._owner_changed)
            except GLib.Error as exc:
                failures.append(friendly_error(exc))
            remaining.discard(key)
            if not remaining:
                callback(None if not failures else failures[0])

        for key, (path, interface) in ENDPOINTS.items():
            # Never D-Bus-activate an unconfigured daemon as a side effect of opening UI.
            flags = Gio.DBusProxyFlags.DO_NOT_AUTO_START | Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES
            Gio.DBusProxy.new_for_bus(
                Gio.BusType.SYSTEM,
                flags,
                None,
                BUS_NAME,
                path,
                interface,
                self.cancel,
                ready,
                key,
            )

    def _owner_changed(self, *_args):
        for listener in tuple(self.owner_listeners):
            listener(self.owner)

    def _signal(self, _proxy, _sender, name, params):
        for listener in tuple(self.listeners):
            listener(name, params.unpack())

    def _call(
        self, endpoint, method, signature, values, callback, parser=lambda x: x, interactive=False
    ):
        if self.closed:
            return
        proxy = self.proxies.get(endpoint)
        if proxy is None or not proxy.get_name_owner():
            callback(None, USBGuardError(_("USBGuard is unavailable. Enable protection first.")))
            return
        owner = proxy.get_name_owner()

        def finished(source, result):
            if self.closed:
                return
            try:
                response = source.call_finish(result).unpack()
                if source.get_name_owner() != owner:
                    raise USBGuardError(_("USBGuard restarted. Refresh and try again."))
                value = parser(response)
            except (GLib.Error, USBGuardError, TypeError, ValueError, IndexError) as exc:
                callback(None, friendly_error(exc))
            else:
                callback(value, None)

        flags = Gio.DBusCallFlags.NO_AUTO_START
        if interactive:
            flags |= Gio.DBusCallFlags.ALLOW_INTERACTIVE_AUTHORIZATION
        proxy.call(
            method,
            GLib.Variant(signature, values),
            flags,
            120000 if interactive else 10000,
            self.cancel,
            finished,
        )

    def list_devices(self, callback):
        self._call(
            "devices",
            "listDevices",
            "(s)",
            ("match",),
            callback,
            lambda value: [Device(rule) for rule in parse_response(value)],
        )

    def list_rules(self, callback):
        self._call("policy", "listRules", "(s)", ("",), callback, parse_response)

    def get_default(self, callback):
        self._call(
            "root",
            "getParameter",
            "(s)",
            ("ImplicitPolicyTarget",),
            callback,
            self._parameter,
        )

    @staticmethod
    def _parameter(value):
        if not isinstance(value, tuple) or len(value) != 1 or not isinstance(value[0], str):
            raise USBGuardError(_("Invalid setting response from USBGuard."))
        return value[0]

    def apply(self, device, action, callback, expected_owner=None):
        options = {
            "allow-once": (Target.ALLOW, False),
            "always-allow": (Target.ALLOW, True),
            "block": (Target.BLOCK, False),
        }
        if action not in options:
            callback(None, USBGuardError(_("Unknown device action.")))
            return
        owner = expected_owner or self.owner

        def checked(devices, error):
            if error:
                callback(None, error)
                return
            current = next((d for d in devices if d.id == device.id), None)
            if self.owner != owner or current is None or current.identity != device.identity:
                callback(
                    None, USBGuardError(_("The device changed or disappeared. Refresh and retry."))
                )
                return
            target, permanent = options[action]
            self._call(
                "devices",
                "applyDevicePolicy",
                "(uub)",
                (device.id, int(target), permanent),
                callback,
                self._rule_id,
                interactive=True,
            )

        self.list_devices(checked)

    @staticmethod
    def _rule_id(value):
        if len(value) != 1 or type(value[0]) is not int or not 0 <= value[0] < 2**32:
            raise USBGuardError(_("Invalid action response from USBGuard."))
        return value[0]

    def forget(self, rule, callback, expected_owner=None):
        owner = expected_owner or self.owner

        def checked(rules, error):
            if error:
                callback(None, error)
            elif self.owner != owner or not any(
                r.id == rule.id and r.raw == rule.raw for r in rules
            ):
                callback(None, USBGuardError(_("The rule changed. Refresh and try again.")))
            else:
                self._call("policy", "removeRule", "(u)", (rule.id,), callback, interactive=True)

        self.list_rules(checked)

    def close(self):
        self.closed = True
        self.cancel.cancel()
        self.listeners.clear()
        self.owner_listeners.clear()
