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
- **Full Find/Replace** — standard Ctrl+F / Ctrl+R
- **Always on top** — pin Jotter above other windows

---

## Installation

### Option 1 — Run the installer (Windows)

Download `JotterSetup.exe` from the [Releases](https://github.com/chrismlutz-gif/Jotter/releases) page and run it. Jotter will run.

### Option 2 — Run from source

**Requirements:** Python 3.9 or later (tkinter included in standard Windows installs)

```bash
git clone https://github.com/chrismlutz-gif/jotter.git
cd jotter
python editor.py
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
- Bundle `editor.py` into `dist\Jotter.exe`
- Compile `installer\JotterSetup.exe` via Inno Setup

---

## Controls

| Action | Result |
|---|---|
| Drag a tab | Reorder it in the bar |
| Drag onto another tab | Group the two tabs together |
| Drag out of a group | Ungroup that tab |
| Drag one group onto another | Merge the groups |
| Click group strip / label | Collapse or expand the group |
| Double-click group label | Rename the group |
| Right-click a tab | Rename, recolour, or close it |
| Right-click group strip | Recolour, rename, or ungroup |
| Click the colour dot | Pick a tab accent colour |
| **Ctrl+N** | New tab |
| **Ctrl+W** | Close tab |
| **Ctrl+O** | Open file |
| **Ctrl+S** | Save file |
| **Ctrl+Shift+S** | Save As |
| **Ctrl+Z / Ctrl+Y** | Undo / Redo |

---

## Project structure

```
jotter/
├── editor.py        # Main application source
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
