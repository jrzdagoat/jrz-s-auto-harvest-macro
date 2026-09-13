"""
Auto Clicker / Key Presser
---------------------------
A small desktop utility that repeatedly clicks a mouse button OR presses a
keyboard key at a set interval. Toggle between the two action types, set an
interval, choose how many times to repeat (or run until stopped), and start
it with a button or the F6 hotkey.

Dependencies: pynput
    pip install pynput

Build to a Windows .exe with PyInstaller (see .github/workflows/build.yml):
    pyinstaller --onefile --windowed --name AutoClicker auto_clicker.py
"""

import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

from pynput import mouse, keyboard

APP_TITLE = "Jrz's Auto Havest Drug Macro"
_BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(_BASE_DIR, "assets")
ICON_ICO = os.path.join(ASSETS_DIR, "icon.ico")
ICON_PNG = os.path.join(ASSETS_DIR, "icon.png")

# ---------------------------------------------------------------------------
# Colors / style - flat black & white theme
# ---------------------------------------------------------------------------
BG = "#ffffff"
PANEL_BG = "#ffffff"
BLUE = "#000000"       # accent, kept as var name for minimal diff, now black
TEXT = "#000000"
MUTED = "#5a5a5a"
BORDER = "#000000"

mouse_ctl = mouse.Controller()
kb_ctl = keyboard.Controller()

MOUSE_BUTTONS = {"Left": mouse.Button.left, "Right": mouse.Button.right, "Middle": mouse.Button.middle}


