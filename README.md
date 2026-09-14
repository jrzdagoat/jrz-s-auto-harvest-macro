# Jrz Auto Harvest

Simple FiveM/GTA V-focused desktop macro.

### FiveM mode
- Default interaction key: **E**
- Default hold: **60 ms**
- **No pause between E presses** is enabled by default.
- The macro releases E and immediately starts the next E press. This removes the artificial interval/pause from the previous version.

If the server/resource itself has a collection cooldown, the macro cannot remove that server-side delay.

### Run
```bash
pip install -r requirements.txt
python auto_clicker.py
```

### Build
```bash
pyinstaller --onefile --windowed --name "JrzAutoHavestDrugMacro" --icon assets/icon.ico --add-data "assets;assets" auto_clicker.py
```
