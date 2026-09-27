from .widgets import Adw, Gtk, button, confirm, detail_window, row


def show_rules(parent):
    owner = parent.client.owner
    window, page = detail_window(parent, "Rules")
    message = Gtk.Label(label="Loading rules…", wrap=True)
    notice = Adw.PreferencesGroup()
    notice.add(message)
    page.add(notice)

    def loaded(rules, error):
        if error:
            message.set_text(str(error))
            return
        message.set_text(
            "Rules are evaluated in the order shown. Forgetting a rule does not "
            "change devices already connected."
            if rules
            else "No saved rules."
        )
        group = Adw.PreferencesGroup(title="Saved Rules")
        for rule in rules:
            widget = Adw.ExpanderRow(title=rule.name, subtitle=rule.status)
            widget.set_use_markup(False)
            widget.add_row(row("Device ID", rule.attributes.get("id", "Custom matching rule")))
            advanced = Adw.ExpanderRow(title="Advanced")
            advanced.add_row(row("USBGuard rule", rule.raw))
            widget.add_row(advanced)
            action = row("Remove saved decision")

            def forget(rule=rule):
                def perform():
                    def complete(_value, error):
                        if error:
                            message.set_text(str(error))
                        else:
                            window.close()
                            parent.refresh()

                    parent.client.forget(rule, complete, owner)

                confirm(
                    window,
                    "Forget this rule?",
                    "Future connections will follow the remaining rules. "
                    "Currently connected devices keep their current access.",
                    "Forget",
                    perform,
                )

            action.add_suffix(button("Forget Rule", forget, destructive=True))
            widget.add_row(action)
            group.add(widget)
        page.add(group)

    parent.client.list_rules(loaded)
    window.present()
    return window
