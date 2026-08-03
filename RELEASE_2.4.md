# Jotter v2.4 Release Notes

## What's New

### Format While You Type
Formatting controls now work in two modes. With text selected, they apply to the selection as before. With no selection, clicking a formatting button enters **typing mode** — every character you type afterwards carries that format. Click the same button again to turn it off. Clicking anywhere in the text area to reposition the cursor exits typing mode.

This applies to:
- **B** — Bold
- **I** — Italic
- **U** — Underline
- **S̶** — Strikethrough
- Color swatch (text color)
- Highlight swatch (background color)

### Formatting Buttons No Longer Drop the Selection
On Windows, clicking a standard button control moves keyboard focus away from the text area, which caused the selection to be silently cleared before any formatting command could read it. The formatting toolbar buttons have been rebuilt as label-based controls that never receive focus on click, so the text widget keeps focus and the selection is always intact when the formatting command runs.

---

## Bug Fixes

- **Bold, Italic, Underline, Strikethrough, color, and highlight** did not apply when clicking the toolbar button with text selected. Root cause: Windows clears the text widget's selection at the OS level (WM_SETFOCUS) when any standard button control is clicked, before any Python code can run. Fixed by replacing the toolbar buttons with focus-safe label controls.
- **Typing with active formatting** was not possible — clicking Bold with no selection did nothing. Fixed by the new typing-format mode described above.

---

## Changes from v2.3

| Area | Change |
|---|---|
| Formatting | Toolbar buttons no longer steal focus, preserving the text selection |
| Formatting | Bold, Italic, Underline, Strikethrough, text color, and highlight now apply correctly to selected text |
| Formatting | New typing-format mode: activate a format with no selection, then type to produce formatted text |

---

## Installation

Download `JotterSetup.exe` from the releases page, or run from source:

```bash
pip install tkinterdnd2
python editor.py
```

---

© 2026 Chris Lutz — chrismlutz@gmail.com
