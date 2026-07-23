# Jotter

A lightweight, tabbed rich-text editor built for speed and organisation — dark mode included.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Version](https://img.shields.io/badge/Version-2.2-orange)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)

---

## Features

### Tabs & Organisation
- **Multiple tabs** — open as many files as you need in one window
- **Drag-to-reorder** — drag tabs left and right to rearrange them
- **Tab groups** — drag one tab onto another to group them; drag out to ungroup
- **Group management** — collapse, expand, rename, and recolour groups
- **Per-tab accent colours** — click the coloured dot on any tab to customise it
- **Per-tab text colours** — set independent text foreground and background per tab

### Files
- **TXT, RTF, and Markdown** — open and save `.txt`, `.rtf`, and `.md` files
- **Drag and drop** — drag a file from Explorer onto the window to open it
- **Default save folder** — configurable via File → Set Default Save Folder
- **Session persistence** — reopens tabs, content, window position, and theme on next launch

### Formatting
- **Rich text** — bold, italic, underline, and strikethrough
- **Font control** — font family and size per selection
- **Text and highlight colour** — foreground and background colour pickers
- **Paragraph alignment** — left, centre, right
- **Word wrap** — toggle per tab
- **Change case** — UPPER, lower, Capitalise, tOGGLE
- **Clear formatting** — strip all formatting from a selection, or the whole document

### Interface
- **Dark and light mode** — toggle under Options
- **Always on Top** — pin Jotter above other windows
- **Launch with Windows** — optional startup entry (Options menu, no admin rights needed)
- **Tooltips** — hover over any toolbar control for a description
- **Line numbers** — always visible alongside the editor
- **Word and character counter** — live count in the status bar
- **Find and Replace** — with match highlighting

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New tab |
| `Ctrl+O` | Open file |
| `Ctrl+W` | Close tab |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save As |
| `Ctrl+F` | Find |
| `Ctrl+H` | Find & Replace |
| `Ctrl+Z` / `Ctrl+Y` | Undo / Redo |
| `Ctrl+A` | Select all |
| `Ctrl+B` | Bold |
| `Ctrl+I` | Italic |
| `Ctrl+U` | Underline |

| Interaction | Action |
|---|---|
| Drag tab | Reorder or group tabs |
| Drag file onto window | Open file |
| Right-click tab | Rename, accent colour, text colours, close |
| Right-click text | Cut / Copy / Paste / Format / Case |
| `Aa▾` toolbar button | Change case |
| `S̶` toolbar button | Strikethrough |
| `↵ Wrap` | Toggle word wrap for active tab |
| `✕ fmt` | Clear all formatting |

---

## Installation

### Option 1 — Run the installer (Windows)

Download `JotterSetup.exe` from the [Releases](https://github.com/chrismlutz-gif/Jotter/releases) page and run it.

### Option 2 — Run from source

**Requirements:** Python 3.9 or later (tkinter is included in standard Windows installs)

```bash
git clone https://github.com/chrismlutz-gif/Jotter.git
cd Jotter
pip install tkinterdnd2
python editor.py
```

---

## Building the installer yourself

1. Install [Inno Setup 7](https://jrsoftware.org/isdl.php) (free)
2. Open a terminal in the project folder and run:

```bat
build.bat
```

This will:
- Install PyInstaller and tkinterdnd2 (if not already present)
- Bundle `editor.py`, `rtf_io.py`, and supporting files into `dist\Jotter.exe`
- Compile `installer\JotterSetup.exe` via Inno Setup

---

## Project Structure

```
Jotter/
├── editor.py        # Main application
├── rtf_io.py        # RTF parser and writer
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
