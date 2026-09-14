# Jrz's Auto Havest Drug Macro

FiveM/GTA V-friendly desktop macro for repeating mouse clicks or keyboard interactions.

## FiveM world interaction mode

If the drug pickup point is a GTA/FiveM world interaction rather than a UI button, use **FiveM interaction** in Click options. It sends a keyboard interaction event (default **E**) instead of a Windows mouse click. You can choose another common interaction key from the dropdown.

This is useful for servers/resources where the interaction is triggered by a key such as E. It does not bypass server-side anti-cheat or resource-specific interaction systems.

## Run

```bash
pip install -r requirements.txt
python auto_clicker.py
```

## Build

```bash
pyinstaller --onefile --windowed --name "JrzAutoHavestDrugMacro" --icon assets/icon.ico --add-data "assets;assets" auto_clicker.py
```
