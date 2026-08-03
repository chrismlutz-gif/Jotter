# Jotter v2.6 Release Notes

## What's New

### Autosave for Titled Tabs
Closing a titled tab — one that's already tied to a file, or that you've renamed — no longer prompts "Save changes before closing?" It's saved automatically and silently:
- If a tab is already tied to a file on disk, it's written to that file.
- If a tab has been renamed but never saved, Jotter creates a new file for it — using the tab's name — in your default save folder, so nothing gets lost just because it was never explicitly saved.

### Untitled Tabs Still Prompt
A tab that's never been saved or renamed has no filename to fall back on, so it keeps the familiar Yes/No/Cancel "Save changes?" prompt when it closes. Cancelling the prompt aborts the close (or, on app quit, aborts the quit entirely).

### Open Save Folder Button
A new 📁 button sits next to the "+" new-tab button in the tab bar. Click it to open your default save folder directly in Explorer — the same folder set via File → Set Default Save Folder.

---

## Behavior Changes

- **Titled tabs no longer show the close-tab confirmation dialog.** If a tab has a file on disk, or has been renamed, closing it (or quitting the app) saves it silently instead of asking. If you relied on "No" to discard changes on a renamed tab, note it will now be saved to a new file rather than discarded.
- **Untitled tabs are unchanged** — they still ask Yes/No/Cancel before closing, same as before.

---

## Changes from v2.4

| Area | Change |
|---|---|
| Saving | Titled tabs (saved or renamed) now autosave silently on tab close and app quit |
| Saving | Untitled tabs still prompt to save before closing |
| Saving | Renaming a tab and closing it without saving auto-creates a file using the tab's name |
| Interface | New 📁 button opens the default save folder directly from the tab bar |
| Versioning | Installer version (`jotter.iss`) now tracks the app version |

---

## Installation

Download `JotterSetup.exe` from the releases page, or run from source:

```bash
pip install tkinterdnd2
python editor.py
```

---

© 2026 Chris Lutz — chrismlutz@gmail.com
