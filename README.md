# Jotter

A lightweight, dark-mode text editor built for speed and organisation.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

---

## Features

- **Multiple tabs** — open as many files as you need, all in one window
- **Drag-to-reorder** — drag tabs left and right to rearrange them
- **Tab groups** — drag one tab onto another to group them; drag out to ungroup
- **Group management** — collapse, expand, rename, and recolour groups; drag groups to reorder or merge them
- **Per-tab accent colours** — click the coloured dot on any tab to customise it
- **Dark and light mode** — toggle under Options menu
- **Session persistence** — reopens your tabs and groups exactly as you left them
- **Line numbers** — always visible alongside the editor
- **Word and character counter** — live count in the status bar
- **File operations** — New, Open, Save, Save As, with unsaved-changes prompts
- **Full undo/redo** — standard Ctrl+Z / Ctrl+Y
- **Always on top** — pin Jotter above other windows
- **TXT/RTF** — work with both TXT and RTF files side by side
- **Text formatting** — RTF files allow for basic text formatting features


---

## Installation

### Option 1 — Run the installer (Windows)

Download `JotterSetup.exe` from the [Releases](https://github.com/chrismlutz-gif/Jotter/releases) page and run it. Jotter will run.

### Option 2 — Run from source

**Requirements:** Python 3.9 or later (tkinter included in standard Windows installs)

```bash
git clone https://github.com/chrismlutz-gif/jotter.git
cd jotter
editor.py
rtf_io.py

```

No additional packages are needed to run from source.

---

## Building the installer yourself

1. Install [Inno Setup 7](https://jrsoftware.org/isdl.php) (free)
2. Open a terminal in the project folder and run:

```bat
build.bat
```

This will:
- Install PyInstaller (if not already present)
- Bundle rtf_io.py and `editor.py` into `dist\Jotter.exe`
- Compile `installer\JotterSetup.exe` via Inno Setup

---

## Controls

("Ctrl+N",          "New tab")
("Ctrl+O",          "Open .txt or .rtf file")
("Ctrl+S",          "Save")
("Ctrl+Shift+S",    "Save As")
("Ctrl+W",          "Close tab")
("Ctrl+F",          "Find")
("Ctrl+H",          "Find & Replace")
("Ctrl+B",          "Bold")
("Ctrl+I",          "Italic")
("Ctrl+U",          "Underline")
("Drag tab",        "Reorder or group tabs")
("Right-click tab", "Rename, color, text background, close")
("Right-click text","Cut / Copy / Paste / Format / Case")
("Toolbar",         "Font family & size, Aa▾ case, B / I / U / S̶")
("Toolbar",         "Text & highlight color, alignment, ↵ Wrap")
("Hover controls",  "Tooltips on all toolbar controls")
("Aa▾",             "Change case: UPPER / lower / Capitalize / tOGGLE")
("S̶  button",       "Strikethrough formatting")
("↵ Wrap",          "Toggle word wrap per tab")
("✕ fmt",           "Clear all formatting from selection")

---

## Project structure

```
jotter/
├── editor.py        # Main application source
├── rtf_io.py        # Main application RTF resource
├── jotter.ico       # Application icon
├── jotter.spec      # PyInstaller build spec
├── jotter.iss       # Inno Setup installer script
├── build.bat        # One-click build script
├── LICENSE
└── README.md
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.

© 2026 Chris Lutz — chrismlutz@gmail.com
