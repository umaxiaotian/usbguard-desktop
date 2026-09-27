import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402


def row(title, subtitle=""):
    widget = Adw.ActionRow(title=title, subtitle=subtitle)
    widget.set_use_markup(False)
    return widget


def button(label, callback, destructive=False):
    widget = Gtk.Button(label=label, valign=Gtk.Align.CENTER)
    widget.add_css_class("destructive-action" if destructive else "suggested-action")
    widget.connect("clicked", lambda _: callback())
    return widget


def confirm(parent, heading, body, label, callback):
    # MessageDialog is supported by the Ubuntu 24.04 Libadwaita 1.5 baseline.
    dialog = Adw.MessageDialog(transient_for=parent, modal=True, heading=heading, body=body)
    dialog.add_response("cancel", "Cancel")
    dialog.add_response("confirm", label)
    dialog.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.set_default_response("cancel")
    dialog.set_close_response("cancel")
    dialog.connect("response", lambda _, response: callback() if response == "confirm" else None)
    dialog.present()


def detail_window(parent, title):
    window = Adw.Window(
        transient_for=parent, modal=True, title=title, default_width=480, default_height=580
    )
    toolbar = Adw.ToolbarView()
    toolbar.add_top_bar(Adw.HeaderBar())
    page = Adw.PreferencesPage()
    toolbar.set_content(page)
    window.set_content(toolbar)
    return window, page
