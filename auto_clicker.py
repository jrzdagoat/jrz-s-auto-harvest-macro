"""
Jrz's Auto Havest Drug Macro
-----------------------------
A small desktop auto-clicker. Set an interval, choose a click type / repeat
count, optionally lock clicks to a fixed screen position, start it with a
button or a rebindable hotkey (default F6), and record/play back simple
click macros.

Dependencies: pynput
    pip install pynput

Build to a Windows .exe with PyInstaller (see .github/workflows/build.yml):
    pyinstaller --onefile --windowed --name "JrzAutoHavestDrugMacro" \
        --icon assets/icon.ico --add-data "assets;assets" auto_clicker.py
"""

import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk

from pynput import mouse, keyboard

APP_TITLE = "Jrz's Auto Havest Drug Macro"
_BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(_BASE_DIR, "assets")
ICON_ICO = os.path.join(ASSETS_DIR, "icon.ico")
ICON_PNG = os.path.join(ASSETS_DIR, "icon.png")

# ---------------------------------------------------------------------------
# Colors / style - white panels, blue accents (matches the reference UI)
# ---------------------------------------------------------------------------
BG = "#f3f4f6"
PANEL_BG = "#ffffff"
BLUE = "#1a73e8"
TEXT = "#20242c"
MUTED = "#9aa0a8"
BORDER = "#e3e5e8"

mouse_ctl = mouse.Controller()
kb_ctl = keyboard.Controller()

MOUSE_BUTTONS = {"Left": mouse.Button.left, "Right": mouse.Button.right, "Middle": mouse.Button.middle}

KEY_NAME_OVERRIDES = {
    keyboard.Key.f1: "F1", keyboard.Key.f2: "F2", keyboard.Key.f3: "F3",
    keyboard.Key.f4: "F4", keyboard.Key.f5: "F5", keyboard.Key.f6: "F6",
    keyboard.Key.f7: "F7", keyboard.Key.f8: "F8", keyboard.Key.f9: "F9",
    keyboard.Key.f10: "F10", keyboard.Key.f11: "F11", keyboard.Key.f12: "F12",
}


def _key_label(key):
    if key in KEY_NAME_OVERRIDES:
        return KEY_NAME_OVERRIDES[key]
    try:
        return key.char.upper()
    except AttributeError:
        return str(key).replace("Key.", "").upper()


