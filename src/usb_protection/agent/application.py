import os
import sys

from gi.repository import Gio, GLib

from .. import AGENT_ID
from ..usbguard.client import USBGuardClient
from ..usbguard.device import Device
from ..usbguard.errors import USBGuardError
from ..usbguard.rule import Rule
from .notifications import NotificationRouter


class Agent(Gio.Application):
    def __init__(self):
        super().__init__(application_id=AGENT_ID)
        self.client = USBGuardClient()
        self.router = NotificationRouter(
            self.client, self.notify_device, self.withdraw_notification
        )
        self.last_error = None
        self.ready = False
        self.polling = False

    def do_startup(self):
        Gio.Application.do_startup(self)
        self.hold()
        for name in ("allow-once", "always-allow"):
            action = Gio.SimpleAction.new(name, GLib.VariantType.new("s"))
            action.connect("activate", self.action)
            self.add_action(action)
        self.client.listeners.append(self.event)
        self.client.owner_listeners.append(self.owner_changed)
        self.client.connect(self.connected)
        self.timer = GLib.timeout_add_seconds(15, self.poll)

    def do_activate(self):
        # A second process simply activates this existing session instance.
        pass

    def connected(self, error):
        self.ready = not error
        if error:
            self.error(str(error))
        else:
            self.poll()

    def owner_changed(self, _owner):
        self.router.clear()
        self.poll()

    def poll(self):
        if not self.ready or not self.client.owner or self.polling:
            return True
        self.polling = True

        def listed(devices, error):
            self.polling = False
            if error:
                self.error(str(error))
                return
            self.last_error = None
            ids = {device.id for device in devices if device.rule.target == "block"}
            for _owner, device in tuple(self.router.pending.values()):
                if device.id not in ids:
                    self.router.remove(device.id)
            for device in devices:
                self.router.offer(device)

        self.client.list_devices(listed)
        return True

    def event(self, name, args):
        try:
            if name == "DevicePresenceChanged" and len(args) == 5 and args[1] == 3:
                self.router.remove(args[0])
            elif name == "DevicePolicyApplied" and len(args) == 5:
                identifier, target, raw, _rule_id, _attributes = args
                if target == 1:
                    self.router.offer(Device(Rule.parse(identifier, raw)))
                else:
                    self.router.remove(identifier)
        except (USBGuardError, TypeError, ValueError):
            self.error("A USB device reported invalid details. Open USB Protection to refresh.")

    def notify_device(self, token, device):
        notification = Gio.Notification.new("New USB Device")
        notification.set_body(f"{device.name}\n{device.kind}\nBlocked until you choose what to do.")
        notification.set_icon(Gio.ThemedIcon.new("io.github.umaxiaotian.USBProtection"))
        notification.add_button_with_target_value(
            "Allow Once", "app.allow-once", GLib.Variant("s", token)
        )
        notification.add_button_with_target_value(
            "Always Allow", "app.always-allow", GLib.Variant("s", token)
        )
        self.send_notification(token, notification)

    def action(self, action, parameter):
        def complete(_value, error):
            if error:
                self.error(str(error))

        self.router.activate(parameter.get_string(), action.get_name(), complete)

    def error(self, message):
        if message == self.last_error:
            return
        self.last_error = message
        notification = Gio.Notification.new("USB Protection needs attention")
        notification.set_body(message)
        self.send_notification("connection-error", notification)

    def do_shutdown(self):
        GLib.source_remove(self.timer)
        self.router.clear()
        self.client.close()
        Gio.Application.do_shutdown(self)


def main():
    if os.geteuid() == 0:
        print("The notification agent must run in a user session, not as root.", file=sys.stderr)
        return 1
    return Agent().run(sys.argv)
