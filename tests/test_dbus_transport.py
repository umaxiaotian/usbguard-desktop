"""Real Gio proxy transport against a fake service; never touches the system bus."""

import os
import time
import uuid

import pytest
from gi.repository import Gio, GLib

from usb_protection.usbguard.client import ENDPOINTS, USBGuardClient

pytestmark = pytest.mark.skipif(
    not os.environ.get("DBUS_SESSION_BUS_ADDRESS"), reason="Requires dbus-run-session"
)

XML = """<node><interface name="org.usbguard.Devices1">
<method name="listDevices"><arg type="s" direction="in"/>
<arg type="a(us)" direction="out"/></method>
<method name="applyDevicePolicy"><arg type="u" direction="in"/>
<arg type="u" direction="in"/><arg type="b" direction="in"/>
<arg type="u" direction="out"/></method>
<signal name="DevicePresenceChanged"><arg type="u"/><arg type="u"/>
<arg type="u"/><arg type="s"/><arg type="a{ss}"/></signal>
</interface></node>"""


def wait_for(predicate):
    context = GLib.MainContext.default()
    deadline = time.monotonic() + 3
    while not predicate() and time.monotonic() < deadline:
        context.iteration(False)
        time.sleep(0.001)
    assert predicate(), "asynchronous callback timed out"


@pytest.fixture
def transport():
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    name = "io.github.umaxiaotian.USBProtection.Test" + uuid.uuid4().hex
    bus.call_sync(
        "org.freedesktop.DBus",
        "/org/freedesktop/DBus",
        "org.freedesktop.DBus",
        "RequestName",
        GLib.Variant("(su)", (name, 0)),
        GLib.VariantType.new("(u)"),
        Gio.DBusCallFlags.NONE,
        1000,
        None,
    )
    calls = []
    state = {"error": None}

    def method(_bus, _sender, _path, _interface, name, parameters, invocation):
        calls.append((name, parameters.unpack()))
        if state["error"]:
            invocation.return_dbus_error("org.freedesktop.DBus.Error.AccessDenied", state["error"])
        elif name == "listDevices":
            invocation.return_value(
                GLib.Variant(
                    "(a(us))", ([(12, 'block id 1234:5678 name "Test device" hash "abc"')],)
                )
            )
        else:
            invocation.return_value(GLib.Variant("(u)", (22,)))

    path, interface = ENDPOINTS["devices"]
    info = Gio.DBusNodeInfo.new_for_xml(XML).interfaces[0]
    registration = bus.register_object(path, info, method, None, None)
    proxy = Gio.DBusProxy.new_sync(
        bus,
        Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES | Gio.DBusProxyFlags.DO_NOT_AUTO_START,
        info,
        name,
        path,
        interface,
        None,
    )
    client = USBGuardClient({"devices": proxy})
    yield client, calls, state, bus, name
    client.close()
    bus.unregister_object(registration)
    bus.call_sync(
        "org.freedesktop.DBus",
        "/org/freedesktop/DBus",
        "org.freedesktop.DBus",
        "ReleaseName",
        GLib.Variant("(s)", (name,)),
        None,
        Gio.DBusCallFlags.NONE,
        1000,
        None,
    )


def test_gio_async_list_and_apply(transport):
    client, calls, _state, _bus, _name = transport
    results = []
    client.list_devices(lambda value, error: results.append((value, error)))
    wait_for(lambda: results)
    devices, error = results.pop()
    assert not error and devices[0].name == "Test device"
    client.apply(devices[0], "always-allow", lambda value, error: results.append((value, error)))
    wait_for(lambda: results)
    assert results == [(22, None)]
    assert calls[-1] == ("applyDevicePolicy", (12, 0, True))


def test_gio_authorization_cancelled(transport):
    client, _calls, state, _bus, _name = transport
    state["error"] = "Authentication cancelled"
    results = []
    client.list_devices(lambda value, error: results.append(error))
    wait_for(lambda: results)
    assert "Permission was not granted" in str(results[0])


def test_close_during_request(transport):
    client, calls, _state, _bus, _name = transport
    results = []
    client.list_devices(lambda *args: results.append(args))
    client.close()
    # Drain pending completions; a closed client must not call disposed UI objects.
    for _ in range(30):
        GLib.MainContext.default().iteration(False)
        time.sleep(0.001)
    assert not results
