# Jrz's Auto Havest Drug Macro

A Windows desktop auto-clicker with a native Windows `SendInput` backend for mouse and keyboard actions. This is intended to improve compatibility with GTA V/FiveM compared with using `pynput.Controller` for the actual game input.

## FiveM/GTA V input

On Windows, mouse clicks and key presses are sent through the native Win32 `SendInput` API. Cursor positioning uses `SetCursorPos`.

The global hotkey and recording UI still use `pynput` listeners because they are used for detecting input rather than injecting the game action.

### Important

FiveM servers/resources can implement their own input handling or anti-automation measures. No desktop macro can guarantee that every server will accept synthetic input.

## Run from source

```powershell
pip install -r requirements.txt
python auto_clicker.py
```

## Build the Windows EXE

```powershell
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed --name "JrzAutoHavestDrugMacro" --icon assets/icon.ico --add-data "assets;assets" auto_clicker.py
```
