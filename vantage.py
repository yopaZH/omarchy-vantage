#!/usr/bin/env python3
"""Lenovo Vantage for Linux - GTK4/libadwaita control panel."""
import glob
import os
import re
import shutil
import subprocess
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Pango", "1.0")
from gi.repository import Adw, Gdk, Gtk, Pango  # noqa: E402

APP_ID = "io.github.niizam.vantage"
HELPER = "/usr/lib/vantage/vantage-helper"
OMARCHY_COLORS_PATH = os.path.expanduser("~/.local/state/omarchy/current/theme/colors.toml")

FAN_MODES = [
    ("Super Silent", "silent"),
    ("Standard", "standard"),
    ("Dust Cleaning", "dust"),
    ("Efficient Thermal Dissipation", "efficient"),
]
FAN_MODE_VALUES = {"0": "silent", "133": "silent", "1": "standard", "2": "dust", "4": "efficient"}


def sh(*args):
    """Run a command, returning (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(args, capture_output=True, text=True)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"{args[0]}: not found"


def which(cmd):
    return shutil.which(cmd) is not None


def vpc_path(name):
    matches = glob.glob(f"/sys/bus/platform/devices/VPC2004:*/{name}")
    return matches[0] if matches else None


def read_file(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def run_helper(*args):
    rc, _, err = sh("pkexec", HELPER, *args)
    return rc == 0, err or "permission denied"


# --- Conservation Mode ---
def get_conservation_mode():
    return read_file(vpc_path("conservation_mode")) == "1"


def set_conservation_mode(active):
    return run_helper("conservation_mode", "on" if active else "off")


# --- Always-On USB ---
def get_usb_charging():
    return read_file(vpc_path("usb_charging")) == "1"


def set_usb_charging(active):
    return run_helper("usb_charging", "on" if active else "off")


# --- Fan Mode ---
def get_fan_mode():
    return FAN_MODE_VALUES.get(read_file(vpc_path("fan_mode")), "standard")


def set_fan_mode(key):
    return run_helper("fan_mode", key)


# --- FN Lock (0 = engaged/on, 1 = disengaged/off on this hardware) ---
def get_fn_lock():
    return read_file(vpc_path("fn_lock")) != "1"


def set_fn_lock(active):
    return run_helper("fn_lock", "on" if active else "off")


# --- Camera ---
def get_camera():
    _, out, _ = sh("lsmod")
    return "uvcvideo" in out


def set_camera(active):
    return run_helper("camera", "on" if active else "off")


# --- Microphone (unprivileged) ---
def get_mic_active():
    _, out, _ = sh("pactl", "get-source-mute", "@DEFAULT_SOURCE@")
    return "yes" not in out.lower()


def set_mic_active(active):
    rc, _, err = sh("pactl", "set-source-mute", "@DEFAULT_SOURCE@", "0" if active else "1")
    return rc == 0, err


# --- Touchpad (unprivileged) ---
def get_touchpad_id():
    rc, out, _ = sh("xinput", "list")
    if rc != 0:
        return None
    for line in out.splitlines():
        if "Touchpad" in line:
            match = re.search(r"id=(\d+)", line)
            if match:
                return match.group(1)
    return None


def get_touchpad_active(touchpad_id):
    _, out, _ = sh("xinput", "--list-props", touchpad_id)
    for line in out.splitlines():
        if "Device Enabled" in line:
            return line.split(":")[-1].strip() == "1"
    return True


def set_touchpad_active(touchpad_id, active):
    rc, _, err = sh("xinput", "enable" if active else "disable", touchpad_id)
    return rc == 0, err


# --- Wi-Fi (unprivileged) ---
def get_wifi_active():
    _, out, _ = sh("nmcli", "radio", "wifi")
    return out.strip() == "enabled"


def set_wifi_active(active):
    rc, _, err = sh("nmcli", "radio", "wifi", "on" if active else "off")
    return rc == 0, err


# --- Omarchy theme integration ---
def read_omarchy_colors():
    colors = {}
    try:
        with open(OMARCHY_COLORS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                colors[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        return None
    return colors or None


def contrast_color(hex_color):
    """Pick black or white text/border filler for readability against hex_color."""
    hex_color = hex_color.lstrip("#")
    try:
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError):
        return "#ffffff"
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#000000" if luminance > 0.6 else "#ffffff"


def apply_omarchy_style():
    """Restyle the app with sharp corners and the active Omarchy theme's accent color."""
    colors = read_omarchy_colors()
    if not colors:
        return

    accent = colors.get("accent", "#89b4fa")
    mode = colors.get("mode", "dark")
    accent_fg = contrast_color(accent)
    background = colors.get("background", "#1e1e2e")
    foreground = colors.get("foreground", "#cdd6f4")

    Adw.StyleManager.get_default().set_color_scheme(
        Adw.ColorScheme.FORCE_DARK if mode == "dark" else Adw.ColorScheme.FORCE_LIGHT
    )

    css = f"""
    @define-color accent_color {accent};
    @define-color accent_bg_color {accent};
    @define-color accent_fg_color {accent_fg};

    @define-color window_bg_color {background};
    @define-color window_fg_color {foreground};
    @define-color view_bg_color {background};
    @define-color view_fg_color {foreground};
    @define-color headerbar_bg_color {background};
    @define-color headerbar_fg_color {foreground};
    @define-color card_bg_color {background};
    @define-color card_fg_color {foreground};
    @define-color popover_bg_color {background};
    @define-color popover_fg_color {foreground};
    @define-color dialog_bg_color {background};
    @define-color dialog_fg_color {foreground};

    * {{
        border-radius: 0;
        font-family: monospace;
    }}

    .boxed-list,
    .boxed-list-separate {{
        box-shadow: none;
    }}

    .boxed-list > row,
    .boxed-list-separate > row {{
        border: 1px solid transparent;
    }}

    .boxed-list > row:hover,
    .boxed-list-separate > row:hover,
    .boxed-list > row.vantage-match,
    .boxed-list-separate > row.vantage-match {{
        background-color: alpha(black, 0.15);
        border-color: alpha(white, 0.25);
    }}

    .vantage-card {{
        padding: 10px;
    }}

    .vantage-header {{
        font-size: 1.05em;
        margin: 12px;
    }}

    toast {{
        border: 1px solid {accent};
    }}

    switch:checked {{
        background-color: {accent};
    }}
    """

    provider = Gtk.CssProvider()
    provider.load_from_string(css)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


class VantageWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Lenovo Vantage")
        self.set_default_size(420, 520)

        # Omarchy's own menu has no search box: you just start typing and
        # the header line shows the filter, with the best match highlighted
        # for an immediate Enter. Mirror that instead of a real search entry.
        self.filter_text = ""
        self.cursor_active = False
        self.selected_pos = 0
        self.rows = []

        toolbar_view = Adw.ToolbarView()

        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(self.build_content())
        toolbar_view.set_content(self.toast_overlay)

        self.set_content(toolbar_view)

        key_controller = Gtk.EventControllerKey()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)

    def matching_rows(self):
        return [row for row in self.rows if self.filter_row(row)]

    def filter_row(self, row):
        if not self.filter_text:
            return True
        return self.filter_text in getattr(row, "vantage_search_text", "")

    def refresh_filter(self):
        if hasattr(self, "header_label"):
            if self.filter_text:
                self.header_label.set_text(self.filter_text)
                self.header_label.set_opacity(1.0)
            else:
                self.header_label.set_text(f"{self.screen_title}…")
                self.header_label.set_opacity(0.58)
        if hasattr(self, "listbox"):
            self.listbox.invalidate_filter()
        matches = self.matching_rows()
        if not matches:
            self.cursor_active = False
            self.selected_pos = 0
        else:
            self.selected_pos = max(0, min(self.selected_pos, len(matches) - 1))
        self.apply_cursor_style(matches)

    def apply_cursor_style(self, matches):
        for row in self.rows:
            row.remove_css_class("vantage-match")
        if self.cursor_active and matches:
            matches[self.selected_pos].add_css_class("vantage-match")

    def move_cursor(self, delta):
        matches = self.matching_rows()
        if not matches:
            return
        if not self.cursor_active:
            self.cursor_active = True
            self.selected_pos = 0
        else:
            self.selected_pos = (self.selected_pos + delta) % len(matches)
        self.apply_cursor_style(matches)

    def activate_cursor(self):
        matches = self.matching_rows()
        if not matches:
            return
        if self.cursor_active:
            self.trigger_row(matches[self.selected_pos])
        else:
            self.cursor_active = True
            self.selected_pos = 0
            self.apply_cursor_style(matches)

    def trigger_row(self, row):
        activate = getattr(row, "vantage_activate", None)
        if activate:
            activate()
        elif isinstance(row, Adw.SwitchRow):
            row.set_active(not row.get_active())
        else:
            row.grab_focus()

    def on_key_pressed(self, _controller, keyval, _keycode, state):
        if keyval == Gdk.KEY_Escape:
            if self.filter_text:
                self.filter_text = ""
                self.refresh_filter()
            elif self.screen != "root":
                self.go_to_screen("root")
            else:
                self.close()
            return True

        if not self.rows:
            return False

        if keyval == Gdk.KEY_BackSpace:
            if self.filter_text:
                self.filter_text = self.filter_text[:-1]
                self.refresh_filter()
            elif self.screen != "root":
                self.go_to_screen("root")
            return True
        if keyval == Gdk.KEY_Up:
            self.move_cursor(-1)
            return True
        if keyval == Gdk.KEY_Down:
            self.move_cursor(1)
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.activate_cursor()
            return True

        if state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK):
            return False
        unicode_value = Gdk.keyval_to_unicode(keyval)
        if unicode_value:
            char = chr(unicode_value)
            if char.isprintable():
                self.filter_text += char
                self.refresh_filter()
                return True
        return False

    def notify(self, message):
        self.toast_overlay.add_toast(Adw.Toast(title=message, timeout=4))

    def add_switch(self, listbox, title, subtitle, get_fn, set_fn):
        row = Adw.SwitchRow(title=title, subtitle=subtitle)
        row.set_active(bool(get_fn()))
        row.vantage_search_text = f"{title} {subtitle}".lower()

        def on_notify(row, _pspec):
            desired = row.get_active()
            ok, err = set_fn(desired)
            if not ok:
                row.handler_block(handler_id)
                row.set_active(not desired)
                row.handler_unblock(handler_id)
                self.notify(f"{title}: {err}")

        handler_id = row.connect("notify::active", on_notify)
        listbox.append(row)
        self.rows.append(row)
        return row

    def add_navigation_row(self, listbox, title, subtitle, on_activate):
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        row.set_activatable(True)
        row.vantage_search_text = f"{title} {subtitle}".lower()
        row.vantage_activate = on_activate
        row.connect("activated", lambda _row: on_activate())
        listbox.append(row)
        self.rows.append(row)
        return row

    def add_fan_mode_row(self, listbox):
        current = get_fan_mode()
        label = next((l for l, k in FAN_MODES if k == current), "Standard")
        self.add_navigation_row(
            listbox, "Fan Mode", f"Currently: {label}",
            lambda: self.go_to_screen("fan_mode"),
        )

    def build_fan_mode_screen(self):
        current = get_fan_mode()
        for label, key in FAN_MODES:
            row = Adw.ActionRow(title=label)
            row.set_activatable(True)
            row.vantage_search_text = label.lower()
            if key == current:
                row.add_suffix(Gtk.Image.new_from_icon_name("object-select-symbolic"))

            def activate(key=key):
                ok, err = set_fan_mode(key)
                if not ok:
                    self.notify(f"Fan Mode: {err}")
                self.go_to_screen("root")

            row.vantage_activate = activate
            row.connect("activated", lambda _row, activate=activate: activate())
            self.listbox.append(row)
            self.rows.append(row)

    def populate_root_rows(self):
        has_any = False

        if vpc_path("conservation_mode"):
            self.add_switch(
                self.listbox, "Conservation Mode",
                "Limit battery charge to prolong its lifespan",
                get_conservation_mode, set_conservation_mode,
            )
            has_any = True
        if vpc_path("usb_charging"):
            self.add_switch(
                self.listbox, "Always-On USB",
                "Charge devices via USB while the laptop is off",
                get_usb_charging, set_usb_charging,
            )
            has_any = True
        if vpc_path("fan_mode"):
            self.add_fan_mode_row(self.listbox)
            has_any = True
        if vpc_path("fn_lock"):
            self.add_switch(
                self.listbox, "FN Lock",
                "Use F1-F12 as standard function keys",
                get_fn_lock, set_fn_lock,
            )
            has_any = True
        touchpad_id = get_touchpad_id()
        if touchpad_id:
            self.add_switch(
                self.listbox, "Touchpad",
                "Enable or disable the built-in touchpad",
                lambda: get_touchpad_active(touchpad_id),
                lambda active: set_touchpad_active(touchpad_id, active),
            )
            has_any = True
        if sh("modinfo", "-n", "uvcvideo")[0] == 0:
            self.add_switch(
                self.listbox, "Camera",
                "Physically enable or disable the webcam driver",
                get_camera, set_camera,
            )
            has_any = True
        if which("pactl"):
            self.add_switch(
                self.listbox, "Microphone",
                "Mute or unmute the default microphone",
                get_mic_active, set_mic_active,
            )
            has_any = True
        if which("nmcli"):
            self.add_switch(
                self.listbox, "Wi-Fi",
                "Turn the wireless radio on or off",
                get_wifi_active, set_wifi_active,
            )
            has_any = True

        return has_any

    def go_to_screen(self, screen):
        child = self.listbox.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.listbox.remove(child)
            child = next_child

        self.rows = []
        self.filter_text = ""
        self.cursor_active = False
        self.selected_pos = 0
        self.screen = screen

        if screen == "fan_mode":
            self.screen_title = "Fan Mode"
            self.build_fan_mode_screen()
        else:
            self.screen = "root"
            self.screen_title = "Lenovo Vantage"
            self.populate_root_rows()

        self.refresh_filter()

    def build_content(self):
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.listbox.add_css_class("boxed-list")
        self.listbox.set_filter_func(self.filter_row)

        self.screen = "root"
        self.screen_title = "Lenovo Vantage"
        has_any = self.populate_root_rows()

        if not has_any:
            return Adw.StatusPage(
                title="No supported hardware found",
                description="This device doesn't expose any known Lenovo Vantage controls.",
                icon_name="dialog-warning-symbolic",
            )

        self.header_label = Gtk.Label(label=f"{self.screen_title}…", xalign=0.0)
        self.header_label.add_css_class("vantage-header")
        self.header_label.set_opacity(0.58)
        self.header_label.set_ellipsize(Pango.EllipsizeMode.END)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        scroller.set_child(self.listbox)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add_css_class("vantage-card")
        box.append(self.header_label)
        box.append(scroller)
        return box


class VantageApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_startup(self):
        Adw.Application.do_startup(self)
        apply_omarchy_style()

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = VantageWindow(self)
        win.present()


def main():
    app = VantageApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
