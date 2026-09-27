from .widgets import Adw, Gtk, button, confirm, detail_window, row


def show_device(parent, device):
    owner = parent.client.owner
    window, page = detail_window(parent, device.name)
    info = Adw.PreferencesGroup(title=device.name, description=device.kind)
    info.add(row("Status", device.rule.status))
    for title, value in device.metadata():
        info.add(row(title, value))
    page.add(info)
    access = Adw.PreferencesGroup(
        title="Access",
        description=(
            "Allow Once lasts for this connection. "
            "Existing persistent rules still apply on reconnect. "
            "Block affects this connection; forget an allow rule "
            "to stop trusting future connections."
        ),
    )
    choices = []
    for label, action in [
        ("Block", "block"),
        ("Allow Once", "allow-once"),
        ("Always Allow", "always-allow"),
    ]:
        choice = Gtk.CheckButton(label=label)
        if choices:
            choice.set_group(choices[0][0])
        choices.append((choice, action))
        access.add(choice)
    choices[0][0].set_active(True)
    page.add(access)
    status = Gtk.Label(wrap=True)
    access.add(status)

    def apply():
        selected = next(action for choice, action in choices if choice.get_active())

        def perform():
            apply_button.set_sensitive(False)

            def complete(_value, error):
                apply_button.set_sensitive(True)
                if error:
                    status.set_text(str(error))
                else:
                    window.close()
                    parent.refresh()

            parent.client.apply(device, selected, complete, owner)

        if selected == "block":
            confirm(
                window,
                "Block this device?",
                "Blocking a keyboard, mouse, network adapter or USB hub may interrupt "
                "your access to this computer.",
                "Block",
                perform,
            )
        else:
            perform()

    apply_button = button("Apply", apply)
    access.add(apply_button)
    window.present()
    return window
