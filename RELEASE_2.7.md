# Jotter v2.7 Release Notes

## What's New

### Clipboard Tab — the first "specialty tab"
Jotter now has a second kind of tab alongside the normal rich-text tab: a **specialty tab**. This release introduces the first one, the **Clipboard tab**, with more specialty tab types planned for future releases.

The Clipboard tab is a continuous, scrollable form of reusable text snippets:

- **One open text box per line, with a Copy button** — click Copy and that line's text is loaded onto your system clipboard, ready to paste anywhere.
- **Add and remove lines freely** — a "+ Add Line" button at the top adds a new blank line at the bottom of the list; each line has its own "×" button to remove it. Each line's text box also grows automatically as you type more into it.
- **Per-line color coding** — click the colored dot next to a line to tag it with a color from the palette, or choose a custom one.
- **Singleton tab** — only one Clipboard tab can be open at a time. Opening it again (via the 📋 button or File → New Clipboard Tab) switches to the one that's already open instead of creating a duplicate.
- **Persisted independently of the tab itself** — lines are saved to `jotter_settings.json` (the same file used for other app-wide preferences, like your default save folder) as you edit them, so they survive closing the Clipboard tab, quitting Jotter, or even a crash — not just a clean session restore.

### Access
- New 📋 button in the tab bar, next to the 📁 (open save folder) button
- File → New Clipboard Tab

---

## Behavior Notes

- The Clipboard tab has no file of its own — Ctrl+S / Ctrl+Shift+S and Ctrl+O don't act on it, and closing it never prompts to save, since its content is already saved continuously.
- Right-clicking the Clipboard tab in the tab bar offers Rename, Tab Color, and Close — the text-background/text-color options (which only apply to normal rich-text tabs) are hidden for it.
- Dark/Light mode theming applies to the Clipboard tab the same as it does everywhere else in Jotter.

---

## Installation

Download `JotterSetup.exe` from the releases page, or run from source:

```bash
pip install tkinterdnd2
python editor.py
```

---

© 2026 Chris Lutz — chrismlutz@gmail.com
