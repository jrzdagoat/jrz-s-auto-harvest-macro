# Auto Clicker

A small Windows desktop utility that repeats a mouse click or a key press at
a set interval. Switch between "Mouse click" and "Key press", set the
interval (defaults to 5 seconds), choose to repeat a fixed number of times
or until stopped, and start/stop it with a button or the **F6** hotkey
(which works even if the window isn't focused).

## Run it directly (any OS, needs Python)

```bash
pip install -r requirements.txt
python auto_clicker.py
```

## Turn it into a Windows .exe with GitHub Actions (no local build needed)

This repo already includes a workflow at `.github/workflows/build.yml` that
builds the `.exe` for you on GitHub's own Windows servers — you don't need
Windows or Python installed locally.

1. **Create a new repository on GitHub** (github.com → New repository).
2. **Add these files to it**, keeping the folder structure:
   ```
   auto_clicker.py
   requirements.txt
   .github/workflows/build.yml
   ```
   Easiest way: on the repo page, click "Add file" → "Upload files", drag in
   `auto_clicker.py` and `requirements.txt`, then create the
   `.github/workflows/build.yml` file the same way (GitHub will let you type
   the path including folders when you use "Create new file" instead).
3. Commit the files to the `main` branch.
4. Go to the **Actions** tab of your repo. A workflow run called
   "Build Windows EXE" will start automatically (or click **Run workflow**
   if it didn't).
5. When it finishes (green check), open the run, scroll to **Artifacts**,
   and download **AutoClicker-windows-exe** — it's a zip containing
   `AutoClicker.exe`.

If you'd rather do it from your own machine with `git`:

```bash
git init
git add .
git commit -m "Add Auto Clicker"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

Then follow steps 4–5 above.

### Optional: attach the .exe to a Release instead of an Actions artifact

If you'd prefer a permanent download link rather than a build artifact
(artifacts expire after 90 days by default), tag a commit:

```bash
git tag v1.0.0
git push origin v1.0.0
```

and extend the workflow with a release step, or just manually upload the
downloaded `AutoClicker.exe` to a GitHub Release.

## Notes

- Windows may show a SmartScreen warning on first run since the exe isn't
  code-signed — click "More info" → "Run anyway".
- Antivirus tools sometimes flag PyInstaller-built exes as suspicious purely
  because of how PyInstaller packages Python; this is a common false
  positive for auto-clicker-style tools, but always be cautious running any
  exe from an unfamiliar source.