class RoundPanel(tk.Frame):
    """A plain white card-style panel (flat borders approximate the
    rounded-corner cards in the reference design - real rounded corners
    aren't available with stock tkinter widgets)."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=PANEL_BG, highlightbackground=BORDER,
                          highlightthickness=1, bd=0, **kwargs)


class AutoClicker(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.geometry("460x560")
        self._set_icon()

        # ---- state -------------------------------------------------------
        self.running = False
        self.stop_event = threading.Event()
        self.worker = None

        self.action_type = tk.StringVar(value="mouse")  # "mouse" or "key"
        self.mouse_button = tk.StringVar(value="Left")
        self.click_type = tk.StringVar(value="Single")

        self._bound_key_obj = None
        self._bound_key_char = "f"
        self.bound_key_display = tk.StringVar(value="F")
        self._listening_for_key = False

        self.repeat_mode = tk.StringVar(value="until_stopped")  # "times" or "until_stopped"
        self.repeat_times = tk.IntVar(value=1)

        self.hours = tk.IntVar(value=0)
        self.mins = tk.IntVar(value=0)
        self.secs = tk.IntVar(value=0)
        self.millis = tk.IntVar(value=100)

        self.random_offset = tk.BooleanVar(value=False)
        self.offset_ms = tk.IntVar(value=40)

        self.cursor_mode = tk.StringVar(value="current")  # "current" or "pick"
        self.pick_x = tk.IntVar(value=0)
        self.pick_y = tk.IntVar(value=0)
        self._picking = False

        self.hotkey = keyboard.Key.f6
        self.hotkey_display = tk.StringVar(value="F6")
        self._listening_for_hotkey = False

        # simple click-macro recorder
        self.recorded_events = []
        self._recording = False
        self._record_start = None
        self._record_listener = None

        self._build_ui()
        self._start_global_listener()

    # -----------------------------------------------------------------
    # Icon
    # -----------------------------------------------------------------
    def _set_icon(self):
        try:
            if os.name == "nt" and os.path.exists(ICON_ICO):
                self.iconbitmap(ICON_ICO)
            elif os.path.exists(ICON_PNG):
                self._icon_img = tk.PhotoImage(file=ICON_PNG)
                self.iconphoto(True, self._icon_img)
        except Exception:
            pass

    # -----------------------------------------------------------------
    # UI helpers
    # -----------------------------------------------------------------
    def _heading(self, parent, text):
        tk.Label(parent, text=text, bg=PANEL_BG, fg=BLUE,
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(10, 6))

    def _spin(self, parent, var, width=5):
        return tk.Spinbox(
            parent, from_=0, to=999, textvariable=var, width=width,
            justify="center", relief="solid", bd=1,
            bg=PANEL_BG, fg=TEXT, buttonbackground=PANEL_BG
        )

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # ---- Click interval -------------------------------------------------
        interval = RoundPanel(self)
        interval.pack(fill="x", **pad)
        self._heading(interval, "Click interval")

        row = tk.Frame(interval, bg=PANEL_BG)
        row.pack(fill="x", padx=12)
        for var, label in [(self.hours, "hours"), (self.mins, "mins"),
                            (self.secs, "secs"), (self.millis, "milliseconds")]:
            self._spin(row, var).pack(side="left", padx=(0, 4))
            tk.Label(row, text=label, bg=PANEL_BG, fg=TEXT).pack(side="left", padx=(0, 10))

        offset_row = tk.Frame(interval, bg=PANEL_BG)
        offset_row.pack(fill="x", padx=12, pady=(8, 12))
        tk.Checkbutton(offset_row, text="Random offset", variable=self.random_offset,
                        bg=PANEL_BG, fg=TEXT, selectcolor=PANEL_BG,
                        activebackground=PANEL_BG, highlightthickness=0).pack(side="left")
        self._spin(offset_row, self.offset_ms, width=6).pack(side="left", padx=(8, 4))
        tk.Label(offset_row, text="milliseconds", bg=PANEL_BG, fg=TEXT).pack(side="left")

        # ---- two-column area: Click options | Click repeat -------------------------
        cols = tk.Frame(self, bg=BG)
        cols.pack(fill="x", padx=12, pady=6)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        options = RoundPanel(cols)
        options.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._heading(options, "Click options")

        toggle_row = tk.Frame(options, bg=PANEL_BG)
        toggle_row.pack(fill="x", padx=12, pady=(0, 6))
        tk.Radiobutton(toggle_row, text="Mouse click", variable=self.action_type, value="mouse",
                        bg=PANEL_BG, fg=TEXT, selectcolor=PANEL_BG, activebackground=PANEL_BG,
                        highlightthickness=0, command=self._refresh_action_widgets).pack(anchor="w")
        tk.Radiobutton(toggle_row, text="Key press", variable=self.action_type, value="key",
                        bg=PANEL_BG, fg=TEXT, selectcolor=PANEL_BG, activebackground=PANEL_BG,
                        highlightthickness=0, command=self._refresh_action_widgets).pack(anchor="w")

        self.action_detail = tk.Frame(options, bg=PANEL_BG)
        self.action_detail.pack(fill="x", padx=12, pady=(2, 12))

        repeat = RoundPanel(cols)
        repeat.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._heading(repeat, "Click repeat")

        rtop = tk.Frame(repeat, bg=PANEL_BG)
        rtop.pack(anchor="w", padx=12)
        tk.Radiobutton(rtop, text="Repeat", variable=self.repeat_mode, value="times",
                        bg=PANEL_BG, fg=TEXT, selectcolor=PANEL_BG,
                        activebackground=PANEL_BG, highlightthickness=0).pack(side="left")
        tk.Spinbox(rtop, from_=1, to=99999, textvariable=self.repeat_times, width=5,
                    justify="center", relief="solid", bd=1,
                    bg=PANEL_BG, fg=TEXT, buttonbackground=PANEL_BG).pack(side="left", padx=4)
        tk.Label(rtop, text="times", bg=PANEL_BG, fg=TEXT).pack(side="left")

        tk.Radiobutton(repeat, text="Repeat until stopped", variable=self.repeat_mode,
                        value="until_stopped", bg=PANEL_BG, fg=TEXT, selectcolor=PANEL_BG,
                        activebackground=PANEL_BG, highlightthickness=0
                        ).pack(anchor="w", padx=12, pady=(4, 12))

        # ---- Cursor position -------------------------------------------------
        cursor = RoundPanel(self)
        cursor.pack(fill="x", **pad)
        self._heading(cursor, "Cursor position")

        crow = tk.Frame(cursor, bg=PANEL_BG)
        crow.pack(fill="x", padx=12, pady=(0, 12))
        tk.Radiobutton(crow, text="Current location", variable=self.cursor_mode, value="current",
                        bg=PANEL_BG, fg=TEXT, selectcolor=PANEL_BG,
                        activebackground=PANEL_BG, highlightthickness=0).pack(side="left")
        tk.Radiobutton(crow, text="", variable=self.cursor_mode, value="pick",
                        bg=PANEL_BG, fg=TEXT, selectcolor=PANEL_BG,
                        activebackground=PANEL_BG, highlightthickness=0).pack(side="left", padx=(14, 0))
        self.pick_btn = tk.Button(crow, text="Pick location", command=self._pick_location,
                                    bg=PANEL_BG, fg=TEXT, relief="solid", bd=1)
        self.pick_btn.pack(side="left")
        tk.Label(crow, text="X", bg=PANEL_BG, fg=TEXT).pack(side="left", padx=(12, 2))
        tk.Entry(crow, textvariable=self.pick_x, width=5, relief="solid", bd=1,
                  state="readonly", justify="center").pack(side="left")
        tk.Label(crow, text="Y", bg=PANEL_BG, fg=TEXT).pack(side="left", padx=(8, 2))
        tk.Entry(crow, textvariable=self.pick_y, width=5, relief="solid", bd=1,
                  state="readonly", justify="center").pack(side="left")

        # ---- Buttons -------------------------------------------------
        btns = tk.Frame(self, bg=BG)
        btns.pack(fill="x", padx=12, pady=(4, 4))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)

        self.start_btn = tk.Button(
            btns, text=f"Start ({self.hotkey_display.get()})", command=self.start,
            bg=PANEL_BG, fg=BLUE, relief="solid", bd=1, height=2, activebackground="#eaf1fd"
        )
        self.start_btn.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))

        self.stop_btn = tk.Button(
            btns, text=f"Stop ({self.hotkey_display.get()})", command=self.stop,
            bg=PANEL_BG, fg=MUTED, relief="solid", bd=1, height=2, state="disabled"
        )
        self.stop_btn.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 4))

        tk.Button(btns, text="Hotkey setting", command=self._open_hotkey_dialog,
                   bg=PANEL_BG, fg=TEXT, relief="solid", bd=1, height=2
                   ).grid(row=1, column=0, sticky="nsew", padx=(0, 4))

        tk.Button(btns, text="Record && Playback", command=self._open_record_dialog,
                   bg=PANEL_BG, fg=TEXT, relief="solid", bd=1, height=2
                   ).grid(row=1, column=1, sticky="nsew", padx=(4, 0))

        # ---- Status -------------------------------------------------
        status = tk.Frame(self, bg=BG)
        status.pack(fill="both", expand=True, padx=12, pady=(8, 12))
        self.status_var = tk.StringVar(value="Stopped")
        tk.Label(status, textvariable=self.status_var, bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")

        self._refresh_action_widgets()

    # -----------------------------------------------------------------
    # Mouse click vs. key press detail widgets
    # -----------------------------------------------------------------
    def _refresh_action_widgets(self):
        for w in self.action_detail.winfo_children():
            w.destroy()

        if self.action_type.get() == "mouse":
            row1 = tk.Frame(self.action_detail, bg=PANEL_BG)
            row1.pack(fill="x", pady=2)
            tk.Label(row1, text="Mouse button:", bg=PANEL_BG, fg=TEXT, width=12, anchor="w").pack(side="left")
            ttk.Combobox(row1, textvariable=self.mouse_button, values=list(MOUSE_BUTTONS),
                         state="readonly", width=9).pack(side="left")

            row2 = tk.Frame(self.action_detail, bg=PANEL_BG)
            row2.pack(fill="x", pady=2)
            tk.Label(row2, text="Click type:", bg=PANEL_BG, fg=TEXT, width=12, anchor="w").pack(side="left")
            ttk.Combobox(row2, textvariable=self.click_type, values=["Single", "Double"],
                         state="readonly", width=9).pack(side="left")
        else:
            row = tk.Frame(self.action_detail, bg=PANEL_BG)
            row.pack(fill="x", pady=2)
            tk.Label(row, text="Key to press:", bg=PANEL_BG, fg=TEXT, width=12, anchor="w").pack(side="left")
            self.key_btn = tk.Button(row, textvariable=self.bound_key_display,
                                       command=self._listen_for_key, width=9,
                                       relief="solid", bd=1, bg=PANEL_BG, fg=TEXT)
            self.key_btn.pack(side="left")
            tk.Label(self.action_detail, text="Click, then press any key to bind it",
                     bg=PANEL_BG, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 0))

    def _listen_for_key(self):
        self.bound_key_display.set("Press a key…")
        self._listening_for_key = True

    def _on_capture_key(self, key):
        if not self._listening_for_key:
            return
        self._listening_for_key = False
        try:
            char = key.char
            self._bound_key_char = char
            self._bound_key_obj = None
            self.bound_key_display.set(char.upper() if char else str(key))
        except AttributeError:
            self._bound_key_obj = key
            self.bound_key_display.set(_key_label(key))

    # -----------------------------------------------------------------
    # Cursor position picking
    # -----------------------------------------------------------------
    def _pick_location(self):
        if self._picking:
            return
        self._picking = True
        self.pick_btn.config(text="Click anywhere…", state="disabled")

        def on_click(x, y, button, pressed):
            if pressed:
                self.after(0, self._finish_pick, x, y)
                return False  # stop listener after first click

        listener = mouse.Listener(on_click=on_click)
        listener.daemon = True
        listener.start()

    def _finish_pick(self, x, y):
        self.pick_x.set(x)
        self.pick_y.set(y)
        self.cursor_mode.set("pick")
        self.pick_btn.config(text="Pick location", state="normal")
        self._picking = False

    # -----------------------------------------------------------------
    # Hotkey rebinding
    # -----------------------------------------------------------------
    def _open_hotkey_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Hotkey setting")
        dlg.configure(bg=PANEL_BG)
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.geometry("300x140")

        tk.Label(dlg, text="Start / Stop hotkey", bg=PANEL_BG, fg=TEXT,
                  font=("Segoe UI", 10, "bold")).pack(pady=(16, 8))

        key_display = tk.StringVar(value=self.hotkey_display.get())
        key_lbl = tk.Label(dlg, textvariable=key_display, bg=PANEL_BG, fg=BLUE,
                             font=("Segoe UI", 14, "bold"))
        key_lbl.pack(pady=4)

        hint = tk.StringVar(value='Click "Rebind", then press any key.')
        tk.Label(dlg, textvariable=hint, bg=PANEL_BG, fg=MUTED,
                  font=("Segoe UI", 8)).pack(pady=(0, 8))

        self._listening_for_hotkey = False
        new_key_holder = {"key": self.hotkey}

        def start_rebind():
            self._listening_for_hotkey = True
            key_display.set("Press a key…")
            hint.set("Waiting for a key press…")

        def apply_and_close():
            self.hotkey = new_key_holder["key"]
            self.hotkey_display.set(key_display.get())
            self.start_btn.config(text=f"Start ({self.hotkey_display.get()})")
            self.stop_btn.config(text=f"Stop ({self.hotkey_display.get()})")
            dlg._local_listener.stop()
            dlg.destroy()

        def on_press(key):
            if not self._listening_for_hotkey:
                return
            self._listening_for_hotkey = False
            new_key_holder["key"] = key
            self.after(0, lambda: (key_display.set(_key_label(key)),
                                    hint.set('Click "Rebind" to change again.')))

        dlg._local_listener = keyboard.Listener(on_press=on_press)
        dlg._local_listener.daemon = True
        dlg._local_listener.start()

        def on_close():
            dlg._local_listener.stop()
            dlg.destroy()
        dlg.protocol("WM_DELETE_WINDOW", on_close)

        btn_row = tk.Frame(dlg, bg=PANEL_BG)
        btn_row.pack(pady=(4, 12))
        tk.Button(btn_row, text="Rebind", command=start_rebind,
                   bg=PANEL_BG, fg=TEXT, relief="solid", bd=1).pack(side="left", padx=6)
        tk.Button(btn_row, text="Save", command=apply_and_close,
                   bg=BLUE, fg="#ffffff", relief="flat", bd=0).pack(side="left", padx=6)

    # -----------------------------------------------------------------
    # Record & Playback (simple click macro)
    # -----------------------------------------------------------------
    def _open_record_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Record & Playback")
        dlg.configure(bg=PANEL_BG)
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.geometry("320x220")

        tk.Label(dlg, text="Record & Playback", bg=PANEL_BG, fg=TEXT,
                  font=("Segoe UI", 10, "bold")).pack(pady=(16, 4))
        tk.Label(dlg, text="Records your mouse clicks (position + timing)\nso you can play them back.",
                  bg=PANEL_BG, fg=MUTED, font=("Segoe UI", 8), justify="center").pack(pady=(0, 10))

        status_var = tk.StringVar(value=f"{len(self.recorded_events)} events recorded")
        tk.Label(dlg, textvariable=status_var, bg=PANEL_BG, fg=BLUE,
                  font=("Segoe UI", 9, "bold")).pack(pady=(0, 10))

        def refresh_status():
            status_var.set(f"{len(self.recorded_events)} events recorded")

        def toggle_record():
            if not self._recording:
                self.recorded_events = []
                self._recording = True
                self._record_start = time.time()
                record_btn.config(text="Stop recording", bg="#e8484d", fg="#ffffff")
                status_var.set("Recording… click anywhere")

                def on_click(x, y, button, pressed):
                    if pressed and self._recording:
                        t = time.time() - self._record_start
                        self.recorded_events.append((t, x, y, button))

                self._record_listener = mouse.Listener(on_click=on_click)
                self._record_listener.daemon = True
                self._record_listener.start()
            else:
                self._recording = False
                if self._record_listener:
                    self._record_listener.stop()
                record_btn.config(text="Start recording", bg=PANEL_BG, fg=TEXT)
                refresh_status()

        def play_back():
            if not self.recorded_events or self._recording:
                return
            play_btn.config(state="disabled")
            status_var.set("Playing back…")

            def run():
                last_t = 0.0
                for t, x, y, button in self.recorded_events:
                    time.sleep(max(0.0, t - last_t))
                    last_t = t
                    mouse_ctl.position = (x, y)
                    mouse_ctl.click(button, 1)
                self.after(0, lambda: (play_btn.config(state="normal"), refresh_status()))

            threading.Thread(target=run, daemon=True).start()

        btn_row = tk.Frame(dlg, bg=PANEL_BG)
        btn_row.pack(pady=6)
        record_btn = tk.Button(btn_row, text="Start recording", command=toggle_record,
                                 bg=PANEL_BG, fg=TEXT, relief="solid", bd=1, width=14)
        record_btn.pack(side="left", padx=6)
        play_btn = tk.Button(btn_row, text="Play back", command=play_back,
                               bg=BLUE, fg="#ffffff", relief="flat", bd=0, width=12)
        play_btn.pack(side="left", padx=6)

        def on_close():
            self._recording = False
            if self._record_listener:
                self._record_listener.stop()
            dlg.destroy()
        dlg.protocol("WM_DELETE_WINDOW", on_close)

    # -----------------------------------------------------------------
    # Global hotkey listener (works even when window unfocused)
    # -----------------------------------------------------------------
    def _start_global_listener(self):
        def on_press(key):
            if self._listening_for_key:
                self.after(0, self._on_capture_key, key)
                return
            if self._listening_for_hotkey:
                return  # handled by the hotkey-setting dialog's own listener
            if key == self.hotkey:
                self.after(0, self.toggle)

        self._hotkey_listener = keyboard.Listener(on_press=on_press)
        self._hotkey_listener.daemon = True
        self._hotkey_listener.start()

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    # -----------------------------------------------------------------
    # Start / stop
    # -----------------------------------------------------------------
    def start(self):
        if self.running:
            return
        interval = (
            self.hours.get() * 3600
            + self.mins.get() * 60
            + self.secs.get()
            + self.millis.get() / 1000.0
        )
        if interval <= 0:
            self.status_var.set("Set an interval greater than 0 first.")
            return

        self.running = True
        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal", fg=TEXT)
        self.status_var.set("Running…")

        self.worker = threading.Thread(target=self._run_loop, args=(interval,), daemon=True)
        self.worker.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.stop_event.set()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled", fg=MUTED)
        self.status_var.set("Stopped")

    def _run_loop(self, interval):
        count = 0
        limit = None
        if self.repeat_mode.get() == "times":
            limit = self.repeat_times.get()

        while not self.stop_event.is_set():
            self._fire_action()
            count += 1
            self.after(0, lambda c=count: self.status_var.set(f"Running… ({c} triggered)"))

            if limit is not None and count >= limit:
                self.after(0, self.stop)
                break

            wait = interval
            if self.random_offset.get():
                import random
                wait += random.uniform(0, self.offset_ms.get() / 1000.0)
            self.stop_event.wait(wait)

    def _fire_action(self):
        if self.action_type.get() == "mouse":
            if self.cursor_mode.get() == "pick":
                mouse_ctl.position = (self.pick_x.get(), self.pick_y.get())
            btn = MOUSE_BUTTONS[self.mouse_button.get()]
            clicks = 2 if self.click_type.get() == "Double" else 1
            mouse_ctl.click(btn, clicks)
        else:
            if self._bound_key_obj is not None:
                kb_ctl.press(self._bound_key_obj)
                kb_ctl.release(self._bound_key_obj)
            else:
                kb_ctl.press(self._bound_key_char)
                kb_ctl.release(self._bound_key_char)


if __name__ == "__main__":
    app = AutoClicker()
    app.mainloop()
