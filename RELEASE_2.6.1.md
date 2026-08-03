# Jotter v2.6.1 Release Notes

## What's New

### Untitled Tabs Prompt Again Before Closing
v2.6 made every tab autosave silently on close, including tabs that had never been saved or named. That went too far — an untitled tab with no filename has no obvious place to save to, so silently discarding or auto-filing it wasn't the right call.

As of v2.6.1, the close behavior is split by whether a tab is "titled":

- **Titled tabs** — already tied to a file on disk, or renamed via right-click → Rename — still autosave silently on tab close and app quit, exactly as in v2.6. No prompt.
- **Untitled tabs** — never saved, never renamed — go back to asking "Save changes to 'Untitled' before closing?" (Yes / No / Cancel). Cancelling aborts the close; on app quit, cancelling any one tab's prompt aborts the whole quit.

---

## Behavior Changes

- **Save prompt is back for untitled tabs.** If you were relying on v2.6's fully-silent close, note that a never-saved, never-renamed tab will once again ask before closing.
- Titled-tab autosave (silent write to an existing file, or auto-creating a file from a renamed tab's name) is unchanged from v2.6.

---

## Changes from v2.6

| Area | Change |
|---|---|
| Saving | Untitled tabs (never saved, never renamed) prompt to save before closing again |
| Saving | Titled tabs (saved or renamed) continue to autosave silently, no prompt |
| Saving | Cancelling the prompt on app quit now aborts the quit, matching pre-2.6 behavior |

---

## Installation

Download `JotterSetup.exe` from the releases page, or run from source:

```bash
pip install tkinterdnd2
python editor.py
```

---

© 2026 Chris Lutz — chrismlutz@gmail.com
