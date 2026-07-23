#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
editor.py -- Jotter  v2.3
  * Multiple tabs with drag-to-reorder and drag-to-group
  * Per-tab accent colour, text background, text foreground
  * RTF read/write with formatting toolbar
  * Find / Replace bar
  * Dark / light mode, Always-on-top
  * Session persistence
"""

import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser, simpledialog, font as tkfont
from tkinter import ttk
import os, sys, json, re
import rtf_io

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _DND_AVAILABLE = True
except ImportError:
    _DND_AVAILABLE = False

try:
    import winreg
    _WINREG_AVAILABLE = True
except ImportError:
    _WINREG_AVAILABLE = False

_STARTUP_REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
_STARTUP_REG_NAME = "Jotter"

def _notes_dir():
    """Default save/open location: ~/Documents/Notes"""
    d = os.path.join(os.path.expanduser("~"), "Documents", "Notes")
    os.makedirs(d, exist_ok=True)
    return d

def _data_dir():
    if getattr(sys, "frozen", False):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        d = os.path.join(base, "Jotter")
    else:
        d = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(d, exist_ok=True)
    return d

SESSION_FILE  = os.path.join(_data_dir(), ".jotter_session.json")
SETTINGS_FILE = os.path.join(_data_dir(), "jotter_settings.json")

THEMES = {
    "dark": {
        "bg": "#1e1e1e", "tab_bar": "#252526", "tab_idle": "#2d2d2d",
        "tab_active": "#1e1e1e", "tab_hover": "#383838",
        "text_bg": "#ffffcc", "text_fg": "#000000", "text_sel": "#264f78",
        "ln_bg": "#252526", "ln_fg": "#858585",
        "status_bg": "#007acc", "status_fg": "#ffffff",
        "border": "#474747", "close_fg": "#858585",
        "menu_bg": "#252526", "menu_fg": "#cccccc", "menu_sel": "#094771",
        "drop_line": "#ffffff", "default_dot": "#569cd6", "toolbar_fg": "#cccccc",
    },
    "light": {
        "bg": "#ffffff", "tab_bar": "#f3f3f3", "tab_idle": "#ececec",
        "tab_active": "#ffffff", "tab_hover": "#e0e0e0",
        "text_bg": "#ffffcc", "text_fg": "#000000", "text_sel": "#add6ff",
        "ln_bg": "#f3f3f3", "ln_fg": "#999999",
        "status_bg": "#007acc", "status_fg": "#ffffff",
        "border": "#cccccc", "close_fg": "#717171",
        "menu_bg": "#f3f3f3", "menu_fg": "#1e1e1e", "menu_sel": "#0060c0",
        "drop_line": "#333333", "default_dot": "#0078d4", "toolbar_fg": "#555555",
    },
}

_ACCENT_CYCLE = ["#569cd6","#4ec9b0","#dcdcaa","#ce9178",
                 "#9cdcfe","#c586c0","#f48771","#b5cea8"]
_GROUP_COLORS = ["#e06c75","#e5c07b","#98c379","#56b6c2",
                 "#61afef","#c678dd","#d19a66"]


class ToolTip:
    """Simple hover tooltip for any widget."""
    def __init__(self, widget, text, delay=600):
        self._widget  = widget
        self._text    = text
        self._delay   = delay
        self._job     = None
        self._tip_win = None
        widget.bind("<Enter>",  self._on_enter,  add="+")
        widget.bind("<Leave>",  self._on_leave,  add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, event=None):
        self._cancel()
        self._job = self._widget.after(self._delay, self._show)

    def _on_leave(self, event=None):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self._job:
            self._widget.after_cancel(self._job)
            self._job = None

    def _show(self):
        if self._tip_win:
            return
        w = self._widget
        x = w.winfo_rootx() + w.winfo_width() // 2
        y = w.winfo_rooty() + w.winfo_height() + 4
        self._tip_win = tw = tk.Toplevel(w)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        tw.attributes("-topmost", True)
        lbl = tk.Label(tw, text=self._text, justify="left",
                       background="#ffffe0", foreground="#000000",
                       relief="solid", borderwidth=1,
                       font=("Segoe UI", 9), padx=5, pady=3)
        lbl.pack()

    def _hide(self):
        if self._tip_win:
            self._tip_win.destroy()
            self._tip_win = None


class TabGroup:
    _ctr = 0
    def __init__(self, color=None):
        TabGroup._ctr += 1
        self.id           = TabGroup._ctr
        self.color        = color or _GROUP_COLORS[(TabGroup._ctr-1) % len(_GROUP_COLORS)]
        self.collapsed    = False
        self.label        = "Group %d" % TabGroup._ctr
        self.container    = None
        self.strip        = None
        self.inner        = None
        self.collapse_btn = None
        self.label_lbl    = None


class Tab:
    _ctr = 0
    def __init__(self, title="Untitled"):
        Tab._ctr += 1
        self.id         = Tab._ctr
        self.title      = title
        self.filepath   = None
        self.modified   = False
        self.color      = None
        self.text_bg    = None
        self.text_fg    = None
        self.group      = None
        self.text_frame = None
        self.text       = None
        self.linenos    = None
        self.hscroll    = None
        self.btn_frame  = None
        self.dot_canvas = None
        self.oval_id    = None
        self.title_lbl  = None
        self.close_lbl  = None


class Editor(TkinterDnD.Tk if _DND_AVAILABLE else tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Jotter")
        self.geometry("1100x740")
        self.minsize(320, 220)

        self._default_dir   = self._load_settings().get(
                                  "default_dir", _notes_dir())
        self._always_on_top = tk.BooleanVar(value=False)
        self._theme_name    = "dark"
        self._T             = THEMES["dark"]
        self._configure_scrollbar_style()
        self._tabs          = []
        self._active        = None
        self._drag_tab      = None
        self._drag_start_x  = 0
        self._drag_moved    = False
        self._press_on_dot  = False
        self._drop_item     = None
        self._ghost         = None
        self._drag_group       = None
        self._drag_grp_start_x = 0
        self._drag_grp_moved   = False

        self.configure(bg=self._T["bg"])
        self._build_menu()
        self._build_tab_bar()
        self._build_fmt_toolbar()
        self._build_body()
        self._build_statusbar()
        self._build_findbar()

        self.bind("<Control-n>", lambda _e: self.cmd_new_tab())
        self.bind("<Control-o>", lambda _e: self.cmd_open())
        self.bind("<Control-s>", lambda _e: self.cmd_save())
        self.bind("<Control-S>", lambda _e: self.cmd_save_as())
        self.bind("<Control-w>", lambda _e: self.cmd_close_tab())
        self.bind("<Control-f>", lambda _e: self._show_find_bar(False))
        self.bind("<Control-h>", lambda _e: self._show_find_bar(True))
        self.bind("<Control-b>", lambda _e: self._fmt_toggle(
            rtf_io.tag_bold(), font=("Consolas",11,"bold")))
        self.bind("<Control-i>", lambda _e: self._fmt_toggle(
            rtf_io.tag_italic(), font=("Consolas",11,"italic")))
        self.bind("<Control-u>", lambda _e: self._fmt_toggle(
            rtf_io.tag_underline(), underline=True))
        self.protocol("WM_DELETE_WINDOW", self._on_quit)

        if _DND_AVAILABLE:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._on_drop)

        if not self._load_session():
            self.cmd_new_tab()

    # ----------------------------------------------------------------
    # Scrollbar style
    # ----------------------------------------------------------------
    def _configure_scrollbar_style(self):
        """Create a pure-Tk (non-native) scrollbar style so width is respected."""
        T = self._T
        s = ttk.Style()
        _SB_W = 20
        # Borrow elements from the 'clam' theme — it renders in pure Tk, not
        # via the Windows visual-styles engine, so width/colours are honoured.
        for elem in (
            'Vertical.Scrollbar.trough',   'Vertical.Scrollbar.thumb',
            'Vertical.Scrollbar.uparrow',  'Vertical.Scrollbar.downarrow',
            'Horizontal.Scrollbar.trough', 'Horizontal.Scrollbar.thumb',
            'Horizontal.Scrollbar.leftarrow', 'Horizontal.Scrollbar.rightarrow',
        ):
            try:
                s.element_create(f'Jotter.{elem}', 'from', 'clam')
            except tk.TclError:
                pass   # already exists from a previous call

        s.layout('Jotter.Vertical.TScrollbar', [
            ('Jotter.Vertical.Scrollbar.trough', {'sticky': 'ns', 'children': [
                ('Jotter.Vertical.Scrollbar.uparrow',  {'side': 'top',    'sticky': ''}),
                ('Jotter.Vertical.Scrollbar.downarrow', {'side': 'bottom', 'sticky': ''}),
                ('Jotter.Vertical.Scrollbar.thumb',    {'expand': '1',    'sticky': 'nswe'}),
            ]}),
        ])
        s.layout('Jotter.Horizontal.TScrollbar', [
            ('Jotter.Horizontal.Scrollbar.trough', {'sticky': 'ew', 'children': [
                ('Jotter.Horizontal.Scrollbar.leftarrow',  {'side': 'left',  'sticky': ''}),
                ('Jotter.Horizontal.Scrollbar.rightarrow', {'side': 'right', 'sticky': ''}),
                ('Jotter.Horizontal.Scrollbar.thumb',      {'expand': '1',   'sticky': 'nswe'}),
            ]}),
        ])
        for name in ('Jotter.Vertical.TScrollbar', 'Jotter.Horizontal.TScrollbar'):
            s.configure(name,
                background=T['tab_bar'],
                troughcolor=T['bg'],
                bordercolor=T['bg'],
                darkcolor=T['tab_bar'],
                lightcolor=T['tab_bar'],
                arrowcolor=T['menu_fg'],
                width=_SB_W,
                arrowsize=_SB_W)
            s.map(name, background=[
                ('active', T['tab_hover']),
                ('!active', T['tab_bar']),
            ])

    # ----------------------------------------------------------------
    # Menu
    # ----------------------------------------------------------------
    def _build_menu(self):
        T  = self._T
        kw = dict(tearoff=0, bg=T["menu_bg"], fg=T["menu_fg"],
                  activebackground=T["menu_sel"], activeforeground=T["menu_fg"],
                  relief="flat", bd=0)
        mb = tk.Menu(self, **kw)
        self.configure(menu=mb)

        fm = tk.Menu(mb, **kw)
        fm.add_command(label="New Tab       Ctrl+N", command=self.cmd_new_tab)
        fm.add_command(label="Open...       Ctrl+O", command=self.cmd_open)
        fm.add_separator()
        fm.add_command(label="Save          Ctrl+S", command=self.cmd_save)
        fm.add_command(label="Save As...    Ctrl+Shift+S", command=self.cmd_save_as)
        fm.add_separator()
        fm.add_command(label="Set Default Save Folder...", command=self._cmd_set_default_dir)
        fm.add_separator()
        fm.add_command(label="Close Tab     Ctrl+W", command=self.cmd_close_tab)
        mb.add_cascade(label="File", menu=fm)

        em = tk.Menu(mb, **kw)
        em.add_command(label="Undo  Ctrl+Z",
            command=lambda: self.focus_get() and self.focus_get().event_generate("<<Undo>>"))
        em.add_command(label="Redo  Ctrl+Y",
            command=lambda: self.focus_get() and self.focus_get().event_generate("<<Redo>>"))
        em.add_separator()
        em.add_command(label="Cut   Ctrl+X",
            command=lambda: self.focus_get() and self.focus_get().event_generate("<<Cut>>"))
        em.add_command(label="Copy  Ctrl+C",
            command=lambda: self.focus_get() and self.focus_get().event_generate("<<Copy>>"))
        em.add_command(label="Paste Ctrl+V",
            command=lambda: self.focus_get() and self.focus_get().event_generate("<<Paste>>"))
        em.add_separator()
        em.add_command(label="Select All Ctrl+A", command=self._select_all)
        em.add_separator()
        em.add_command(label="Find...    Ctrl+F", command=lambda: self._show_find_bar(False))
        em.add_command(label="Replace... Ctrl+H", command=lambda: self._show_find_bar(True))
        mb.add_cascade(label="Edit", menu=em)

        om = tk.Menu(mb, **kw)
        om.add_checkbutton(label="Dark Mode", command=self.cmd_toggle_theme)
        om.add_checkbutton(label="Always on Top", variable=self._always_on_top,
            command=lambda: self.attributes("-topmost", self._always_on_top.get()))
        if _WINREG_AVAILABLE:
            self._launch_with_windows = tk.BooleanVar(value=self._startup_enabled())
            om.add_checkbutton(label="Launch with Windows",
                               variable=self._launch_with_windows,
                               command=self._toggle_startup)
        mb.add_cascade(label="Options", menu=om)

        hm = tk.Menu(mb, **kw)
        hm.add_command(label="About Jotter...", command=self._show_about)
        mb.add_cascade(label="Help", menu=hm)

    def _select_all(self, event=None):
        if self._active and self._active.text:
            self._active.text.tag_add("sel", "1.0", "end")
            self._active.text.mark_set("insert", "end")

    # ----------------------------------------------------------------
    # Tab bar
    # ----------------------------------------------------------------
    def _build_tab_bar(self):
        T = self._T
        outer = tk.Frame(self, bg=T["tab_bar"])
        outer.pack(side="top", fill="x")
        self._bar_outer = outer
        canvas = tk.Canvas(outer, bg=T["tab_bar"], height=36,
                           highlightthickness=0, bd=0)
        canvas.pack(side="left", fill="both", expand=True)
        self._bar_canvas = canvas
        inner = tk.Frame(canvas, bg=T["tab_bar"])
        self._bar_inner = inner
        canvas.create_window((0,0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._drop_canvas  = canvas
        self._drop_line_id = None
        # "+" new-tab button pinned to the right of the bar
        plus = tk.Label(outer, text="  ＋  ", bg=T["tab_idle"], fg=T["toolbar_fg"],
                        font=("Segoe UI", 13, "bold"), cursor="hand2",
                        relief="flat", padx=2, pady=3)
        plus.pack(side="right", padx=6, pady=3)
        plus.bind("<Button-1>", lambda e: self.cmd_new_tab())
        plus.bind("<Enter>", lambda e: plus.configure(bg=T["tab_hover"]))
        plus.bind("<Leave>", lambda e: plus.configure(bg=T["tab_idle"]))
        ToolTip(plus, "New tab  (Ctrl+N)")

    def _rebuild_tab_buttons(self):
        T = self._T
        for w in self._bar_inner.winfo_children():
            w.destroy()
        seen_groups = {}
        for tab in self._tabs:
            grp = tab.group
            if grp is not None:
                if grp not in seen_groups:
                    con = self._make_group_container(grp,
                        [t for t in self._tabs if t.group is grp],
                        self._bar_inner)
                    grp.container = con
                    seen_groups[grp] = con
                    con.pack(side="left", padx=2, pady=2)
                if not grp.collapsed:
                    self._make_tab_btn(tab, grp.inner)
            else:
                self._make_tab_btn(tab, self._bar_inner)
        self._update_bar_height()
        self._restore_active_highlight()

    def _update_bar_height(self):
        self._bar_inner.update_idletasks()
        h = self._bar_inner.winfo_reqheight()
        self._bar_canvas.configure(height=max(h, 36))

    def _make_group_container(self, group, tabs, parent):
        T   = self._T
        con = tk.Frame(parent, bg=group.color, bd=0)
        group.container = con
        strip = tk.Frame(con, bg=group.color, cursor="hand2")
        strip.pack(side="top", fill="x")
        group.strip = strip
        btn = tk.Label(strip, text="▾" if not group.collapsed else "▸",
                       bg=group.color, fg="#ffffff",
                       font=("Segoe UI", 9), padx=3, cursor="hand2")
        btn.pack(side="left")
        group.collapse_btn = btn
        lbl = tk.Label(strip, text=group.label,
                       bg=group.color, fg="#ffffff",
                       font=("Segoe UI", 9, "bold"), padx=4, cursor="hand2")
        lbl.pack(side="left")
        group.label_lbl = lbl
        for w in (strip, btn, lbl):
            w.bind("<Button-1>",   lambda e, g=group: self._toggle_collapse(g))
            w.bind("<Double-Button-1>", lambda e, g=group: self._rename_group(g))
            w.bind("<Button-3>",   lambda e, g=group: self._group_context(e, g))
            w.bind("<ButtonPress-1>",   lambda e, g=group: self._on_group_press(e, g))
            w.bind("<B1-Motion>",       lambda e, g=group: self._on_group_drag(e, g))
            w.bind("<ButtonRelease-1>", lambda e, g=group: self._on_group_release(e, g))
        inner = tk.Frame(con, bg=T["tab_bar"])
        inner.pack(side="top", fill="x")
        group.inner = inner
        return con

    def _make_tab_btn(self, tab, parent):
        T        = self._T
        is_active = (tab is self._active)
        bg       = T["tab_active"] if is_active else T["tab_idle"]
        frm      = tk.Frame(parent, bg=bg, cursor="hand2")
        frm.pack(side="left", padx=(0,1), pady=(2,0))
        tab.btn_frame = frm
        dot_color = tab.color or T["default_dot"]
        dot = tk.Canvas(frm, width=10, height=10, bg=bg,
                        highlightthickness=0, cursor="hand2")
        dot.pack(side="left", padx=(6,2), pady=8)
        oid = dot.create_oval(1,1,9,9, fill=dot_color, outline="")
        tab.dot_canvas = dot
        tab.oval_id   = oid
        title_lbl = tk.Label(frm, text=tab.title, bg=bg, fg=T["toolbar_fg"],
                             font=("Segoe UI", 10), padx=2)
        title_lbl.pack(side="left", pady=4)
        tab.title_lbl = title_lbl
        close_lbl = tk.Label(frm, text=" × ", bg=bg, fg=T["close_fg"],
                             font=("Segoe UI", 11), cursor="hand2")
        close_lbl.pack(side="left", pady=4)
        tab.close_lbl = close_lbl
        for w in (frm, title_lbl, dot):
            w.bind("<ButtonPress-1>",   lambda e, t=tab, d=(w is dot): self._on_press(e, t, d))
            w.bind("<B1-Motion>",       lambda e, t=tab: self._on_drag(e, t))
            w.bind("<ButtonRelease-1>", lambda e, t=tab: self._on_release(e, t))
            w.bind("<Enter>", lambda e, t=tab: self._tab_hover(t, True))
            w.bind("<Leave>", lambda e, t=tab: self._tab_hover(t, False))
            w.bind("<Button-3>", lambda e, t=tab: self._tab_context(e, t))
        close_lbl.bind("<Button-1>",  lambda e, t=tab: self.cmd_close_tab(t))
        dot.bind("<Button-1>",        lambda e, t=tab: self._show_tab_color_picker(t))
        frm.bind("<Button-1>",        lambda e, t=tab: self._activate(t))
        title_lbl.bind("<Button-1>",  lambda e, t=tab: self._activate(t))
        if is_active:
            for w in (frm, title_lbl, dot, close_lbl):
                w.configure(bg=T["tab_active"])
            dot.configure(bg=T["tab_active"])

    def _restore_active_highlight(self):
        T = self._T
        for tab in self._tabs:
            if tab.btn_frame:
                bg = T["tab_active"] if tab is self._active else T["tab_idle"]
                tab.btn_frame.configure(bg=bg)
                if tab.title_lbl: tab.title_lbl.configure(bg=bg)
                if tab.close_lbl: tab.close_lbl.configure(bg=bg)
                if tab.dot_canvas: tab.dot_canvas.configure(bg=bg)

    def _tab_hover(self, tab, entering):
        if tab is self._active:
            return
        T  = self._T
        bg = T["tab_hover"] if entering else T["tab_idle"]
        if tab.btn_frame:  tab.btn_frame.configure(bg=bg)
        if tab.title_lbl:  tab.title_lbl.configure(bg=bg)
        if tab.close_lbl:  tab.close_lbl.configure(bg=bg)
        if tab.dot_canvas: tab.dot_canvas.configure(bg=bg)

    def _activate(self, tab):
        if self._active and self._active is not tab:
            if self._active.text_frame:
                self._active.text_frame.pack_forget()
        self._active = tab
        if tab.text_frame:
            tab.text_frame.pack(fill="both", expand=True)
        if tab.text:
            self._apply_text_colors(tab)
            tab.text.focus_set()
        self._restore_active_highlight()
        self._refresh_status()
        if hasattr(self, "_wrap_on") and tab.text:
            is_wrapped = tab.text.cget("wrap") != "none"
            self._wrap_on.set(is_wrapped)
            if tab.hscroll:
                if is_wrapped:
                    tab.hscroll.pack_forget()
                else:
                    tab.hscroll.pack(side="bottom", fill="x")

    # ----------------------------------------------------------------
    # Ghost drag
    # ----------------------------------------------------------------
    def _create_ghost(self, tab):
        T     = self._T
        ghost = tk.Toplevel(self)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)
        ghost.attributes("-alpha", 0.75)
        frm = tk.Frame(ghost, bg=T["tab_hover"], padx=10, pady=6)
        frm.pack()
        tk.Label(frm, text=tab.title, bg=T["tab_hover"],
                 fg=T["text_fg"], font=("Segoe UI", 10)).pack()
        self._ghost = ghost

    def _move_ghost(self, x, y):
        if self._ghost:
            self._ghost.geometry("+%d+%d" % (x+12, y-10))

    def _destroy_ghost(self):
        if self._ghost:
            self._ghost.destroy()
            self._ghost = None

    # ----------------------------------------------------------------
    # Tab drag
    # ----------------------------------------------------------------
    def _on_press(self, event, tab, dot=False):
        self._drag_tab     = None
        self._drag_start_x = event.x_root
        self._drag_moved   = False
        self._press_on_dot = dot
        self._activate(tab)

    def _on_drag(self, event, tab):
        if self._press_on_dot:
            return
        if abs(event.x_root - self._drag_start_x) > 6:
            if self._drag_tab is None:
                self._drag_tab = tab
                self._create_ghost(tab)
            self._drag_moved = True
            self._move_ghost(event.x_root, event.y_root)
            self._update_drop_indicator(event.x_root)

    def _on_release(self, event, tab):
        self._destroy_ghost()
        self._clear_drop_indicator()
        if not self._drag_moved or self._drag_tab is None:
            self._drag_tab   = None
            self._drag_moved = False
            return
        drag = self._drag_tab
        self._drag_tab   = None
        self._drag_moved = False
        result = self._find_drop_target(event.x_root, drag)
        if result is None:
            return
        kind, payload = result
        if kind == "reorder":
            self._do_reorder(drag, payload)
        elif kind == "make_group":
            new_grp = TabGroup()
            drag.group    = new_grp
            payload.group = new_grp
            self._rebuild_tab_buttons()
        elif kind == "group":
            self._do_group(drag, payload)
        elif kind == "ungroup":
            self._do_ungroup_tab(drag)

    def _find_drop_target(self, x_root, drag_tab):
        zones = []
        seen_groups = set()
        for tab in self._tabs:
            if tab is drag_tab:
                continue
            if tab.group is None:
                if tab.btn_frame:
                    try:
                        bx = tab.btn_frame.winfo_rootx()
                        bw = tab.btn_frame.winfo_width()
                        li = self._tabs.index(tab)
                        zones.append((bx, bx+bw, "tab", tab, li, li+1))
                    except Exception:
                        pass
            else:
                grp = tab.group
                if grp not in seen_groups:
                    seen_groups.add(grp)
                    con = grp.container
                    if con:
                        try:
                            bx   = con.winfo_rootx()
                            bw   = con.winfo_width()
                            idxs = [i for i,t in enumerate(self._tabs) if t.group is grp]
                            zones.append((bx, bx+bw, "group", grp, min(idxs), max(idxs)+1))
                        except Exception:
                            pass
        for bx, bx_end, kind, payload, left_idx, right_idx in zones:
            if bx <= x_root <= bx_end:
                rel = (x_root - bx) / max(bx_end - bx, 1)
                if 0.2 <= rel <= 0.8:
                    return ("group" if kind == "group" else "make_group", payload)
                return ("reorder", left_idx if rel < 0.5 else right_idx)
        if zones:
            return ("reorder", len(self._tabs))
        return None

    def _update_drop_indicator(self, x_root):
        c = self._drop_canvas
        if self._drop_line_id:
            c.delete(self._drop_line_id)
            self._drop_line_id = None
        cx = c.winfo_rootx()
        lx = x_root - cx
        h  = c.winfo_height()
        self._drop_line_id = c.create_line(lx, 0, lx, h,
            fill=self._T["drop_line"], width=2, dash=(4,2))

    def _clear_drop_indicator(self):
        if self._drop_line_id:
            try:
                self._drop_canvas.delete(self._drop_line_id)
            except Exception:
                pass
            self._drop_line_id = None

    def _do_reorder(self, tab, new_idx):
        old = self._tabs.index(tab)
        self._tabs.pop(old)
        if new_idx > old:
            new_idx -= 1
        self._tabs.insert(new_idx, tab)
        if tab.group is not None:
            self._do_ungroup_tab(tab, rebuild=False)
        self._rebuild_tab_buttons()

    def _do_group(self, tab, target_group):
        tab.group = target_group
        self._rebuild_tab_buttons()

    def _do_ungroup_tab(self, tab, rebuild=True):
        old_grp = tab.group
        tab.group = None
        if old_grp:
            remaining = [t for t in self._tabs if t.group is old_grp]
            if len(remaining) == 1:
                remaining[0].group = None
        if rebuild:
            self._rebuild_tab_buttons()

    # ----------------------------------------------------------------
    # Group drag
    # ----------------------------------------------------------------
    def _on_group_press(self, event, group):
        self._drag_group       = None
        self._drag_grp_start_x = event.x_root
        self._drag_grp_moved   = False

    def _on_group_drag(self, event, group):
        if abs(event.x_root - self._drag_grp_start_x) > 8:
            self._drag_group   = group
            self._drag_grp_moved = True
            self._update_group_drop_indicator(event.x_root)

    def _on_group_release(self, event, group):
        self._clear_drop_indicator()
        if not self._drag_grp_moved or self._drag_group is None:
            self._drag_group   = None
            self._drag_grp_moved = False
            return
        drag = self._drag_group
        self._drag_group   = None
        self._drag_grp_moved = False
        result = self._find_group_drop_target(event.x_root)
        if result is None:
            return
        kind, payload = result
        if kind == "reorder":
            self._do_group_reorder(drag, payload)
        elif kind == "merge":
            self._do_merge_groups(drag, payload)

    def _find_group_drop_target(self, x_root):
        seen = set()
        zones = []
        for tab in self._tabs:
            grp = tab.group
            if grp is None or grp in seen or grp is self._drag_group:
                continue
            seen.add(grp)
            con = grp.container
            if con:
                try:
                    bx = con.winfo_rootx()
                    bw = con.winfo_width()
                    zones.append((bx, bx+bw, grp))
                except Exception:
                    pass
        for bx, bx_end, grp in zones:
            if bx <= x_root <= bx_end:
                rel = (x_root - bx) / max(bx_end - bx, 1)
                if 0.2 <= rel <= 0.8:
                    return ("merge", grp)
                return ("reorder", x_root)
        return ("reorder", x_root)

    def _update_group_drop_indicator(self, x_root):
        self._update_drop_indicator(x_root)

    def _do_group_reorder(self, group, screen_x):
        tabs_in  = [t for t in self._tabs if t.group is group]
        tabs_out = [t for t in self._tabs if t.group is not group]
        insert_at = len(tabs_out)
        for i, t in enumerate(tabs_out):
            if t.btn_frame:
                try:
                    if t.btn_frame.winfo_rootx() > screen_x:
                        insert_at = i
                        break
                except Exception:
                    pass
        new_order = tabs_out[:insert_at] + tabs_in + tabs_out[insert_at:]
        self._tabs = new_order
        self._rebuild_tab_buttons()

    def _do_merge_groups(self, src, tgt):
        for tab in self._tabs:
            if tab.group is src:
                tab.group = tgt
        self._rebuild_tab_buttons()

    # ----------------------------------------------------------------
    # Group actions
    # ----------------------------------------------------------------
    def _toggle_collapse(self, group):
        group.collapsed = not group.collapsed
        if group.collapse_btn:
            group.collapse_btn.configure(
                text="▸" if group.collapsed else "▾")
        self._rebuild_tab_buttons()

    def _group_context(self, event, group):
        T  = self._T
        kw = dict(tearoff=0, bg=T["menu_bg"], fg=T["menu_fg"],
                  activebackground=T["menu_sel"], activeforeground=T["menu_fg"])
        m = tk.Menu(self, **kw)
        lbl = "Expand" if group.collapsed else "Collapse"
        m.add_command(label=lbl,             command=lambda: self._toggle_collapse(group))
        m.add_command(label="Rename...",     command=lambda: self._rename_group(group))
        m.add_command(label="Change Color...",command=lambda: self._pick_group_color(group))
        m.add_separator()
        m.add_command(label="Ungroup All",   command=lambda: self._ungroup(group))
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def _rename_group(self, group):
        name = simpledialog.askstring("Rename Group", "Enter group name:",
            initialvalue=group.label, parent=self)
        if name and name.strip():
            group.label = name.strip()
            if group.label_lbl:
                group.label_lbl.configure(text=group.label)

    def _pick_group_color(self, group):
        result = colorchooser.askcolor(color=group.color,
            parent=self, title="Group Color")
        if result and result[1]:
            group.color = result[1]
            self._rebuild_tab_buttons()

    def _ungroup(self, group):
        for tab in self._tabs:
            if tab.group is group:
                tab.group = None
        self._rebuild_tab_buttons()

    # ----------------------------------------------------------------
    # Tab context menu
    # ----------------------------------------------------------------
    def _tab_context(self, event, tab):
        T  = self._T
        kw = dict(tearoff=0, bg=T["menu_bg"], fg=T["menu_fg"],
                  activebackground=T["menu_sel"], activeforeground=T["menu_fg"])
        m = tk.Menu(self, **kw)
        m.add_command(label="Rename...",          command=lambda: self._rename_tab(tab))
        m.add_command(label="Tab Color...",       command=lambda: self._show_tab_color_picker(tab))
        m.add_command(label="Text Background...", command=lambda: self._pick_text_bg(tab))
        m.add_command(label="Reset Text Colors",  command=lambda: self._reset_text_colors(tab))
        m.add_separator()
        m.add_command(label="Close",              command=lambda: self.cmd_close_tab(tab))
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def _rename_tab(self, tab):
        name = simpledialog.askstring("Rename Tab", "Enter tab name:",
            initialvalue=tab.title.rstrip(" *"), parent=self)
        if name and name.strip():
            tab.title = name.strip()
            if tab.title_lbl:
                tab.title_lbl.configure(text=tab.title)

    def _show_tab_color_picker(self, tab):
        T   = self._T
        win = tk.Toplevel(self)
        win.title("Tab Color")
        win.configure(bg=T["tab_bar"])
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        tk.Label(win, text="Choose a color:", bg=T["tab_bar"],
                 fg=T["text_fg"], font=("Segoe UI", 10), pady=8).pack()
        row = tk.Frame(win, bg=T["tab_bar"])
        row.pack(padx=12, pady=(0,8))
        def pick(c):
            tab.color = c
            if tab.dot_canvas and tab.oval_id:
                tab.dot_canvas.itemconfig(tab.oval_id, fill=c)
            win.destroy()
        for c in _ACCENT_CYCLE:
            b = tk.Canvas(row, width=24, height=24, bg=T["tab_bar"],
                          highlightthickness=0, cursor="hand2")
            b.pack(side="left", padx=3)
            b.create_oval(3,3,21,21, fill=c, outline="")
            b.bind("<Button-1>", lambda e, col=c: pick(col))
        def custom():
            r = colorchooser.askcolor(color=tab.color or T["default_dot"],
                parent=win, title="Custom Color")
            if r and r[1]:
                pick(r[1])
        tk.Button(win, text="Custom...", command=custom,
                  bg=T["tab_idle"], fg=T["text_fg"],
                  relief="flat", pady=4).pack(pady=(0,10))

    # ----------------------------------------------------------------
    # Per-tab text colors
    # ----------------------------------------------------------------
    def _pick_text_bg(self, tab):
        r = colorchooser.askcolor(color=tab.text_bg or self._T["text_bg"],
            parent=self, title="Text Background Color")
        if r and r[1]:
            tab.text_bg = r[1]
            self._apply_text_colors(tab)

    def _pick_text_fg(self, tab):
        r = colorchooser.askcolor(color=tab.text_fg or self._T["text_fg"],
            parent=self, title="Text Color")
        if r and r[1]:
            tab.text_fg = r[1]
            self._apply_text_colors(tab)

    def _reset_text_colors(self, tab):
        tab.text_bg = None
        tab.text_fg = None
        self._apply_text_colors(tab)

    def _apply_text_colors(self, tab):
        if tab.text:
            bg = tab.text_bg or self._T["text_bg"]
            fg = tab.text_fg or self._T["text_fg"]
            tab.text.configure(bg=bg, fg=fg, insertbackground=fg)

    # ----------------------------------------------------------------
    # Settings
    # ----------------------------------------------------------------
    def _startup_enabled(self):
        """Return True if the Jotter startup registry entry exists."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_REG_KEY)
            winreg.QueryValueEx(key, _STARTUP_REG_NAME)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def _toggle_startup(self):
        """Add or remove the Windows startup registry entry."""
        enable = self._launch_with_windows.get()
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _STARTUP_REG_KEY,
                                 0, winreg.KEY_SET_VALUE)
            if enable:
                if getattr(sys, "frozen", False):
                    target = f'"{sys.executable}"'
                else:
                    pythonw = os.path.join(os.path.dirname(sys.executable),
                                           "pythonw.exe")
                    script  = os.path.abspath(__file__)
                    target  = f'"{pythonw}" "{script}"'
                winreg.SetValueEx(key, _STARTUP_REG_NAME, 0,
                                  winreg.REG_SZ, target)
            else:
                try:
                    winreg.DeleteValue(key, _STARTUP_REG_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            messagebox.showerror("Startup Error",
                                 f"Could not update startup entry:\n{e}",
                                 parent=self)
            # Revert the checkbox
            self._launch_with_windows.set(not enable)

    def _load_settings(self):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_settings(self, data):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _cmd_set_default_dir(self):
        chosen = filedialog.askdirectory(
            parent=self,
            title="Choose Default Save Folder",
            initialdir=self._default_dir)
        if not chosen:
            return
        self._default_dir = os.path.normpath(chosen)
        settings = self._load_settings()
        settings["default_dir"] = self._default_dir
        self._save_settings(settings)
        messagebox.showinfo(
            "Default Folder Set",
            f"Default save folder is now:\n{self._default_dir}",
            parent=self)

    # ----------------------------------------------------------------
    # About
    # ----------------------------------------------------------------
    def _show_about(self):
        T   = self._T
        win = tk.Toplevel(self)
        win.title("About Jotter")
        win.configure(bg=T["bg"])
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        tk.Label(win, text="Jotter", bg=T["bg"], fg=T["menu_fg"],
                 font=("Segoe UI", 20, "bold"), pady=12).pack()
        tk.Label(win, text="Version 2.3", bg=T["bg"], fg=T["menu_fg"],
                 font=("Segoe UI", 11)).pack()
        tk.Label(win, text="A lightweight rich-text editor", bg=T["bg"],
                 fg=T["close_fg"], font=("Segoe UI", 10), pady=4).pack()

        frame = tk.Frame(win, bg=T["bg"], padx=20, pady=8)
        frame.pack(fill="x")
        features = [
            # -- Tabs --
            ("— Tabs —",        ""),
            ("Ctrl+N",          "New tab"),
            ("Ctrl+W",          "Close tab"),
            ("＋ button",        "New tab (tab bar)"),
            ("Drag tab",        "Reorder or group tabs"),
            ("Right-click tab", "Rename, accent color, text bg/fg, close"),
            # -- Files --
            ("— Files —",       ""),
            ("Ctrl+O",          "Open file (.txt, .rtf, .md)"),
            ("Ctrl+S",          "Save"),
            ("Ctrl+Shift+S",    "Save As"),
            ("Drag & drop",     "Drop a file onto the window to open it"),
            ("File > Set Default Folder", "Change the default save location"),
            # -- Editing --
            ("— Editing —",     ""),
            ("Ctrl+Z / Ctrl+Y", "Undo / Redo"),
            ("Ctrl+A",          "Select all"),
            ("Ctrl+F",          "Find"),
            ("Ctrl+H",          "Find & Replace"),
            # -- Formatting --
            ("— Formatting —",  ""),
            ("Ctrl+B",          "Bold"),
            ("Ctrl+I",          "Italic"),
            ("Ctrl+U",          "Underline"),
            ("S̶  button",       "Strikethrough"),
            ("Aa▾",             "Change case: UPPER / lower / Capitalize / tOGGLE"),
            ("↵ Wrap",          "Toggle word wrap per tab"),
            ("✕ fmt",           "Clear all formatting (selection or whole doc)"),
            ("Toolbar",         "Font family & size, colors, alignment"),
            ("Right-click text","Cut / Copy / Paste / Format / Case"),
            # -- Options --
            ("— Options —",     ""),
            ("Options menu",    "Dark mode, Always on Top, Launch with Windows"),
            ("Hover controls",  "Tooltips on all toolbar & tab controls"),
            ("Session restore", "Reopens tabs, content, position & theme"),
        ]
        for key, desc in features:
            row = tk.Frame(frame, bg=T["bg"])
            row.pack(fill="x", pady=1)
            if desc == "":
                # Section header
                tk.Label(row, text=key, bg=T["bg"], fg=T["close_fg"],
                         font=("Segoe UI", 8, "italic"),
                         anchor="w").pack(side="left", pady=(6, 0))
            else:
                tk.Label(row, text=key, bg=T["bg"], fg=T["default_dot"],
                         font=("Consolas", 9), width=22, anchor="e").pack(side="left")
                tk.Label(row, text="  " + desc, bg=T["bg"], fg=T["menu_fg"],
                         font=("Segoe UI", 9), anchor="w").pack(side="left")
        tk.Frame(win, bg=T["border"], height=1).pack(fill="x", padx=20, pady=(8,0))
        mit = (
            "MIT License\n"
            "Copyright (c) 2024 Chris Lutz\n\n"
            "Permission is hereby granted, free of charge, to any person\n"
            "obtaining a copy of this software and associated documentation\n"
            "files (the Software), to deal in the Software without restriction,\n"
            "including without limitation the rights to use, copy, modify,\n"
            "merge, publish, distribute, sublicense, and/or sell copies of\n"
            "the Software, and to permit persons to whom the Software is\n"
            "furnished to do so, subject to the following conditions:\n\n"
            "The above copyright notice and this permission notice shall be\n"
            "included in all copies or substantial portions of the Software.\n\n"
            "THE SOFTWARE IS PROVIDED AS IS, WITHOUT WARRANTY OF ANY KIND,\n"
            "EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES\n"
            "OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND\n"
            "NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT\n"
            "HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,\n"
            "WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING\n"
            "FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR\n"
            "OTHER DEALINGS IN THE SOFTWARE."
        )
        tk.Label(win, text=mit, bg=T["bg"], fg=T["close_fg"],
                 font=("Consolas", 8), justify="left",
                 padx=20, pady=8).pack(anchor="w")
        tk.Button(win, text="Close", command=win.destroy,
                  bg=T["tab_idle"], fg=T["menu_fg"], relief="flat",
                  padx=20, pady=4).pack(pady=(4,14))

    # ----------------------------------------------------------------
    # File commands
    # ----------------------------------------------------------------
    def _refresh_tab_label(self, tab):
        title = tab.title
        if tab.modified:
            title += " *"
        if tab.title_lbl:
            tab.title_lbl.configure(text=title)
        base = tab.title.rstrip(" *") if tab.title else "Jotter"
        self.title(base + (" *" if tab.modified else "") + " — Jotter")

    def cmd_open(self, event=None):
        tab = self._active
        cur_dir = (os.path.dirname(tab.filepath)
                   if tab and tab.filepath else self._default_dir)
        path = filedialog.askopenfilename(
            parent=self,
            initialdir=cur_dir,
            filetypes=[("Text & RTF files", "*.txt *.rtf *.md"),
                       ("Text files", "*.txt"),
                       ("Markdown files", "*.md"),
                       ("RTF files",  "*.rtf"),
                       ("All files",  "*.*")])
        if path:
            self._open_path(path)

    def _open_path(self, path):
        """Open a file by path, reusing the active tab only if it's blank."""
        path = os.path.normpath(path)
        tab = self._active
        if tab is None or tab.modified or tab.filepath is not None:
            tab = Tab(os.path.basename(path))
            self._tabs.append(tab)
            self._make_text_area(tab)
        else:
            tab.title = os.path.basename(path)
        tab.filepath = path
        tab.modified = False
        self._rebuild_tab_buttons()
        self._activate(tab)
        tw = tab.text
        tw.configure(state="normal")
        tw.delete("1.0", "end")
        if path.lower().endswith(".rtf"):
            try:
                with open(path, "rb") as f:
                    raw = f.read().decode("latin-1", errors="replace")
                rtf_io.parse_rtf(tw, raw)
            except Exception as e:
                messagebox.showerror("Open Error", str(e), parent=self)
        else:
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    tw.insert("1.0", f.read())
            except Exception as e:
                messagebox.showerror("Open Error", str(e), parent=self)
        tw.edit_reset()
        self._refresh_tab_label(tab)

    def _on_drop(self, event):
        """Handle files dragged onto the window."""
        # tkinterdnd2 wraps paths with spaces in {braces}
        paths = re.findall(r'\{([^}]+)\}|(\S+)', event.data)
        for braced, plain in paths:
            path = braced or plain
            if os.path.isfile(path):
                self._open_path(path)

    def cmd_save(self, event=None):
        if self._active is None:
            return
        if self._active.filepath is None:
            self.cmd_save_as()
            return
        self._write_file(self._active, self._active.filepath)

    def cmd_save_as(self, event=None):
        if self._active is None:
            return
        ext = os.path.splitext(self._active.filepath or "")[1].lower()
        default_ext = ext if ext in (".rtf", ".md", ".txt") else ".txt"
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=default_ext,
            initialdir=(os.path.dirname(self._active.filepath)
                        if self._active.filepath else self._default_dir),
            filetypes=[("RTF files", "*.rtf"),
                       ("Text files", "*.txt"),
                       ("Markdown files", "*.md"),
                       ("All files",  "*.*")],
            initialfile=self._active.title.rstrip(" *") or "Untitled")
        if not path:
            return
        self._active.filepath = path
        self._active.title    = os.path.basename(path)
        self._write_file(self._active, path)

    def _write_file(self, tab, path):
        tw = tab.text
        try:
            if path.lower().endswith(".rtf"):
                rtf_bytes = rtf_io.generate_rtf(tw)
                with open(path, "wb") as f:
                    f.write(rtf_bytes.encode("latin-1", errors="replace"))
            else:
                content = tw.get("1.0", "end-1c")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
            tab.modified = False
            self._refresh_tab_label(tab)
        except Exception as e:
            messagebox.showerror("Save Error", str(e), parent=self)

    def cmd_toggle_theme(self, event=None):
        self._theme_name = "light" if self._theme_name == "dark" else "dark"
        self._T = THEMES[self._theme_name]
        self.configure(bg=self._T["bg"])
        self._rebuild_tab_buttons()
        for tab in self._tabs:
            self._apply_text_colors(tab)
            if tab.linenos:
                T = self._T
                tab.linenos.configure(bg=T["ln_bg"], fg=T["ln_fg"])
        if hasattr(self, "_status_left"):
            T = self._T
            self._status_left.master.configure(bg=T["status_bg"])
            self._status_left.configure(bg=T["status_bg"], fg=T["status_fg"])
            self._status_right.configure(bg=T["status_bg"], fg=T["status_fg"])

    # ----------------------------------------------------------------
    # Formatting toolbar
    # ----------------------------------------------------------------
    def _build_fmt_toolbar(self):
        T   = self._T
        bar = tk.Frame(self, bg=T["tab_bar"], pady=2)
        bar.pack(side="top", fill="x")
        self._fmt_bar = bar

        families = sorted(tkfont.families())
        self._font_var = tk.StringVar(value="Consolas")
        fc = ttk.Combobox(bar, textvariable=self._font_var, values=families,
                          width=18, state="readonly")
        fc.pack(side="left", padx=(4,2))
        fc.bind("<<ComboboxSelected>>",
                lambda e: self._fmt_set_font(self._font_var.get(),
                                             int(self._size_var.get())))
        ToolTip(fc, "Font family\nApplied to selected text")

        sizes = [str(s) for s in [8,9,10,11,12,14,16,18,20,24,28,32,36,48,72]]
        self._size_var = tk.StringVar(value="11")
        sc = ttk.Combobox(bar, textvariable=self._size_var, values=sizes,
                          width=4, state="readonly")
        sc.pack(side="left", padx=(0,4))
        sc.bind("<<ComboboxSelected>>",
                lambda e: self._fmt_set_font(self._font_var.get(),
                                             int(self._size_var.get())))
        ToolTip(sc, "Font size (pt)\nApplied to selected text")

        btn_kw = dict(bg=T["tab_idle"], fg=T["toolbar_fg"],
                      relief="flat", padx=6, pady=2,
                      cursor="hand2")

        def _show_case_menu(event=None):
            T2 = self._T
            kw2 = dict(tearoff=0, bg=T2["menu_bg"], fg=T2["menu_fg"],
                       activebackground=T2["menu_sel"],
                       activeforeground=T2["menu_fg"])
            m = tk.Menu(self, **kw2)
            m.add_command(label="UPPER CASE",           command=lambda: self._change_case("upper"))
            m.add_command(label="lower case",            command=lambda: self._change_case("lower"))
            m.add_command(label="Capitalize Each Word",  command=lambda: self._change_case("title"))
            m.add_command(label="tOGGLE cASE",           command=lambda: self._change_case("toggle"))
            try:
                m.tk_popup(case_btn.winfo_rootx(),
                           case_btn.winfo_rooty() + case_btn.winfo_height())
            finally:
                m.grab_release()

        case_btn = tk.Button(bar, text="Aa▾", font=("Segoe UI", 10), **btn_kw,
            command=_show_case_menu)
        case_btn.pack(side="left", padx=(4,6))
        ToolTip(case_btn, "Change case\nUPPER / lower / Capitalize / tOGGLE")

        b_btn = tk.Button(bar, text="B", font=("Segoe UI", 10, "bold"), **btn_kw,
            command=lambda: self._fmt_toggle(rtf_io.tag_bold(),
                font=("Consolas", 11, "bold")))
        b_btn.pack(side="left", padx=1)
        ToolTip(b_btn, "Bold (Ctrl+B)")

        i_btn = tk.Button(bar, text="I", font=("Segoe UI", 10, "italic"), **btn_kw,
            command=lambda: self._fmt_toggle(rtf_io.tag_italic(),
                font=("Consolas", 11, "italic")))
        i_btn.pack(side="left", padx=1)
        ToolTip(i_btn, "Italic (Ctrl+I)")

        u_btn = tk.Button(bar, text="U", font=("Segoe UI", 10), **btn_kw,
            command=lambda: self._fmt_toggle(rtf_io.tag_underline(),
                underline=True))
        u_btn.pack(side="left", padx=1)
        ToolTip(u_btn, "Underline (Ctrl+U)")

        s_btn = tk.Button(bar, text="S̶", font=("Segoe UI", 10), **btn_kw,
            command=lambda: self._fmt_toggle(rtf_io.tag_strikethrough(),
                overstrike=True))
        s_btn.pack(side="left", padx=1)
        ToolTip(s_btn, "Strikethrough")

        self._fg_swatch = tk.Canvas(bar, width=22, height=22,
            bg=T["tab_idle"], highlightthickness=1,
            highlightbackground=T["border"], cursor="hand2")
        self._fg_swatch.pack(side="left", padx=(6,1))
        self._fg_rect = self._fg_swatch.create_rectangle(3,3,19,19,
            fill="#ff0000", outline="")
        self._fg_swatch.bind("<Button-1>", lambda e: self._fmt_pick_fg())
        ToolTip(self._fg_swatch, "Text color\nClick to choose color")
        tk.Label(bar, text="A", bg=T["tab_idle"], fg=T["toolbar_fg"],
                 font=("Segoe UI", 9)).pack(side="left")

        self._bg_swatch = tk.Canvas(bar, width=22, height=22,
            bg=T["tab_idle"], highlightthickness=1,
            highlightbackground=T["border"], cursor="hand2")
        self._bg_swatch.pack(side="left", padx=(6,1))
        self._bg_rect = self._bg_swatch.create_rectangle(3,3,19,19,
            fill="#ffff00", outline="")
        self._bg_swatch.bind("<Button-1>", lambda e: self._fmt_pick_bg())
        ToolTip(self._bg_swatch, "Highlight color\nClick to choose color")
        tk.Label(bar, text="HL", bg=T["tab_idle"], fg=T["toolbar_fg"],
                 font=("Segoe UI", 9)).pack(side="left")

        tk.Label(bar, text=" ", bg=T["tab_bar"]).pack(side="left", padx=4)
        align_tips = {"left": "Align left", "center": "Align center", "right": "Align right"}
        for sym, align in [("≡L","left"),("≡C","center"),("≡R","right")]:
            ab = tk.Button(bar, text=sym, font=("Segoe UI", 10), **btn_kw,
                command=lambda a=align: self._fmt_set_align(a))
            ab.pack(side="left", padx=1)
            ToolTip(ab, align_tips[align])

        self._wrap_on = tk.BooleanVar(value=True)
        wrap_btn = tk.Checkbutton(bar, text="↵ Wrap", font=("Segoe UI", 10),
            variable=self._wrap_on, command=self._toggle_wrap,
            bg=T["tab_bar"], fg=T["toolbar_fg"],
            selectcolor=T["tab_idle"], activebackground=T["tab_bar"],
            activeforeground=T["toolbar_fg"],
            indicatoron=False, relief="flat", padx=6, pady=2,
            cursor="hand2")
        wrap_btn.pack(side="left", padx=(8,1))
        ToolTip(wrap_btn, "Toggle word wrap\nfor the active tab")
        self._wrap_btn = wrap_btn

        clr_btn = tk.Button(bar, text="✕ fmt", font=("Segoe UI", 10), **btn_kw,
            command=self._fmt_clear)
        clr_btn.pack(side="left", padx=(8,1))
        ToolTip(clr_btn, "Clear all formatting\nfrom selected text")

    def _toggle_wrap(self):
        tab = self._active
        if tab and tab.text:
            wrap_on = self._wrap_on.get()
            tab.text.configure(wrap="word" if wrap_on else "none")
            if tab.hscroll:
                if wrap_on:
                    tab.hscroll.pack_forget()
                else:
                    tab.hscroll.pack(side="bottom", fill="x")

    def _fmt_toggle(self, tag_name, **tag_kw):
        tab = self._active
        if tab is None or tab.text is None:
            return
        tw = tab.text
        try:
            sel_start = tw.index("sel.first")
            sel_end   = tw.index("sel.last")
        except tk.TclError:
            return
        existing = tw.tag_ranges(tag_name)
        has_tag  = False
        idx = sel_start
        while tw.compare(idx, "<", sel_end):
            tags_here = tw.tag_names(idx)
            if tag_name in tags_here:
                has_tag = True
                break
            idx = tw.index("%s +1c" % idx)
        if has_tag:
            tw.tag_remove(tag_name, sel_start, sel_end)
        else:
            tw.tag_add(tag_name, sel_start, sel_end)
            tw.tag_configure(tag_name, **tag_kw)

    def _fmt_apply(self, tag_name, sel_start, sel_end, **tag_kw):
        tab = self._active
        if tab is None or tab.text is None:
            return
        tw = tab.text
        tw.tag_add(tag_name, sel_start, sel_end)
        tw.tag_configure(tag_name, **tag_kw)

    def _fmt_set_font(self, family, size):
        tab = self._active
        if tab is None or tab.text is None:
            return
        tw = tab.text
        try:
            sel_start = tw.index("sel.first")
            sel_end   = tw.index("sel.last")
        except tk.TclError:
            return
        fn_tag = rtf_io.tag_font(family)
        sz_tag = rtf_io.tag_size(size)
        tw.tag_add(fn_tag, sel_start, sel_end)
        tw.tag_configure(fn_tag, font=(family, size))
        tw.tag_add(sz_tag, sel_start, sel_end)
        tw.tag_configure(sz_tag, font=(family, size))

    def _fmt_pick_fg(self):
        current = self._fg_swatch.itemcget(self._fg_rect, "fill") or "#ff0000"
        r = colorchooser.askcolor(color=current, parent=self, title="Text Color")
        if not (r and r[1]):
            return
        color = r[1]
        self._fg_swatch.itemconfig(self._fg_rect, fill=color)
        tab = self._active
        if tab is None or tab.text is None:
            return
        tw = tab.text
        try:
            sel_start = tw.index("sel.first")
            sel_end   = tw.index("sel.last")
        except tk.TclError:
            return
        tag = rtf_io.tag_fg(color)
        tw.tag_add(tag, sel_start, sel_end)
        tw.tag_configure(tag, foreground=color)

    def _fmt_pick_bg(self):
        current = self._bg_swatch.itemcget(self._bg_rect, "fill") or "#ffff00"
        r = colorchooser.askcolor(color=current, parent=self, title="Highlight Color")
        if not (r and r[1]):
            return
        color = r[1]
        self._bg_swatch.itemconfig(self._bg_rect, fill=color)
        tab = self._active
        if tab is None or tab.text is None:
            return
        tw = tab.text
        try:
            sel_start = tw.index("sel.first")
            sel_end   = tw.index("sel.last")
        except tk.TclError:
            return
        tag = rtf_io.tag_bg(color)
        tw.tag_add(tag, sel_start, sel_end)
        tw.tag_configure(tag, background=color)

    def _fmt_set_align(self, align):
        tab = self._active
        if tab is None or tab.text is None:
            return
        tw = tab.text
        try:
            sel_start = tw.index("sel.first")
            sel_end   = tw.index("sel.last")
        except tk.TclError:
            ins = tw.index("insert")
            sel_start = tw.index("%s linestart" % ins)
            sel_end   = tw.index("%s lineend"   % ins)
        for a in ("left", "center", "right"):
            tw.tag_remove(rtf_io.tag_align(a), sel_start, sel_end)
        tag = rtf_io.tag_align(align)
        tw.tag_add(tag, sel_start, sel_end)
        tw.tag_configure(tag, justify=align)

    def _fmt_clear(self):
        tab = self._active
        if tab is None or tab.text is None:
            return
        tw = tab.text
        try:
            sel_start = tw.index("sel.first")
            sel_end   = tw.index("sel.last")
        except tk.TclError:
            sel_start, sel_end = "1.0", "end"
        for tag in tw.tag_names():
            if tag.startswith("fmt_"):
                tw.tag_remove(tag, sel_start, sel_end)

    def _change_case(self, mode):
        tab = self._active
        if tab is None or tab.text is None:
            return
        tw = tab.text
        try:
            sel_start = tw.index("sel.first")
            sel_end   = tw.index("sel.last")
        except tk.TclError:
            return
        text = tw.get(sel_start, sel_end)
        if mode == "upper":
            new = text.upper()
        elif mode == "lower":
            new = text.lower()
        elif mode == "title":
            new = text.title()
        elif mode == "toggle":
            new = "".join(c.lower() if c.isupper() else c.upper() for c in text)
        else:
            new = text
        if new == text:
            return
        saved_tags = []
        for tag in tw.tag_names():
            ranges = tw.tag_ranges(tag)
            for i in range(0, len(ranges), 2):
                r0 = str(ranges[i])
                r1 = str(ranges[i+1])
                if tw.compare(r0, ">=", sel_start) and tw.compare(r1, "<=", sel_end):
                    saved_tags.append((tag, r0, r1))
        tw.delete(sel_start, sel_end)
        tw.insert(sel_start, new)
        new_end = tw.index("%s +%dc" % (sel_start, len(new)))
        for tag, r0, r1 in saved_tags:
            tw.tag_add(tag, r0, min(r1, new_end))
            cfg = {}
            try:
                cfg = {k: v for k, v in tw.tag_configure(tag).items() if v}
            except Exception:
                pass
        tw.tag_add("sel", sel_start, new_end)

    # ----------------------------------------------------------------
    # Find / Replace bar
    # ----------------------------------------------------------------
    def _build_findbar(self):
        T   = self._T
        bar = tk.Frame(self, bg=T["tab_bar"], pady=3)
        self._findbar = bar

        tk.Label(bar, text="Find:", bg=T["tab_bar"], fg=T["toolbar_fg"],
                 font=("Segoe UI", 10)).pack(side="left", padx=(6,2))
        self._find_var = tk.StringVar()
        fe = tk.Entry(bar, textvariable=self._find_var, width=22,
                      bg=T["text_bg"], fg=T["text_fg"],
                      insertbackground=T["text_fg"], relief="flat", bd=2)
        fe.pack(side="left", padx=2)
        self._find_entry = fe
        fe.bind("<Return>",         lambda e: self._find_step(1))
        fe.bind("<Shift-Return>",   lambda e: self._find_step(-1))
        self._find_var.trace_add("write", lambda *_: self._run_find())

        self._match_lbl = tk.Label(bar, text="", bg=T["tab_bar"],
                                   fg=T["close_fg"], font=("Segoe UI", 9))
        self._match_lbl.pack(side="left", padx=4)

        tk.Button(bar, text="▲", bg=T["tab_idle"], fg=T["toolbar_fg"],
                  relief="flat", padx=4,
                  command=lambda: self._find_step(-1)).pack(side="left", padx=1)
        tk.Button(bar, text="▼", bg=T["tab_idle"], fg=T["toolbar_fg"],
                  relief="flat", padx=4,
                  command=lambda: self._find_step(1)).pack(side="left", padx=1)

        self._replace_var = tk.StringVar()
        self._replace_lbl = tk.Label(bar, text="Replace:", bg=T["tab_bar"],
                                     fg=T["toolbar_fg"], font=("Segoe UI", 10))
        re_entry = tk.Entry(bar, textvariable=self._replace_var, width=22,
                            bg=T["text_bg"], fg=T["text_fg"],
                            insertbackground=T["text_fg"], relief="flat", bd=2)
        self._replace_entry = re_entry

        self._replace_btn = tk.Button(bar, text="Replace",
            bg=T["tab_idle"], fg=T["toolbar_fg"], relief="flat", padx=6,
            command=self._do_replace)
        self._replace_all_btn = tk.Button(bar, text="Replace All",
            bg=T["tab_idle"], fg=T["toolbar_fg"], relief="flat", padx=6,
            command=self._do_replace_all)

        self._case_var = tk.BooleanVar(value=False)
        tk.Checkbutton(bar, text="Aa", variable=self._case_var,
                       bg=T["tab_bar"], fg=T["toolbar_fg"],
                       selectcolor=T["tab_idle"], activebackground=T["tab_bar"],
                       command=self._run_find).pack(side="left", padx=4)

        tk.Button(bar, text="✕", bg=T["tab_bar"], fg=T["close_fg"],
                  relief="flat", padx=4,
                  command=self._hide_find_bar).pack(side="right", padx=4)

        self._find_matches   = []
        self._find_match_idx = -1

    def _show_find_bar(self, show_replace=False):
        T = self._T
        self._findbar.pack(side="bottom", fill="x",
                           before=self._body_frame)
        if show_replace:
            self._replace_lbl.pack(side="left", padx=(12,2))
            self._replace_entry.pack(side="left", padx=2)
            self._replace_btn.pack(side="left", padx=2)
            self._replace_all_btn.pack(side="left", padx=2)
        else:
            self._replace_lbl.pack_forget()
            self._replace_entry.pack_forget()
            self._replace_btn.pack_forget()
            self._replace_all_btn.pack_forget()
        self._find_entry.focus_set()
        self._find_entry.select_range(0, "end")
        self._run_find()

    def _hide_find_bar(self):
        self._findbar.pack_forget()
        self._clear_find_highlights()
        if self._active and self._active.text:
            self._active.text.focus_set()

    def _run_find(self, *_):
        self._clear_find_highlights()
        self._find_matches   = []
        self._find_match_idx = -1
        query = self._find_var.get()
        if not query:
            self._match_lbl.configure(text="")
            return
        tab = self._active
        if tab is None or tab.text is None:
            return
        tw  = tab.text
        nocase = not self._case_var.get()
        start  = "1.0"
        while True:
            pos = tw.search(query, start, stopindex="end", nocase=nocase)
            if not pos:
                break
            end_pos = "%s +%dc" % (pos, len(query))
            tw.tag_add("find_match", pos, end_pos)
            self._find_matches.append(pos)
            start = end_pos
        tw.tag_configure("find_match", background="#515c6a", foreground="#ffffff")
        n = len(self._find_matches)
        self._match_lbl.configure(text="%d match%s" % (n, "es" if n != 1 else ""))
        if n:
            self._find_step(1)

    def _find_step(self, direction):
        if not self._find_matches:
            return
        n = len(self._find_matches)
        self._find_match_idx = (self._find_match_idx + direction) % n
        pos = self._find_matches[self._find_match_idx]
        tab = self._active
        if tab is None or tab.text is None:
            return
        tw = tab.text
        query   = self._find_var.get()
        end_pos = "%s +%dc" % (pos, len(query))
        tw.tag_remove("find_current", "1.0", "end")
        tw.tag_add("find_current", pos, end_pos)
        tw.tag_configure("find_current", background="#f6a623", foreground="#000000")
        tw.see(pos)
        self._match_lbl.configure(
            text="%d / %d" % (self._find_match_idx + 1, n))

    def _clear_find_highlights(self):
        for tab in self._tabs:
            if tab.text:
                tab.text.tag_remove("find_match",   "1.0", "end")
                tab.text.tag_remove("find_current", "1.0", "end")

    def _do_replace(self):
        if not self._find_matches or self._find_match_idx < 0:
            return
        tab = self._active
        if tab is None or tab.text is None:
            return
        tw      = tab.text
        pos     = self._find_matches[self._find_match_idx]
        query   = self._find_var.get()
        repl    = self._replace_var.get()
        end_pos = "%s +%dc" % (pos, len(query))
        tw.delete(pos, end_pos)
        tw.insert(pos, repl)
        self._run_find()

    def _do_replace_all(self):
        tab = self._active
        if tab is None or tab.text is None:
            return
        query = self._find_var.get()
        repl  = self._replace_var.get()
        if not query:
            return
        tw     = tab.text
        nocase = not self._case_var.get()
        count  = 0
        start  = "1.0"
        while True:
            pos = tw.search(query, start, stopindex="end", nocase=nocase)
            if not pos:
                break
            end_pos = "%s +%dc" % (pos, len(query))
            tw.delete(pos, end_pos)
            tw.insert(pos, repl)
            start = "%s +%dc" % (pos, len(repl))
            count += 1
        self._match_lbl.configure(text="Replaced %d" % count)
        self._clear_find_highlights()
        self._find_matches   = []
        self._find_match_idx = -1

    # ----------------------------------------------------------------
    # Text area right-click context menu
    # ----------------------------------------------------------------
    def _text_context(self, event, tab):
        T  = self._T
        kw = dict(tearoff=0, bg=T["menu_bg"], fg=T["menu_fg"],
                  activebackground=T["menu_sel"], activeforeground=T["menu_fg"])
        m = tk.Menu(self, **kw)
        tw = tab.text
        m.add_command(label="Cut",
            command=lambda: tw.event_generate("<<Cut>>"))
        m.add_command(label="Copy",
            command=lambda: tw.event_generate("<<Copy>>"))
        m.add_command(label="Paste",
            command=lambda: tw.event_generate("<<Paste>>"))
        m.add_command(label="Delete",
            command=lambda: tw.delete("sel.first", "sel.last"))
        m.add_separator()
        m.add_command(label="Select All",
            command=lambda: (tw.tag_add("sel", "1.0", "end"),
                             tw.mark_set("insert", "end")))
        m.add_separator()
        m.add_command(label="Bold",
            command=lambda: self._fmt_toggle(rtf_io.tag_bold(),
                font=("Consolas",11,"bold")))
        m.add_command(label="Italic",
            command=lambda: self._fmt_toggle(rtf_io.tag_italic(),
                font=("Consolas",11,"italic")))
        m.add_command(label="Underline",
            command=lambda: self._fmt_toggle(rtf_io.tag_underline(),
                underline=True))
        m.add_command(label="Strikethrough",
            command=lambda: self._fmt_toggle(rtf_io.tag_strikethrough(),
                overstrike=True))
        m.add_command(label="Clear Formatting", command=self._fmt_clear)
        cc = tk.Menu(m, **kw)
        cc.add_command(label="UPPER CASE",          command=lambda: self._change_case("upper"))
        cc.add_command(label="lower case",           command=lambda: self._change_case("lower"))
        cc.add_command(label="Capitalize Each Word", command=lambda: self._change_case("title"))
        cc.add_command(label="tOGGLE cASE",          command=lambda: self._change_case("toggle"))
        m.add_cascade(label="Change Case", menu=cc)
        m.add_separator()
        m.add_command(label="Find...",    command=lambda: self._show_find_bar(False))
        m.add_command(label="Replace...", command=lambda: self._show_find_bar(True))
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    # ----------------------------------------------------------------
    # Body / text area
    # ----------------------------------------------------------------
    def _build_body(self):
        T     = self._T
        frame = tk.Frame(self, bg=T["bg"])
        frame.pack(fill="both", expand=True)
        self._body_frame = frame

    def _make_text_area(self, tab):
        T     = self._T
        frame = tk.Frame(self._body_frame, bg=T["bg"])
        tab.text_frame = frame

        # Inner row: line numbers + text widget + vertical scrollbar
        inner = tk.Frame(frame, bg=T["bg"])
        inner.pack(side="top", fill="both", expand=True)

        ln = tk.Text(inner, width=4, padx=4, bg=T["ln_bg"], fg=T["ln_fg"],
                     relief="flat", state="disabled", cursor="arrow",
                     font=("Consolas", 11), spacing1=2,
                     takefocus=False, wrap="none")
        ln.pack(side="left", fill="y")
        tab.linenos = ln

        tw = tk.Text(inner, undo=True, wrap="word",
                     bg=T["text_bg"], fg=T["text_fg"],
                     insertbackground=T["text_fg"],
                     selectbackground=T["text_sel"],
                     relief="flat", bd=8,
                     font=("Consolas", 11), spacing1=2)
        tw.pack(side="left", fill="both", expand=True)
        tab.text = tw

        sb_v = ttk.Scrollbar(inner, orient="vertical", command=tw.yview,
                             style="Jotter.Vertical.TScrollbar")
        sb_v.pack(side="right", fill="y")

        # Horizontal scrollbar — shown only when word wrap is off
        sb_h = ttk.Scrollbar(frame, orient="horizontal", command=tw.xview,
                             style="Jotter.Horizontal.TScrollbar")
        tab.hscroll = sb_h
        # Not packed yet; shown when wrap is toggled off

        tw.configure(
            yscrollcommand=lambda f, l: (sb_v.set(f, l), self._update_linenos(tab)),
            xscrollcommand=sb_h.set
        )
        tw.bind("<<Modified>>",    lambda e, t=tab: self._on_modified(t))
        tw.bind("<KeyRelease>",    lambda e, t=tab: self._refresh_status())
        tw.bind("<ButtonRelease>", lambda e, t=tab: self._refresh_status())
        tw.bind("<Button-3>",      lambda e, t=tab: self._text_context(e, t))
        if _DND_AVAILABLE:
            tw.drop_target_register(DND_FILES)
            tw.dnd_bind('<<Drop>>', self._on_drop)
        self._apply_text_colors(tab)

    def _on_modified(self, tab):
        if tab.text.edit_modified():
            if not tab.modified:
                tab.modified = True
                self._refresh_tab_label(tab)
            tab.text.edit_modified(False)
            self._update_linenos(tab)
            self._refresh_status()

    def _update_linenos(self, tab):
        tw = tab.text
        ln = tab.linenos
        ln.configure(state="normal")
        ln.delete("1.0", "end")
        count = int(tw.index("end-1c").split(".")[0])
        ln.insert("1.0", "\n".join(str(i) for i in range(1, count + 1)))
        ln.configure(state="disabled")
        # Sync scroll position with the main text widget
        ln.yview_moveto(tw.yview()[0])

    # ----------------------------------------------------------------
    # Status bar
    # ----------------------------------------------------------------
    def _build_statusbar(self):
        T    = self._T
        bar  = tk.Frame(self, bg=T["status_bg"])
        bar.pack(side="bottom", fill="x")
        lbl_l = tk.Label(bar, text="", bg=T["status_bg"], fg=T["status_fg"],
                         font=("Segoe UI", 9), anchor="w", padx=8)
        lbl_l.pack(side="left")
        lbl_r = tk.Label(bar, text="", bg=T["status_bg"], fg=T["status_fg"],
                         font=("Segoe UI", 9), anchor="e", padx=8)
        lbl_r.pack(side="right")
        self._status_left  = lbl_l
        self._status_right = lbl_r

    def _refresh_status(self):
        tab = self._active
        if tab is None or tab.text is None:
            self._status_left.configure(text="")
            self._status_right.configure(text="")
            return
        tw      = tab.text
        content = tw.get("1.0", "end-1c")
        words   = len(content.split()) if content.strip() else 0
        chars   = len(content)
        try:
            row, col = tw.index("insert").split(".")
            pos_text = "Ln %s  Col %s" % (row, int(col)+1)
        except Exception:
            pos_text = ""
        self._status_left.configure(text=pos_text)
        self._status_right.configure(
            text="%d word%s  %d char%s" % (
                words, "s" if words != 1 else "",
                chars, "s" if chars != 1 else ""))

    # ----------------------------------------------------------------
    # Tab management
    # ----------------------------------------------------------------
    def cmd_new_tab(self, event=None):
        tab = Tab()
        self._tabs.append(tab)
        self._make_text_area(tab)
        self._rebuild_tab_buttons()
        self._activate(tab)

    def cmd_close_tab(self, tab=None, event=None):
        if tab is None:
            tab = self._active
        if tab is None:
            return
        if tab.modified:
            ans = messagebox.askyesnocancel(
                "Unsaved Changes",
                "Save changes to '%s' before closing?" % tab.title.rstrip(" *"),
                parent=self)
            if ans is None:
                return
            if ans:
                self.cmd_save()
        if tab.text_frame:
            tab.text_frame.destroy()
        old_grp = tab.group
        self._tabs.remove(tab)
        if old_grp:
            remain = [t for t in self._tabs if t.group is old_grp]
            if len(remain) == 1:
                remain[0].group = None
        if tab is self._active:
            self._active = None
            if self._tabs:
                self._activate(self._tabs[-1])
        self._rebuild_tab_buttons()
        if not self._tabs:
            self.cmd_new_tab()

    # ----------------------------------------------------------------
    # Session persistence
    # ----------------------------------------------------------------
    def _on_quit(self):
        self._save_session()
        self.destroy()

    def _save_session(self):
        groups  = {}
        tab_list = []
        for tab in self._tabs:
            grp_id = None
            if tab.group:
                gid = str(tab.group.id)
                if gid not in groups:
                    groups[gid] = {
                        "label":    tab.group.label,
                        "color":    tab.group.color,
                        "collapsed": tab.group.collapsed,
                    }
                grp_id = gid
            tab_list.append({
                "title":    tab.title,
                "filepath": tab.filepath,
                "color":    tab.color,
                "text_bg":  tab.text_bg,
                "text_fg":  tab.text_fg,
                "group_id": grp_id,
                "active":   tab is self._active,
                "content":  tab.text.get("1.0", "end-1c") if tab.text else "",
            })
        # Save window geometry (but not if minimised — state is 'iconic')
        geom = None
        if self.state() == "normal":
            geom = self.geometry()
        data = {"tabs": tab_list, "groups": groups,
                "theme": self._theme_name, "geometry": geom}
        try:
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load_session(self):
        if not os.path.exists(SESSION_FILE):
            return False
        try:
            with open(SESSION_FILE, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return False

        geom = data.get("geometry")
        if geom:
            try:
                self.geometry(geom)
            except Exception:
                pass

        theme = data.get("theme", "dark")
        if theme in THEMES:
            self._theme_name = theme
            self._T = THEMES[theme]
            self.configure(bg=self._T["bg"])

        raw_groups = data.get("groups", {})
        if not isinstance(raw_groups, dict):
            raw_groups = {}

        group_map = {}
        for gid, gdata in raw_groups.items():
            grp = TabGroup(color=gdata.get("color"))
            grp.label     = gdata.get("label", grp.label)
            grp.collapsed = gdata.get("collapsed", False)
            group_map[gid] = grp

        active_tab = None
        for tdata in data.get("tabs", []):
            tab          = Tab(tdata.get("title", "Untitled"))
            tab.filepath = tdata.get("filepath")
            tab.color    = tdata.get("color")
            tab.text_bg  = tdata.get("text_bg")
            tab.text_fg  = tdata.get("text_fg")
            gid          = tdata.get("group_id")
            if gid and gid in group_map:
                tab.group = group_map[gid]
            self._tabs.append(tab)
            self._make_text_area(tab)
            content = tdata.get("content", "")
            if content and tab.text:
                tab.text.insert("1.0", content)
                tab.text.edit_reset()
            if tdata.get("active"):
                active_tab = tab

        if not self._tabs:
            return False

        self._rebuild_tab_buttons()
        self._rebuild_tab_buttons()
        self._activate(active_tab or self._tabs[-1])
        return True


def main():
    import traceback
    log_path = os.path.join(_data_dir(), "jotter_error.log")
    try:
        app = Editor()
        app.mainloop()
    except Exception:
        err = traceback.format_exc()
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(err)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
