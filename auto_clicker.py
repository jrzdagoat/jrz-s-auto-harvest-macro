"""Jrz's Auto Havest Drug Macro - FiveM focused macro."""

import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk
from pynput import mouse, keyboard

# ---------------------------------------------------------------------------
# Native Windows input backend
# ---------------------------------------------------------------------------
if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    INPUT_MOUSE = 0
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_SCANCODE = 0x0008
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_MIDDLEDOWN = 0x0020
    MOUSEEVENTF_MIDDLEUP = 0x0040

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                    ("wParamH", wintypes.WORD)]

    class INPUTUNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", INPUTUNION)]

    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    user32.SendInput.restype = wintypes.UINT
    user32.SetCursorPos.argtypes = (wintypes.INT, wintypes.INT)
    user32.SetCursorPos.restype = wintypes.BOOL
    user32.MapVirtualKeyW.argtypes = (wintypes.UINT, wintypes.UINT)
    user32.MapVirtualKeyW.restype = wintypes.UINT

    VK = {
        **{chr(i): i for i in range(ord("A"), ord("Z") + 1)},
        **{str(i): ord(str(i)) for i in range(10)},
        "SPACE": 0x20, "ENTER": 0x0D, "TAB": 0x09,
        "ESC": 0x1B, "ESCAPE": 0x1B, "BACKSPACE": 0x08,
        "SHIFT": 0x10, "CTRL": 0x11, "ALT": 0x12,
        "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27,
        "DELETE": 0x2E, "INSERT": 0x2D, "HOME": 0x24, "END": 0x23,
        "PAGEUP": 0x21, "PAGEDOWN": 0x22,
    }
    VK.update({f"F{i}": 0x6F + i for i in range(1, 13)})

    def _vk_from_key(key):
        if isinstance(key, int):
            return key
        # pynput KeyCode objects can expose the real Windows virtual-key code.
        # Prefer it so virtually any keyboard key (punctuation, numpad, etc.)
        # can be used, not just the predefined letters.
        vk = getattr(key, "vk", None)
        if vk:
            return vk
        if hasattr(key, "char") and key.char:
            return VK.get(key.char.upper())
        name = str(key).replace("Key.", "").upper()
        aliases = {"RETURN": "ENTER", "ESC": "ESCAPE", "SHIFT_L": "SHIFT",
                   "SHIFT_R": "SHIFT", "CTRL_L": "CTRL", "CTRL_R": "CTRL",
                   "ALT_L": "ALT", "ALT_R": "ALT"}
        return VK.get(aliases.get(name, name))

    def _send(inp):
        return user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 1

    def _native_mouse_click(button, clicks=1):
        down, up = {"Left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
                    "Right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
                    "Middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP)}[button]
        for i in range(clicks):
            _send(INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, down, 0, None)))
            _send(INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(0, 0, 0, up, 0, None)))
            if i + 1 < clicks:
                time.sleep(0.02)

    def _key_down_up(key, hold_ms=60):
        vk = _vk_from_key(key)
        if vk is None:
            return False
        scan = user32.MapVirtualKeyW(vk, 0)
        if scan:
            down = INPUT(type=INPUT_KEYBOARD,
                         ki=KEYBDINPUT(0, scan, KEYEVENTF_SCANCODE, 0, None))
            up = INPUT(type=INPUT_KEYBOARD,
                       ki=KEYBDINPUT(0, scan, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0, None))
        else:
            down = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(vk, 0, 0, 0, None))
            up = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, None))
        if not _send(down):
            return False
        # Long enough for FiveM/GTA's frame-based input polling, but short
        # enough that the next press can happen immediately after release.
        time.sleep(max(0.01, hold_ms / 1000.0))
        return _send(up)
else:
    def _native_mouse_click(button, clicks=1):
        ctl = mouse.Controller()
        ctl.click({"Left": mouse.Button.left, "Right": mouse.Button.right,
                   "Middle": mouse.Button.middle}[button], clicks)

    def _key_down_up(key, hold_ms=60):
        ctl = keyboard.Controller()
        ctl.press(key)
        time.sleep(max(0.01, hold_ms / 1000.0))
        ctl.release(key)
        return True

