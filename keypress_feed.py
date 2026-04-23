#!/usr/bin/env python3
"""
Keypress Feed Overlay
- Eingabezeile unten (groß, durch Linie getrennt) + Badge-Zähler
- Einträge wandern nach oben und gleiten per Slide-up raus
- Kein Opacity-Fade, direktes Slide-out
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import evdev
from evdev import ecodes
import threading
import time

# ── Konfiguration ──────────────────────────────────────────
WINDOW_WIDTH     = 300
WINDOW_HEIGHT    = 800
MAX_ENTRIES      = 18
DISAPPEAR_AFTER  = 2.5    # Sekunden bis Slide-out beginnt
SLIDE_DURATION   = 300    # Millisekunden für Slide-up
FONT_SIZE        = 15
INPUT_FONT_SIZE  = 22
BG_COLOR         = "#FFFFFF"
FG_COLOR         = "#111111"
DIVIDER_COLOR    = "#333333"
# ───────────────────────────────────────────────────────────

MODIFIERS = {
    ecodes.KEY_LEFTSHIFT:  "Shift",
    ecodes.KEY_RIGHTSHIFT: "Shift",
    ecodes.KEY_LEFTCTRL:   "Ctrl",
    ecodes.KEY_RIGHTCTRL:  "Ctrl",
    ecodes.KEY_LEFTALT:    "Alt",
    ecodes.KEY_RIGHTALT:   "AltGr",
    ecodes.KEY_LEFTMETA:   "Super",
    ecodes.KEY_RIGHTMETA:  "Super",
}

held_modifiers = set()


def keycode_to_name(code):
    name = ecodes.KEY.get(code, f"KEY_{code}")
    if isinstance(name, list):
        name = name[0]
    name = name.replace("KEY_", "")
    replacements = {
        "SPACE": "Space", "ENTER": "Enter", "BACKSPACE": "⌫",
        "TAB": "Tab", "ESCAPE": "Esc", "DELETE": "Del",
        "INSERT": "Ins", "HOME": "Home", "END": "End",
        "PAGEUP": "PgUp", "PAGEDOWN": "PgDn",
        "UP": "↑", "DOWN": "↓", "LEFT": "←", "RIGHT": "→",
        "CAPSLOCK": "CapsLock", "NUMLOCK": "NumLock",
        "F1": "F1", "F2": "F2", "F3": "F3", "F4": "F4",
        "F5": "F5", "F6": "F6", "F7": "F7", "F8": "F8",
        "F9": "F9", "F10": "F10", "F11": "F11", "F12": "F12",
    }
    return replacements.get(name, name.capitalize())


class FeedEntry:
    def __init__(self, text, feed_box, on_removed):
        self.text = text
        self.feed_box = feed_box
        self.on_removed = on_removed
        self.birth_time = time.time()
        self.sliding = False
        self.removed = False

        self.revealer = Gtk.Revealer()
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.revealer.set_transition_duration(SLIDE_DURATION)

        self.label = Gtk.Label(label=text)
        self.label.set_xalign(0)
        self.label.get_style_context().add_class("key-entry")
        self.revealer.add(self.label)

        feed_box.pack_end(self.revealer, False, False, 0)
        self.revealer.show_all()
        self.revealer.set_reveal_child(True)

    def slide_out(self):
        if self.sliding or self.removed:
            return
        self.sliding = True
        self.revealer.set_reveal_child(False)
        GLib.timeout_add(SLIDE_DURATION + 50, self._remove)

    def _remove(self):
        if not self.removed:
            self.removed = True
            self.feed_box.remove(self.revealer)
            self.on_removed(self)
        return False


class KeyFeedWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Key Feed")
        self.set_default_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.set_resizable(False)
        self.set_keep_above(True)
        self._input_time = 0
        self._current_key = ""
        self._key_count = 0

        css = f"""
        window {{
            background-color: {BG_COLOR};
        }}
        .key-entry {{
            font-size: {FONT_SIZE}pt;
            font-family: "Monospace";
            color: {FG_COLOR};
            padding: 3px 12px;
        }}
        .header {{
            font-size: 11pt;
            font-family: "Sans";
            color: #888888;
            padding: 8px 12px 4px 12px;
            border-bottom: 2px solid #DDDDDD;
        }}
        .input-line {{
            font-size: {INPUT_FONT_SIZE}pt;
            font-family: "Monospace";
            font-weight: bold;
            color: {FG_COLOR};
            padding: 10px 12px 10px 12px;
        }}
        .badge {{
            font-size: 13pt;
            font-family: "Sans";
            font-weight: bold;
            color: #FFFFFF;
            background-color: #111111;
            border-radius: 6px;
            padding: 2px 8px;
            margin: 8px 12px;
        }}
        .badge-hidden {{
            color: transparent;
            background-color: transparent;
        }}
        .divider {{
            background-color: {DIVIDER_COLOR};
            min-height: 2px;
        }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(outer)

        # Header
        header = Gtk.Label(label="⌨ Key Feed")
        header.get_style_context().add_class("header")
        header.set_xalign(0)
        outer.pack_start(header, False, False, 0)

        # Feed
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        outer.pack_start(self.scroll, True, True, 0)

        self.feed_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.feed_box.set_valign(Gtk.Align.END)
        self.scroll.add(self.feed_box)

        # Trennlinie
        divider = Gtk.Box()
        divider.get_style_context().add_class("divider")
        divider.set_size_request(-1, 2)
        outer.pack_start(divider, False, False, 0)

        # Eingabebereich: Taste + Badge nebeneinander
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        outer.pack_start(input_row, False, False, 0)

        self.input_label = Gtk.Label(label="")
        self.input_label.get_style_context().add_class("input-line")
        self.input_label.set_xalign(0)
        input_row.pack_start(self.input_label, True, True, 0)

        self.badge_label = Gtk.Label(label="1")
        self.badge_label.get_style_context().add_class("badge")
        self.badge_label.get_style_context().add_class("badge-hidden")
        self.badge_label.set_valign(Gtk.Align.CENTER)
        input_row.pack_end(self.badge_label, False, False, 0)

        self.entries = []

        GLib.timeout_add(200, self._check_timeouts)
        self.show_all()

    def _on_entry_removed(self, entry):
        if entry in self.entries:
            self.entries.remove(entry)

    def _update_badge(self):
        if self._key_count > 1:
            self.badge_label.set_text(str(self._key_count))
            ctx = self.badge_label.get_style_context()
            ctx.remove_class("badge-hidden")
            ctx.add_class("badge")
        else:
            ctx = self.badge_label.get_style_context()
            ctx.add_class("badge-hidden")

    def add_key(self, text):
        def _add():
            now = time.time()
            current = self.input_label.get_text()

            if current:
                if text == self._current_key:
                    # Gleiche Taste: Zähler erhöhen
                    self._key_count += 1
                    self._input_time = now
                    self._update_badge()
                    return False

                # Andere Taste: aktuellen Eintrag in Feed schieben
                entry = FeedEntry(current, self.feed_box, self._on_entry_removed)
                self.entries.append(entry)

                if len(self.entries) > MAX_ENTRIES:
                    self.entries[0].slide_out()

                adj = self.scroll.get_vadjustment()
                GLib.idle_add(lambda: adj.set_value(adj.get_upper()))

            # Neue Taste
            self.input_label.set_text(text)
            self._current_key = text
            self._key_count = 1
            self._input_time = now
            self._update_badge()
            return False

        GLib.idle_add(_add)

    def _check_timeouts(self):
        now = time.time()

        # Eingabezeile leeren wenn zu alt
        if self.input_label.get_text():
            if now - self._input_time > DISAPPEAR_AFTER:
                self.input_label.set_text("")
                self._current_key = ""
                self._key_count = 0
                self._update_badge()
                if self.entries:
                    self.entries[0].slide_out()

        # Feed-Einträge der Reihe nach rausschieben
        elif self.entries:
            oldest = self.entries[0]
            if not oldest.sliding and now - oldest.birth_time > DISAPPEAR_AFTER:
                oldest.slide_out()

        return True


def find_keyboard():
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for dev in devices:
        name = dev.name.lower()
        if "keyboard" in name and "mouse" not in name and "pointer" not in name:
            caps = dev.capabilities()
            if ecodes.EV_KEY in caps:
                keys = caps[ecodes.EV_KEY]
                if ecodes.KEY_A in keys and ecodes.KEY_SPACE in keys:
                    return dev
    for dev in devices:
        caps = dev.capabilities()
        if ecodes.EV_KEY in caps:
            keys = caps[ecodes.EV_KEY]
            if ecodes.KEY_A in keys and ecodes.KEY_SPACE in keys:
                return dev
    return None


def input_thread(window):
    dev = find_keyboard()
    if not dev:
        print("Kein Keyboard gefunden!")
        return
    print(f"Lese von: {dev.name} ({dev.path})")

    for event in dev.read_loop():
        if event.type != ecodes.EV_KEY:
            continue
        key_event = evdev.categorize(event)
        if event.code in MODIFIERS:
            if key_event.keystate in (key_event.key_down, key_event.key_hold):
                held_modifiers.add(event.code)
            else:
                held_modifiers.discard(event.code)
            continue
        if key_event.keystate != key_event.key_down:
            continue

        key_name = keycode_to_name(event.code)
        mods = []
        for mod_code in [ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL]:
            if mod_code in held_modifiers:
                mods.append("Ctrl"); break
        for mod_code in [ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT]:
            if mod_code in held_modifiers:
                mods.append("Shift"); break
        for mod_code in [ecodes.KEY_LEFTALT]:
            if mod_code in held_modifiers:
                mods.append("Alt"); break
        for mod_code in [ecodes.KEY_RIGHTALT]:
            if mod_code in held_modifiers:
                mods.append("AltGr"); break

        display = "+".join(mods) + "+" + key_name if mods else key_name
        window.add_key(display)


def main():
    win = KeyFeedWindow()
    win.connect("destroy", Gtk.main_quit)
    t = threading.Thread(target=input_thread, args=(win,), daemon=True)
    t.start()
    Gtk.main()


if __name__ == "__main__":
    main()
