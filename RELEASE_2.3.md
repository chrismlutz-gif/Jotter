# Jotter v2.3 Release Notes

## What's New

### Drag and Drop to Open Files
Files can now be dragged directly from Windows Explorer onto the Jotter window to open them. Each dropped file opens in its own tab. Files with spaces in their paths are handled correctly. Multiple files can be dropped at once.

> **Note:** Requires the `tkinterdnd2` package. If running from source, install it with `pip install tkinterdnd2` before launching.

### Markdown File Support
Jotter now recognizes `.md` files throughout the app — in the Open dialog, Save As dialog, and via drag and drop. Markdown files are read and written as plain UTF-8 text.

### Horizontal and Vertical Scrollbars
Both scrollbars are now always visible and sized at 20px for easier use. The horizontal scrollbar appears automatically at the bottom of the editor when word wrap is turned off, and hides again when wrap is re-enabled — matching the behavior of WordPad. Scrollbar colors follow the active dark/light theme.

### Line Numbers Scroll in Sync
The line number panel now stays in sync with the text area when scrolling vertically.

### Configurable Default Save Folder
A new **File → Set Default Save Folder...** option lets you choose where the Open and Save As dialogs open by default. The choice is saved across sessions. The built-in default is `Documents\Notes`, which is created automatically if it doesn't exist.

### Launch with Windows
A new **Options → Launch with Windows** toggle adds or removes a startup entry for Jotter in the Windows registry (`HKEY_CURRENT_USER`). No administrator rights are required. The checkbox accurately reflects the current registry state each time the menu is opened.

### Window Position Remembered
Jotter now restores its size and position from the previous session on launch. If the window was minimized when the app was closed, the last normal position is used instead.

---

## Bug Fixes

- **Clear All Formatting (✕ fmt)** previously did nothing when no text was selected. It now clears formatting across the entire document when there is no active selection.
- **About box text** was invisible in dark mode due to using the text-area foreground color (black) against a dark window background. Fixed to use the correct menu foreground color.
- **Line numbers** were not scrolling with the text. Fixed.

---

## Changes from v2.2

| Area | Change |
|---|---|
| Files | Added drag and drop support |
| Files | Added `.md` (Markdown) file support |
| Files | Added configurable default save folder |
| Editor | Added horizontal scrollbar (shown when word wrap is off) |
| Editor | Scrollbars resized to 20px using pure-Tk rendering |
| Editor | Line numbers now scroll in sync with text |
| Options | Added Launch with Windows toggle |
| Session | Window size and position now restored on launch |
| Bug fix | Clear All Formatting now works without a selection |
| Bug fix | About box text readable in dark mode |

---

## Installation

Download `JotterSetup.exe` from the releases page, or run from source:

```bash
pip install tkinterdnd2
python editor.py
```

---

© 2026 Chris Lutz — chrismlutz@gmail.com