APP_TITLE = "Jrz Auto Harvest"
_BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(_BASE_DIR, "assets")
ICON_ICO = os.path.join(ASSETS_DIR, "icon.ico")
ICON_PNG = os.path.join(ASSETS_DIR, "icon.png")

# Simple modern dark palette
BG = "#080808"
CARD = "#101010"
CARD_2 = "#171717"
TEXT = "#f5f5f5"
MUTED = "#858585"
ACCENT = "#ffffff"
ACCENT_HOVER = "#dddddd"
RED = "#ffffff"
GREEN = "#ffffff"
BORDER = "#292929"

mouse_ctl = mouse.Controller()
MOUSE_BUTTONS = {"Left": mouse.Button.left, "Right": mouse.Button.right, "Middle": mouse.Button.middle}
KEY_NAME_OVERRIDES = {getattr(keyboard.Key, f"f{i}"): f"F{i}" for i in range(1, 13)}


def _key_label(key):
    if key in KEY_NAME_OVERRIDES:
        return KEY_NAME_OVERRIDES[key]
    try:
        return key.char.upper()
    except AttributeError:
        return str(key).replace("Key.", "").upper()


class AutoClicker(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.geometry("440x545")
        self._set_icon()

        self.running = False
        self.stop_event = threading.Event()
        self.worker = None

        self.action_type = tk.StringVar(value="fivem")
        self.fivem_key = tk.StringVar(value="E")
        self.fivem_key_obj = None
        self.fivem_key_char = "e"
        self.fivem_key_display = tk.StringVar(value="E")
        self.fivem_hold_ms = tk.IntVar(value=60)
        self.no_pause = tk.BooleanVar(value=True)
        self.mouse_button = tk.StringVar(value="Left")
        self.click_type = tk.StringVar(value="Single")
        self.cursor_mode = tk.StringVar(value="current")
        self.pick_x = tk.IntVar(value=0)
        self.pick_y = tk.IntVar(value=0)
        self.hours = tk.IntVar(value=0)
        self.mins = tk.IntVar(value=0)
        self.secs = tk.IntVar(value=0)
        self.millis = tk.IntVar(value=100)
        self.repeat_mode = tk.StringVar(value="until_stopped")
        self.repeat_times = tk.IntVar(value=1)
        self.random_offset = tk.BooleanVar(value=False)
        self.offset_ms = tk.IntVar(value=40)

        self.hotkey = keyboard.Key.f6
        self.hotkey_display = tk.StringVar(value="F6")
        self._listening_for_hotkey = False
        self._listening_for_key = False
        self._listening_for_fivem_key = False
        self._bound_key_obj = None
        self._bound_key_char = "f"
        self.bound_key_display = tk.StringVar(value="F")
        self._picking = False

        self.recorded_events = []
        self._recording = False
        self._record_listener = None
        self._build_ui()
        self._start_global_listener()

    def _set_icon(self):
        try:
            if os.name == "nt" and os.path.exists(ICON_ICO):
                self.iconbitmap(ICON_ICO)
            elif os.path.exists(ICON_PNG):
                self._icon_img = tk.PhotoImage(file=ICON_PNG)
                self.iconphoto(True, self._icon_img)
        except Exception:
            pass

    def _card(self, parent):
        return tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)

    def _label(self, parent, text, size=9, color=TEXT, bold=False):
        return tk.Label(parent, text=text, bg=CARD, fg=color,
                        font=("Segoe UI", size, "bold" if bold else "normal"))

    def _build_ui(self):
        root = tk.Frame(self, bg=BG)
        root.pack(fill="both", expand=True, padx=18, pady=16)

        # Minimal header
        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", pady=(0, 12))
        title_box = tk.Frame(header, bg=BG)
        title_box.pack(side="left")
        tk.Label(title_box, text="JRZ", bg=BG, fg=TEXT,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(title_box, text="Auto Harvest", bg=BG, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Frame(title_box, bg=TEXT, height=2, width=34).pack(anchor="w", pady=(5, 0))

        status_box = tk.Frame(header, bg=BG)
        status_box.pack(side="right", pady=(7, 0))
        self.status_dot = tk.Label(status_box, text="●", bg=BG, fg=MUTED,
                                   font=("Segoe UI", 9))
        self.status_dot.pack(side="left", padx=(0, 5))
        self.status_text = tk.Label(status_box, text="Stopped", bg=BG, fg=MUTED,
                                    font=("Segoe UI", 9, "bold"))
        self.status_text.pack(side="left")

        # ttk styling for the monochrome selectors
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Mono.TCombobox", fieldbackground=CARD_2, background=CARD_2,
                        foreground=TEXT, arrowcolor=TEXT, bordercolor=BORDER,
                        lightcolor=BORDER, darkcolor=BORDER, padding=5)
        style.map("Mono.TCombobox", fieldbackground=[("readonly", CARD_2)],
                  foreground=[("readonly", TEXT)], selectbackground=[("readonly", CARD_2)],
                  selectforeground=[("readonly", TEXT)])

        action = self._card(root)
        action.pack(fill="x", pady=(0, 9))
        top = tk.Frame(action, bg=CARD)
        top.pack(fill="x", padx=14, pady=(12, 7))
        self._label(top, "MODE", 8, MUTED, True).pack(side="left")
        ttk.Combobox(top, textvariable=self.action_type,
                     values=["fivem", "mouse", "key"], state="readonly", width=13,
                     style="Mono.TCombobox").pack(side="right")
        self.action_detail = tk.Frame(action, bg=CARD)
        self.action_detail.pack(fill="x", padx=14, pady=(0, 12))

        timing = self._card(root)
        timing.pack(fill="x", pady=(0, 9))
        row = tk.Frame(timing, bg=CARD)
        row.pack(fill="x", padx=14, pady=11)
        self._label(row, "INTERVAL", 8, MUTED, True).pack(side="left")
        for var, unit in ((self.millis, "MS"), (self.secs, "SEC")):
            tk.Spinbox(row, from_=0, to=9999, textvariable=var, width=5,
                       bg=CARD_2, fg=TEXT, insertbackground=TEXT, relief="flat",
                       buttonbackground=CARD_2, highlightthickness=1,
                       highlightbackground=BORDER, highlightcolor=TEXT,
                       justify="center").pack(side="right", padx=(4, 2))
            self._label(row, unit, 8, MUTED).pack(side="right")

        repeat = self._card(root)
        repeat.pack(fill="x", pady=(0, 12))
        rr = tk.Frame(repeat, bg=CARD)
        rr.pack(fill="x", padx=14, pady=10)
        self._label(rr, "REPEAT", 8, MUTED, True).pack(side="left")
        tk.Radiobutton(rr, text="Until stopped", variable=self.repeat_mode, value="until_stopped",
                       bg=CARD, fg=TEXT, selectcolor=CARD_2, activebackground=CARD,
                       activeforeground=TEXT, highlightthickness=0).pack(side="right")
        tk.Radiobutton(rr, text="Count", variable=self.repeat_mode, value="times",
                       bg=CARD, fg=TEXT, selectcolor=CARD_2, activebackground=CARD,
                       activeforeground=TEXT, highlightthickness=0).pack(side="right", padx=(0, 7))
        tk.Spinbox(rr, from_=1, to=99999, textvariable=self.repeat_times, width=5,
                   bg=CARD_2, fg=TEXT, insertbackground=TEXT, relief="flat",
                   highlightthickness=1, highlightbackground=BORDER,
                   highlightcolor=TEXT).pack(side="right", padx=(4, 4))

        buttons = tk.Frame(root, bg=BG)
        buttons.pack(fill="x")
        self.start_btn = tk.Button(buttons, text="START  •  F6", command=self.start,
                                   bg=ACCENT, fg="#080808", activebackground=ACCENT_HOVER,
                                   activeforeground="#080808", relief="flat", bd=0,
                                   font=("Segoe UI", 10, "bold"), height=2, cursor="hand2")
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.stop_btn = tk.Button(buttons, text="STOP", command=self.stop,
                                  bg=CARD_2, fg=MUTED, activebackground=BORDER,
                                  activeforeground=TEXT, relief="flat", bd=0,
                                  font=("Segoe UI", 10, "bold"), height=2,
                                  state="disabled", cursor="hand2")
        self.stop_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))

        lower = tk.Frame(root, bg=BG)
        lower.pack(fill="x", pady=(8, 0))
        tk.Button(lower, text="HOTKEY", command=self._open_hotkey_dialog,
                  bg=BG, fg=MUTED, activebackground=BG, activeforeground=TEXT,
                  relief="flat", bd=0, font=("Segoe UI", 8, "bold"), cursor="hand2").pack(side="left")
        tk.Button(lower, text="RECORD / PLAYBACK", command=self._open_record_dialog,
                  bg=BG, fg=MUTED, activebackground=BG, activeforeground=TEXT,
                  relief="flat", bd=0, font=("Segoe UI", 8, "bold"), cursor="hand2").pack(side="right")

        self._refresh_action_widgets()

    def _refresh_action_widgets(self):
        for w in self.action_detail.winfo_children():
            w.destroy()

        if self.action_type.get() == "fivem":
            row = tk.Frame(self.action_detail, bg=CARD)
            row.pack(fill="x")
            self._label(row, "Interaction key", 9).pack(side="left")
            tk.Button(row, textvariable=self.fivem_key_display, command=self._listen_for_fivem_key,
                      bg=ACCENT, fg="#080808", activebackground=ACCENT_HOVER,
                      activeforeground="#080808", relief="flat", bd=0, width=10,
                      cursor="hand2", font=("Segoe UI", 9, "bold")).pack(side="right")
            row2 = tk.Frame(self.action_detail, bg=CARD)
            row2.pack(fill="x", pady=(9, 0))
            self._label(row2, "Hold", 9).pack(side="left")
            tk.Spinbox(row2, from_=30, to=500, textvariable=self.fivem_hold_ms, width=6,
                       bg=CARD_2, fg=TEXT, insertbackground=TEXT, relief="flat",
                       buttonbackground=CARD_2, highlightthickness=1,
                       highlightbackground=BORDER, highlightcolor=TEXT).pack(side="right")
            self._label(row2, "milliseconds", 8, MUTED).pack(side="right", padx=(0, 7))
            tk.Checkbutton(row2, text="No pause", variable=self.no_pause,
                           bg=CARD, fg=TEXT, selectcolor=CARD_2, activebackground=CARD,
                           activeforeground=TEXT, highlightthickness=0).pack(side="left", padx=(12, 0))
            self._label(self.action_detail, "E is default • click the key box to choose any key",
                        8, MUTED).pack(anchor="w", pady=(7, 0))
        elif self.action_type.get() == "mouse":
            row = tk.Frame(self.action_detail, bg=CARD); row.pack(fill="x")
            self._label(row, "Mouse button", 9).pack(side="left")
            ttk.Combobox(row, textvariable=self.mouse_button, values=list(MOUSE_BUTTONS),
                         state="readonly", width=9, style="Mono.TCombobox").pack(side="right")
            row2 = tk.Frame(self.action_detail, bg=CARD); row2.pack(fill="x", pady=(7, 0))
            self._label(row2, "Click type", 9).pack(side="left")
            ttk.Combobox(row2, textvariable=self.click_type, values=["Single", "Double"],
                         state="readonly", width=9, style="Mono.TCombobox").pack(side="right")
        else:
            row = tk.Frame(self.action_detail, bg=CARD); row.pack(fill="x")
            self._label(row, "Key to press", 9).pack(side="left")
            tk.Button(row, textvariable=self.bound_key_display, command=self._listen_for_key,
                      bg=ACCENT, fg="#080808", activebackground=ACCENT_HOVER,
                      activeforeground="#080808", relief="flat", width=9,
                      cursor="hand2", font=("Segoe UI", 9, "bold")).pack(side="right")
    def _listen_for_fivem_key(self):
        self._listening_for_fivem_key = True
        self.fivem_key_display.set("Press any key…")

    def _listen_for_key(self):
        self.bound_key_display.set("Press key")
        self._listening_for_key = True

    def _on_capture_key(self, key):
        if self._listening_for_fivem_key:
            self._listening_for_fivem_key = False
            try:
                if getattr(key, "char", None):
                    self.fivem_key_char = key.char
                    self.fivem_key_obj = None
                    self.fivem_key.set(key.char.upper())
                    self.fivem_key_display.set(key.char.upper())
                else:
                    self.fivem_key_obj = key
                    self.fivem_key_char = ""
                    label = _key_label(key)
                    self.fivem_key.set(label)
                    self.fivem_key_display.set(label)
            except Exception:
                self.fivem_key_obj = key
                label = _key_label(key)
                self.fivem_key.set(label)
                self.fivem_key_display.set(label)
            return

        if not self._listening_for_key:
            return
        self._listening_for_key = False
        try:
            self._bound_key_char = key.char
            self._bound_key_obj = None
            self.bound_key_display.set(key.char.upper())
        except AttributeError:
            self._bound_key_obj = key
            self.bound_key_display.set(_key_label(key))

    def _pick_location(self):
        if self._picking:
            return
        self._picking = True
        def on_click(x, y, button, pressed):
            if pressed:
                self.after(0, lambda: (self.pick_x.set(x), self.pick_y.set(y)))
                return False
        listener = mouse.Listener(on_click=on_click)
        listener.daemon = True
        listener.start()

    def _open_hotkey_dialog(self):
        dlg = tk.Toplevel(self); dlg.title("Hotkey"); dlg.configure(bg=CARD); dlg.resizable(False, False)
        dlg.geometry("300x150"); dlg.transient(self)
        tk.Label(dlg, text="Start / Stop hotkey", bg=CARD, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(pady=(16, 6))
        display = tk.StringVar(value=self.hotkey_display.get())
        tk.Label(dlg, textvariable=display, bg=CARD, fg=ACCENT,
                 font=("Segoe UI", 15, "bold")).pack()
        waiting = {"value": False}
        holder = {"key": self.hotkey}
        def rebind():
            waiting["value"] = True; display.set("Press a key…")
        def on_press(key):
            if waiting["value"]:
                waiting["value"] = False; holder["key"] = key
                self.after(0, lambda: display.set(_key_label(key)))
        listener = keyboard.Listener(on_press=on_press); listener.daemon = True; listener.start()
        def save():
            self.hotkey = holder["key"]; self.hotkey_display.set(display.get())
            self.start_btn.config(text=f"START  •  {self.hotkey_display.get()}")
            listener.stop(); dlg.destroy()
        tk.Button(dlg, text="Rebind", command=rebind, bg=CARD_2, fg=TEXT,
                  relief="flat", width=10).pack(side="left", padx=(55, 5), pady=14)
        tk.Button(dlg, text="Save", command=save, bg=ACCENT, fg="white",
                  relief="flat", width=10).pack(side="left", padx=5, pady=14)
        dlg.protocol("WM_DELETE_WINDOW", lambda: (listener.stop(), dlg.destroy()))

    def _open_record_dialog(self):
        dlg = tk.Toplevel(self); dlg.title("Record / Playback"); dlg.configure(bg=CARD)
        dlg.resizable(False, False); dlg.geometry("330x210"); dlg.transient(self)
        tk.Label(dlg, text="Record / Playback", bg=CARD, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(pady=(16, 4))
        status = tk.StringVar(value=f"{len(self.recorded_events)} events recorded")
        tk.Label(dlg, textvariable=status, bg=CARD, fg=MUTED).pack(pady=8)
        def toggle_record():
            if not self._recording:
                self.recorded_events = []; self._recording = True; start = time.time()
                def on_click(x, y, button, pressed):
                    if pressed and self._recording:
                        self.recorded_events.append((time.time() - start, x, y, button))
                self._record_listener = mouse.Listener(on_click=on_click); self._record_listener.daemon = True
                self._record_listener.start(); record_btn.config(text="Stop recording", bg=RED); status.set("Recording…")
            else:
                self._recording = False
                if self._record_listener: self._record_listener.stop()
                record_btn.config(text="Start recording", bg=CARD_2); status.set(f"{len(self.recorded_events)} events recorded")
        def play():
            if not self.recorded_events or self._recording: return
            def run():
                last = 0
                for t, x, y, button in self.recorded_events:
                    time.sleep(max(0, t-last)); last = t
                    if os.name == "nt": user32.SetCursorPos(x, y)
                    name = {mouse.Button.left:"Left", mouse.Button.right:"Right", mouse.Button.middle:"Middle"}.get(button, "Left")
                    _native_mouse_click(name)
                self.after(0, lambda: status.set(f"{len(self.recorded_events)} events recorded"))
            threading.Thread(target=run, daemon=True).start()
        frame = tk.Frame(dlg, bg=CARD); frame.pack(pady=10)
        record_btn = tk.Button(frame, text="Start recording", command=toggle_record, bg=CARD_2, fg=TEXT,
                                relief="flat", width=15); record_btn.pack(side="left", padx=5)
        tk.Button(frame, text="Play back", command=play, bg=ACCENT, fg="white",
                  relief="flat", width=12).pack(side="left", padx=5)
        dlg.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, "_recording", False),
                                                   self._record_listener.stop() if self._record_listener else None,
                                                   dlg.destroy()))

    def _start_global_listener(self):
        def on_press(key):
            if self._listening_for_key or self._listening_for_fivem_key:
                self.after(0, self._on_capture_key, key); return
            if not self._listening_for_hotkey and key == self.hotkey:
                self.after(0, self.toggle)
        self._hotkey_listener = keyboard.Listener(on_press=on_press)
        self._hotkey_listener.daemon = True; self._hotkey_listener.start()

    def toggle(self):
        self.stop() if self.running else self.start()

    def start(self):
        if self.running: return
        interval = self.hours.get()*3600 + self.mins.get()*60 + self.secs.get() + self.millis.get()/1000
        if self.action_type.get() == "fivem" and self.no_pause.get():
            interval = 0
        elif interval <= 0:
            self.status_text.config(text="Set an interval")
            return
        self.running = True; self.stop_event.clear()
        self.start_btn.config(state="disabled"); self.stop_btn.config(state="normal", fg=TEXT)
        self.status_text.config(text="Running", fg=GREEN); self.status_dot.config(fg=GREEN)
        self.worker = threading.Thread(target=self._run_loop, args=(interval,), daemon=True); self.worker.start()

    def stop(self):
        if not self.running: return
        self.running = False; self.stop_event.set()
        self.start_btn.config(state="normal"); self.stop_btn.config(state="disabled", fg=MUTED)
        self.status_text.config(text="Stopped", fg=MUTED); self.status_dot.config(fg=MUTED)

    def _run_loop(self, interval):
        count = 0; limit = self.repeat_times.get() if self.repeat_mode.get() == "times" else None
        while not self.stop_event.is_set():
            self._fire_action(); count += 1
            if limit is not None and count >= limit:
                self.after(0, self.stop); break
            if interval > 0:
                wait = interval
                if self.random_offset.get():
                    import random
                    wait += random.uniform(0, self.offset_ms.get()/1000)
                self.stop_event.wait(wait)

    def _fire_action(self):
        mode = self.action_type.get()
        if mode == "fivem":
            key = self.fivem_key_obj if self.fivem_key_obj is not None else self.fivem_key_char
            _key_down_up(key, self.fivem_hold_ms.get())
        elif mode == "mouse":
            if self.cursor_mode.get() == "pick":
                user32.SetCursorPos(self.pick_x.get(), self.pick_y.get()) if os.name == "nt" else setattr(mouse_ctl, "position", (self.pick_x.get(), self.pick_y.get()))
            _native_mouse_click(self.mouse_button.get(), 2 if self.click_type.get() == "Double" else 1)
        else:
            key = self._bound_key_obj if self._bound_key_obj is not None else self._bound_key_char
            _key_down_up(key, 60)


if __name__ == "__main__":
    app = AutoClicker()
    app.mainloop()
