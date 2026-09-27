from gi.repository import GLib

from ..services.protection import ProtectionService
from ..usbguard.client import USBGuardClient
from .device_page import show_device
from .rules_page import show_rules
from .setup_page import setup_group
from .widgets import Adw, Gtk, button, confirm, row


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, application):
        super().__init__(
            application=application, title="USB Protection", default_width=640, default_height=700
        )
        self.client = USBGuardClient()
        self.service = ProtectionService()
        self.closed = False
        self.busy = False
        self.refreshing = False
        self.generation = 0
        self.toast = Adw.ToastOverlay()
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Refresh")
        refresh.connect("clicked", lambda _: self.refresh())
        header.pack_end(refresh)
        toolbar.add_top_bar(header)
        self.page = Adw.PreferencesPage()
        toolbar.set_content(self.page)
        self.toast.set_child(toolbar)
        self.set_content(self.toast)
        self.groups = []
        self.client.owner_listeners.append(lambda _: self.refresh())
        self.client.listeners.append(self.event)
        self.client.connect(lambda error: self.refresh())
        self.connect("close-request", self.closing)
        self.timer = GLib.timeout_add_seconds(5, self.tick)
        self.refresh()

    def event(self, name, _params):
        if name in {"DevicePolicyApplied", "DevicePresenceChanged"}:
            self.refresh()

    def tick(self):
        self.refresh()
        return not self.closed

    def add_group(self, group):
        self.groups.append(group)
        self.page.add(group)

    def refresh(self):
        if self.closed or self.busy or self.refreshing:
            return
        self.refreshing = True
        self.generation += 1
        generation = self.generation

        def status(state):
            self.refreshing = False
            if self.closed or generation != self.generation or self.busy:
                return
            for group in self.groups:
                self.page.remove(group)
            self.groups.clear()
            if not state["installed"]:
                group = Adw.PreferencesGroup(title="USBGuard is not installed.")
                group.add(row("Please reinstall USB Protection."))
                self.add_group(group)
                return
            if not state["configured"] and not state["active"]:
                self.add_group(setup_group(self))
                return
            protection = Adw.PreferencesGroup(title="Protection")
            switch = Adw.SwitchRow(title="USB Protection", active=state["active"])
            switch.set_subtitle(
                "On" if state["active"] else "USB Protection is currently disabled."
            )
            switch.connect("notify::active", self.toggle)
            protection.add(switch)
            self.add_group(protection)
            if state["error"]:
                protection.add(row("Unable to read service state", state["error"]))
            if not state["active"]:
                return
            if not self.client.owner:
                action = row("USBGuard connection unavailable", "Protection service is running.")
                action.add_suffix(button("Reconnect", lambda: self.change("enable")))
                protection.add(action)
                return
            behavior = row(
                "New devices", "Ask — blocked until you allow them, unless a saved rule applies."
            )
            protection.add(behavior)

            def default_loaded(value, error):
                if generation == self.generation and not self.closed:
                    if error:
                        behavior.set_subtitle("Unable to read the existing default policy.")
                    elif value != "block":
                        behavior.set_subtitle(
                            "Existing configuration: "
                            + str(value)
                            + ". Your policy has been preserved."
                        )

            self.client.get_default(default_loaded)
            devices_group = Adw.PreferencesGroup(title="Connected Devices")
            self.add_group(devices_group)

            def devices_loaded(devices, error):
                if self.closed or generation != self.generation:
                    return
                if error:
                    devices_group.add(row("Could not load devices", str(error)))
                    return
                if not devices:
                    devices_group.add(row("No connected USB devices"))
                for device in devices:
                    widget = row(device.name, f"{device.kind} · {device.rule.status}")
                    widget.set_activatable(True)
                    widget.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
                    widget.connect("activated", lambda _, d=device: show_device(self, d))
                    devices_group.add(widget)

            self.client.list_devices(devices_loaded)
            rules = Adw.PreferencesGroup()
            action = row("Rules", "Manage saved device decisions")
            action.set_activatable(True)
            action.connect("activated", lambda _: show_rules(self))
            rules.add(action)
            self.add_group(rules)

        self.service.status(status)

    def toggle(self, switch, _param):
        if switch.get_active():
            self.change("enable")
        else:
            # Refresh resets the switch to actual service state if the dialog is cancelled.
            self.refresh()
            confirm(
                self,
                "Turn off USB Protection?",
                "New USB devices will no longer be managed by USB Protection. "
                "Depending on your existing configuration, blocked devices may remain "
                "unavailable until you reconnect them or restart the computer.",
                "Turn Off",
                lambda: self.change("disable"),
            )

    def change(self, operation):
        if self.busy:
            return
        self.busy = True
        self.page.set_sensitive(False)

        def complete(_output, error):
            if self.closed:
                return
            self.busy = False
            self.page.set_sensitive(True)
            self.toast.add_toast(
                Adw.Toast(title=str(error)[:300] if error else "Protection updated")
            )
            self.refresh()

        self.service.change(operation, complete)

    def closing(self, *_args):
        self.closed = True
        GLib.source_remove(self.timer)
        self.client.close()
        self.service.close()
        return False
