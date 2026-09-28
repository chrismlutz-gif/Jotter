# Jotter v3.0 Release Notes

## What's New

### Clipboard Tab
- **Copy buttons stand out** — each line's Copy button now has a colored border that matches the line's color dot. Change the dot's color and the border changes with it.
- **Clearer buttons** — Copy, ×, and + Add Line now use their own button colors, a step apart from the background, in both Dark and Light Mode, with a more noticeable hover.

### More Vibrant Colors
- **Richer accent palette** — the tab dot, clipboard line, and tab group colors are about 30% more saturated.
- **Tuned for Light Mode** — in Light Mode, accent colors are drawn a shade deeper and richer so they don't wash out on a white background. Your chosen colors are saved unchanged; only how they're drawn differs by theme.
- **Existing colors upgrade automatically** — tabs, groups, and clipboard lines using the old palette pick up the new versions the next time Jotter starts. Custom colors are left exactly as you chose them.

### New Icon Accent
- The Jotter icon now has a peach border, drawn at every icon size so it stays visible even at 16 px.

---

## Fixes

### Dark / Light Mode
- **Buttons reverting to dark colors** — after switching to Light Mode, buttons on the Clipboard tab, the ＋ / 📁 / 📋 buttons in the tab bar, and the formatting toolbar buttons would turn back to Dark Mode colors after you moused over them. They now always use the current theme.
- **Tab bar and formatting toolbar stayed dark** — these now switch with the theme, both when you toggle it and when Jotter starts up in Light Mode.
- **Scrollbars stayed dark** — scrollbars now follow the theme, and their handle is easier to see in both modes.

---

## Installation

Jotter ships as a standalone `Jotter.exe` — no installer. Download it from the releases page and run it, or run from source:

```bash
pip install tkinterdnd2
python editor.py
```

---

© 2026 Chris Lutz — chrismlutz@gmail.com