class AutoClicker(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.geometry("460x430")
        self._set_icon()

        # ---- state -------------------------------------------------------
        self.running = False
        self.stop_event = threading.Event()
        self.worker = None

        self.action_type = tk.StringVar(value="mouse")   # "mouse" or "key"
        self.mouse_button = tk.StringVar(value="Left")
        self.click_type = tk.StringVar(value="Single")
        self.bound_key = keyboard.Key.f6.name if False else "f6"  # placeholder, set below
        self.bound_key_display = tk.StringVar(value="F6")
        self._bound_key_obj = keyboard.KeyCode.from_char("f")  # default key press target
        self._bound_key_obj = None
        self._bound_key_char = "f"

        self.repeat_mode = tk.StringVar(value="until_stopped")  # "times" or "until_stopped"
        self.repeat_times = tk.IntVar(value=1)

        self.hours = tk.IntVar(value=0)
        self.mins = tk.IntVar(value=0)
        self.secs = tk.IntVar(value=5)          # <-- default interval: 5 seconds
        self.millis = tk.IntVar(value=0)

        self.random_offset = tk.BooleanVar(value=False)
        self.offset_ms = tk.IntVar(value=40)

        self._listening_for_key = False

        self._build_ui()
        self._start_hotkey_listener()

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
            pass  # missing/unsupported icon file shouldn't block the app

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _section(self, parent, title):
        # Flat, borderless section: a small bold caption + a thin rule,
        # instead of a boxed LabelFrame - simpler, monochrome look.
        frame = tk.Frame(parent, bg=PANEL_BG)
        tk.Label(
            frame, text=title.upper(), bg=PANEL_BG, fg=TEXT,
            font=("Segoe UI", 8, "bold")
        ).pack(anchor="w")
        tk.Frame(frame, bg=BORDER, height=1).pack(fill="x", pady=(2, 8))
        return frame

    def _spin(self, parent, var, width=5):
        return tk.Spinbox(
            parent, from_=0, to=999, textvariable=var, width=width,
            justify="center", relief="solid", bd=1,
            bg=PANEL_BG, fg=TEXT, buttonbackground=PANEL_BG,
            highlightbackground=BORDER, highlightthickness=1
        )

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # ---- Click interval -------------------------------------------------
        interval = self._section(self, "Click interval")
        interval.pack(fill="x", **pad)

        row = tk.Frame(interval, bg=PANEL_BG)
        row.pack(fill="x")
        for var, label in [(self.hours, "hours"), (self.mins, "mins"),
                            (self.secs, "secs"), (self.millis, "milliseconds")]:
            self._spin(row, var).pack(side="left", padx=(0, 4))
            tk.Label(row, text=label, bg=PANEL_BG, fg=TEXT).pack(side="left", padx=(0, 12))

        offset_row = tk.Frame(interval, bg=PANEL_BG)
        offset_row.pack(fill="x", pady=(8, 0))
        tk.Checkbutton(offset_row, text="Random offset", variable=self.random_offset,
                        bg=PANEL_BG, fg=TEXT, selectcolor=PANEL_BG).pack(side="left")
        self._spin(offset_row, self.offset_ms, width=6).pack(side="left", padx=(8, 4))
        tk.Label(offset_row, text="milliseconds", bg=PANEL_BG, fg=TEXT).pack(side="left")

        # ---- two-column area: Action | Click repeat -------------------------
        cols = tk.Frame(self, bg=BG)
        cols.pack(fill="x", padx=12, pady=6)

        action = self._section(cols, "Action")
        action.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        tk.Radiobutton(action, text="Mouse click", variable=self.action_type, value="mouse",
                        bg=PANEL_BG, fg=TEXT, selectcolor=PANEL_BG,
                        command=self._refresh_action_widgets).pack(anchor="w")
        tk.Radiobutton(action, text="Key press", variable=self.action_type, value="key",
                        bg=PANEL_BG, fg=TEXT, selectcolor=PANEL_BG,
                        command=self._refresh_action_widgets).pack(anchor="w")

        self.action_detail = tk.Frame(action, bg=PANEL_BG)
        self.action_detail.pack(fill="x", pady=(6, 0))
        self._refresh_action_widgets()

        repeat = self._section(cols, "Click repeat")
        repeat.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        rtop = tk.Frame(repeat, bg=PANEL_BG)
        rtop.pack(anchor="w")
        tk.Radiobutton(rtop, text="Repeat", variable=self.repeat_mode, value="times",
                        bg=PANEL_BG, fg=TEXT, selectcolor=PANEL_BG).pack(side="left")
        tk.Spinbox(rtop, from_=1, to=99999, textvariable=self.repeat_times, width=6,
                    justify="center", relief="solid", bd=1,
                    bg=PANEL_BG, fg=TEXT, buttonbackground=PANEL_BG,
                    highlightbackground=BORDER, highlightthickness=1).pack(side="left", padx=6)
        tk.Label(rtop, text="times", bg=PANEL_BG, fg=TEXT).pack(side="left")

        tk.Radiobutton(repeat, text="Repeat until stopped", variable=self.repeat_mode,
                        value="until_stopped", bg=PANEL_BG, fg=TEXT,
                        selectcolor=PANEL_BG).pack(anchor="w", pady=(4, 0))

        # ---- Hotkey row -------------------------------------------------
        hk = self._section(self, "Hotkey")
        hk.pack(fill="x", padx=12, pady=6)
        tk.Label(hk, text="Start / Stop hotkey:", bg=PANEL_BG, fg=TEXT).pack(side="left")
        tk.Label(hk, text="F6", bg=PANEL_BG, fg=TEXT, font=("Segoe UI", 9, "bold")).pack(side="left", padx=6)
        tk.Label(hk, text="(works even when unfocused)",
                 bg=PANEL_BG, fg=MUTED, font=("Segoe UI", 8)).pack(side="left")

        # ---- Buttons -------------------------------------------------
        btns = tk.Frame(self, bg=BG)
        btns.pack(fill="x", padx=12, pady=(10, 4))

        self.start_btn = tk.Button(
            btns, text="Start (F6)", command=self.start, bg="#000000", fg="#ffffff",
            relief="flat", bd=0, height=2, activebackground="#2a2a2a", activeforeground="#ffffff"
        )
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.stop_btn = tk.Button(
            btns, text="Stop (F6)", command=self.stop, bg=PANEL_BG, fg=MUTED,
            relief="solid", bd=1, height=2, state="disabled",
            highlightbackground=BORDER
        )
        self.stop_btn.pack(side="left", expand=True, fill="x", padx=(4, 0))

        # ---- Status / log -------------------------------------------------
        status = tk.Frame(self, bg=BG)
        status.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        self.status_var = tk.StringVar(value="Stopped")
        tk.Label(status, textvariable=self.status_var, bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")

    def _refresh_action_widgets(self):
        for w in self.action_detail.winfo_children():
            w.destroy()

        if self.action_type.get() == "mouse":
            row1 = tk.Frame(self.action_detail, bg=PANEL_BG)
            row1.pack(fill="x", pady=2)
            tk.Label(row1, text="Mouse button:", bg=PANEL_BG, fg=TEXT, width=12, anchor="w").pack(side="left")
            ttk.Combobox(row1, textvariable=self.mouse_button, values=list(MOUSE_BUTTONS),
                         state="readonly", width=10).pack(side="left")

            row2 = tk.Frame(self.action_detail, bg=PANEL_BG)
            row2.pack(fill="x", pady=2)
            tk.Label(row2, text="Click type:", bg=PANEL_BG, fg=TEXT, width=12, anchor="w").pack(side="left")
            ttk.Combobox(row2, textvariable=self.click_type, values=["Single", "Double"],
                         state="readonly", width=10).pack(side="left")
        else:
            row = tk.Frame(self.action_detail, bg=PANEL_BG)
            row.pack(fill="x", pady=2)
            tk.Label(row, text="Key to press:", bg=PANEL_BG, fg=TEXT, width=12, anchor="w").pack(side="left")
            self.key_btn = tk.Button(row, textvariable=self.bound_key_display,
                                      command=self._listen_for_key, width=10,
                                      relief="solid", bd=1)
            self.key_btn.pack(side="left")
            tk.Label(self.action_detail, text="Click, then press any key to bind it",
                     bg=PANEL_BG, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 0))

    # -----------------------------------------------------------------
    # Key binding capture
    # -----------------------------------------------------------------
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
            name = str(key).replace("Key.", "")
            self.bound_key_display.set(name.upper())

    # -----------------------------------------------------------------
    # Global F6 hotkey listener (works even when window unfocused)
    # -----------------------------------------------------------------
    def _start_hotkey_listener(self):
        def on_press(key):
            if self._listening_for_key:
                self._on_capture_key(key)
                return
            if key == keyboard.Key.f6:
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
        self.start_btn.config(state="disabled", bg="#555555")
        self.stop_btn.config(state="normal", fg=TEXT)
        self.status_var.set("Running…")

        self.worker = threading.Thread(target=self._run_loop, args=(interval,), daemon=True)
        self.worker.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.stop_event.set()
        self.start_btn.config(state="normal", bg="#000000")
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
