#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
editor.py -- Dark-mode text editor
  * Multiple tabs with drag-to-reorder and drag-to-group
  * Visual ghost tab follows cursor while dragging
  * Drag a tab out of a group to ungroup it
  * Per-tab accent colour (click the dot or right-click > Change Color)
  * Per-group accent colour  (right-click the group strip)
  * Group labels shown in header, renameable via double-click
  * Dark / light mode toggle  (Options menu)
  * Always-on-top toggle      (Options menu)
  * Line numbers, word & character counter in status bar
  * File operations: New, Open, Save, Save As
  * Undo / redo, cut / copy / paste, select all
  * Session persistence across restarts
  * Group drag-to-reorder and drag-to-merge
"""

import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser, simpledialog
import os
import sys
import json

def _data_dir():
    """Return a writable directory for persistent data.
    When frozen by PyInstaller use AppData\\Roaming\\Jotter;
    otherwise use the directory containing this script."""
    if getattr(sys, "frozen", False):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        d = os.path.join(base, "Jotter")
    else:
        d = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(d, exist_ok=True)
    return d

SESSION_FILE = os.path.join(_data_dir(), ".jotter_session.json")

# ---------------------------------------------------------------------------
# Themes
# ---------------------------------------------------------------------------
THEMES = {
    "dark": {
        "bg":           "#1e1e1e",
        "tab_bar":      "#252526",
        "tab_idle":     "#2d2d2d",
        "tab_active":   "#1e1e1e",
        "tab_hover":    "#383838",
        "text_bg":      "#1e1e1e",
        "text_fg":      "#d4d4d4",
        "text_sel":     "#264f78",
        "ln_bg":        "#252526",
        "ln_fg":        "#858585",
        "status_bg":    "#007acc",
        "status_fg":    "#ffffff",
        "border":       "#474747",
        "close_fg":     "#858585",
        "menu_bg":      "#252526",
        "menu_fg":      "#cccccc",
        "menu_sel":     "#094771",
        "drop_line":    "#ffffff",
        "default_dot":  "#569cd6",
    },
    "light": {
        "bg":           "#ffffff",
        "tab_bar":      "#f3f3f3",
        "tab_idle":     "#ececec",
        "tab_active":   "#ffffff",
        "tab_hover":    "#e0e0e0",
        "text_bg":      "#ffffff",
        "text_fg":      "#1e1e1e",
        "text_sel":     "#add6ff",
        "ln_bg":        "#f3f3f3",
        "ln_fg":        "#999999",
        "status_bg":    "#007acc",
        "status_fg":    "#ffffff",
        "border":       "#cccccc",
        "close_fg":     "#717171",
        "menu_bg":      "#f3f3f3",
        "menu_fg":      "#1e1e1e",
        "menu_sel":     "#0060c0",
        "drop_line":    "#333333",
        "default_dot":  "#0078d4",
    },
}

_ACCENT_CYCLE = [
    "#569cd6", "#4ec9b0", "#dcdcaa", "#ce9178",
    "#9cdcfe", "#c586c0", "#f48771", "#b5cea8",
]

_GROUP_COLORS = [
    "#e06c75", "#e5c07b", "#98c379", "#56b6c2",
    "#61afef", "#c678dd", "#d19a66",
]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
class TabGroup:
    _ctr = 0
    def __init__(self, color=None):
        TabGroup._ctr += 1
        self.id        = TabGroup._ctr
        self.color     = color or _GROUP_COLORS[(TabGroup._ctr - 1) % len(_GROUP_COLORS)]
        self.collapsed = False
        self.label     = "Group %d" % TabGroup._ctr
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
        self.group      = None
        self.text_frame = None
        self.text       = None
        self.linenos    = None
        self.btn_frame  = None
        self.dot_canvas = None
        self.oval_id    = None
        self.title_lbl  = None
        self.close_lbl  = None


# ---------------------------------------------------------------------------
# Main editor window
# ---------------------------------------------------------------------------
class Editor(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Jotter")
        self.geometry("1100x740")
        self.minsize(640, 440)

        self._always_on_top = tk.BooleanVar(value=False)
        self._theme_name    = "dark"
        self._T             = THEMES["dark"]
        self._tabs          = []
        self._active        = None
        self._accent_idx    = 0

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
        self.protocol("WM_DELETE_WINDOW", self._on_quit)

        if not self._load_session():
            self.cmd_new_tab()

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------
    def _build_menu(self):
        T  = self._T
        kw = dict(tearoff=0, bg=T["menu_bg"], fg=T["menu_fg"],
                  activebackground=T["menu_sel"], activeforeground=T["menu_fg"],
                  relief="flat", bd=0)
        mb = tk.Menu(self, **kw)
        self.configure(menu=mb)

        fm = tk.Menu(mb, **kw)
        fm.add_command(label="New Tab          Ctrl+N",       command=self.cmd_new_tab)
        fm.add_command(label="Open...          Ctrl+O",       command=self.cmd_open)
        fm.add_separator()
        fm.add_command(label="Save             Ctrl+S",       command=self.cmd_save)
        fm.add_command(label="Save As...       Ctrl+Shift+S", command=self.cmd_save_as)
        fm.add_separator()
        fm.add_command(label="Close Tab        Ctrl+W",       command=self.cmd_close_tab)
        mb.add_cascade(label="File", menu=fm)

        em = tk.Menu(mb, **kw)
        em.add_command(label="Undo  Ctrl+Z", command=lambda: self.focus_get() and self.focus_get().event_generate("<<Undo>>"))
        em.add_command(label="Redo  Ctrl+Y", command=lambda: self.focus_get() and self.focus_get().event_generate("<<Redo>>"))
        em.add_separator()
        em.add_command(label="Cut   Ctrl+X",  command=lambda: self.focus_get() and self.focus_get().event_generate("<<Cut>>"))
        em.add_command(label="Copy  Ctrl+C",  command=lambda: self.focus_get() and self.focus_get().event_generate("<<Copy>>"))
        em.add_command(label="Paste Ctrl+V",  command=lambda: self.focus_get() and self.focus_get().event_generate("<<Paste>>"))
        em.add_separator()
        em.add_command(label="Select All Ctrl+A", command=self._select_all)
        em.add_separator()
        em.add_command(label="Find...    Ctrl+F", command=lambda: self._show_find_bar(False))
        em.add_command(label="Replace... Ctrl+H", command=lambda: self._show_find_bar(True))
        mb.add_cascade(label="Edit", menu=em)

        om = tk.Menu(mb, **kw)
        om.add_checkbutton(label="Dark Mode",      command=self.cmd_toggle_theme)
        om.add_checkbutton(label="Always on Top",  variable=self._always_on_top,
                           command=lambda: self.attributes("-topmost", self._always_on_top.get()))
        mb.add_cascade(label="Options", menu=om)

        hm = tk.Menu(mb, **kw)
        hm.add_command(label="About Jotter...", command=self._show_about)
        mb.add_cascade(label="Help", menu=hm)

    def _txt_ev(self, seq, fn):
        if self._active and self._active.text:
            self._active.text.bind(seq, fn)

    def _select_all(self, event=None):
        if self._active and self._active.text:
            t = self._active.text
            t.tag_add("sel", "1.0", "end")
            t.mark_set("insert", "1.0")
            t.see("insert")

    # ------------------------------------------------------------------
    # Tab bar
    # ------------------------------------------------------------------
    def _build_tab_bar(self):
        T = self._T
        outer = tk.Frame(self, bg=T["tab_bar"], height=41)
        outer.pack(side="top", fill="x")
        outer.pack_propagate(False)
        self._bar_outer = outer

        canvas = tk.Canvas(outer, bg=T["tab_bar"], highlightthickness=0, bd=0)
        canvas.pack(side="left", fill="both", expand=True)
        self._bar_canvas = canvas

        inner = tk.Frame(canvas, bg=T["tab_bar"])
        canvas.create_window((0, 0), window=inner, anchor="nw")
        self._bar_inner = inner

        plus = tk.Label(outer, text=" + ", bg=T["tab_bar"],
                        fg=T["close_fg"], font=("Segoe UI", 14), cursor="hand2")
        plus.pack(side="right", padx=4)
        plus.bind("<Button-1>", lambda _e: self.cmd_new_tab())
        self._plus = plus

        canvas.bind("<Configure>",
                    lambda e: canvas.configure(
                        scrollregion=canvas.bbox("all")))

    def _rebuild_tab_buttons(self):
        T = self._T
        for w in self._bar_inner.winfo_children():
            w.destroy()

        seen_groups = []
        i = 0
        while i < len(self._tabs):
            tab = self._tabs[i]
            if tab.group is None:
                self._make_tab_btn(tab, self._bar_inner)
                i += 1
            else:
                grp = tab.group
                if grp not in seen_groups:
                    seen_groups.append(grp)
                    grp_tabs = [t for t in self._tabs if t.group is grp]
                    self._make_group_container(grp, grp_tabs, self._bar_inner)
                i += 1

        self._restore_active_highlight()
        self.after(1, self._update_bar_height)

    def _update_bar_height(self):
        self._bar_inner.update_idletasks()
        h = max(self._bar_inner.winfo_reqheight(), 41)
        self._bar_outer.configure(height=h)
        self._bar_canvas.configure(height=h)
        self._bar_canvas.configure(scrollregion=self._bar_canvas.bbox("all"))

    def _make_group_container(self, group, tabs, parent):
        T = self._T

        container = tk.Frame(parent, bg=T["tab_bar"])
        container.pack(side="left", padx=(3, 0))

        strip = tk.Frame(container, height=6, bg=group.color, cursor="hand2")
        strip.pack(side="top", fill="x")

        header = tk.Frame(container, bg=T["tab_bar"])
        header.pack(side="top", fill="x")

        sym = "<" if group.collapsed else "v"
        collapse_btn = tk.Label(
            header, text=sym, bg=T["tab_bar"],
            fg=group.color, font=("Segoe UI", 9), cursor="hand2", padx=3)
        collapse_btn.pack(side="left")

        label_lbl = tk.Label(
            header, text=group.label, bg=T["tab_bar"],
            fg=group.color, font=("Segoe UI", 8, "bold"), cursor="hand2", padx=2)
        label_lbl.pack(side="left")

        inner = tk.Frame(container, bg=T["tab_bar"])
        if not group.collapsed:
            inner.pack(side="top")

        group.container    = container
        group.strip        = strip
        group.inner        = inner
        group.collapse_btn = collapse_btn
        group.label_lbl    = label_lbl

        for w in (strip, header, collapse_btn, label_lbl):
            w.bind("<ButtonPress-1>",   lambda e, g=group: self._on_group_press(e, g))
            w.bind("<B1-Motion>",       lambda e, g=group: self._on_group_drag(e, g))
            w.bind("<ButtonRelease-1>", lambda e, g=group: self._on_group_release(e, g))
            w.bind("<Button-3>",        lambda e, g=group: self._group_context(e, g))
        label_lbl.bind("<Double-Button-1>",
                       lambda _e, g=group: self._rename_group(g))

        if group.collapsed:
            n = len(tabs)
            count_lbl = tk.Label(
                container,
                text="  %d tab%s  " % (n, "s" if n != 1 else ""),
                bg=T["tab_bar"], fg=group.color,
                font=("Segoe UI", 9, "italic"), cursor="hand2")
            count_lbl.pack(side="top", pady=(0, 3))
            count_lbl.bind("<Button-1>", lambda _e, g=group: self._toggle_collapse(g))
            count_lbl.bind("<Button-3>", lambda  e, g=group: self._group_context(e, g))

        for tab in tabs:
            self._make_tab_btn(tab, inner)

    def _make_tab_btn(self, tab, parent):
        T = self._T
        dot_color = tab.color or T["default_dot"]

        frm = tk.Frame(parent, bg=T["tab_idle"], cursor="hand2")
        frm.pack(side="left", padx=(1, 0), pady=(3, 0))

        dc = tk.Canvas(frm, width=10, height=10,
                       bg=T["tab_idle"], highlightthickness=0, bd=0)
        dc.pack(side="left", padx=(9, 2), pady=14)
        ov = dc.create_oval(1, 1, 9, 9, fill=dot_color, outline="")

        lbl = tk.Label(frm, text=tab.title, bg=T["tab_idle"],
                       fg=T["text_fg"], font=("Segoe UI", 10), padx=2)
        lbl.pack(side="left")

        cls = tk.Label(frm, text="x", bg=T["tab_idle"],
                       fg=T["close_fg"], font=("Segoe UI", 11, "bold"), padx=7)
        cls.pack(side="left")

        tab.btn_frame  = frm
        tab.dot_canvas = dc
        tab.oval_id    = ov
        tab.title_lbl  = lbl
        tab.close_lbl  = cls

        for w in (frm, lbl):
            w.bind("<ButtonPress-1>",   lambda e, t=tab: self._on_press(e, t))
            w.bind("<B1-Motion>",       lambda e, t=tab: self._on_drag(e, t))
            w.bind("<ButtonRelease-1>", lambda e, t=tab: self._on_release(e, t))
            w.bind("<Button-3>",        lambda e, t=tab: self._tab_context(e, t))
            w.bind("<Enter>",           lambda e, t=tab: self._tab_hover(t, True))
            w.bind("<Leave>",           lambda e, t=tab: self._tab_hover(t, False))

        dc.bind("<ButtonPress-1>",   lambda e, t=tab: self._on_press(e, t, dot=True))
        dc.bind("<B1-Motion>",       lambda e, t=tab: self._on_drag(e, t))
        dc.bind("<ButtonRelease-1>", lambda e, t=tab: self._on_release(e, t))

        cls.bind("<ButtonPress-1>",   lambda e, t=tab: self.cmd_close_tab(t))
        cls.bind("<Enter>",  lambda e, w=cls: w.configure(fg="#ff4444"))
        cls.bind("<Leave>",  lambda e, w=cls, T2=T: w.configure(fg=T2["close_fg"]))

    def _restore_active_highlight(self):
        T = self._T
        for tab in self._tabs:
            if not tab.btn_frame:
                continue
            bg = T["tab_active"] if tab is self._active else T["tab_idle"]
            tab.btn_frame.configure(bg=bg)
            if tab.dot_canvas:
                tab.dot_canvas.configure(bg=bg)
            if tab.title_lbl:
                tab.title_lbl.configure(bg=bg)
            if tab.close_lbl:
                tab.close_lbl.configure(bg=bg)

    def _tab_hover(self, tab, entering):
        if tab is self._active:
            return
        T   = self._T
        bg  = T["tab_hover"] if entering else T["tab_idle"]
        if tab.btn_frame:
            tab.btn_frame.configure(bg=bg)
        if tab.dot_canvas:
            tab.dot_canvas.configure(bg=bg)
        if tab.title_lbl:
            tab.title_lbl.configure(bg=bg)
        if tab.close_lbl:
            tab.close_lbl.configure(bg=bg)

    def _activate(self, tab):
        if self._active and self._active is not tab:
            if self._active.text_frame:
                self._active.text_frame.pack_forget()
        self._active = tab
        if tab.text_frame:
            tab.text_frame.pack(fill="both", expand=True)
        if tab.text:
            tab.text.focus_set()
        self._restore_active_highlight()
        self._refresh_status()

    # ------------------------------------------------------------------
    # Ghost (floating preview during tab drag)
    # ------------------------------------------------------------------
    def _create_ghost(self, tab):
        T = self._T
        ghost = tk.Toplevel(self)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)
        try:
            ghost.attributes("-alpha", 0.75)
        except Exception:
            pass
        dot_color = tab.color or T["default_dot"]
        frm = tk.Frame(ghost, bg=T["tab_active"],
                       highlightthickness=1, highlightbackground=T["border"])
        frm.pack()
        dc = tk.Canvas(frm, width=10, height=10, bg=T["tab_active"],
                       highlightthickness=0, bd=0)
        dc.pack(side="left", padx=(9, 2), pady=8)
        dc.create_oval(1, 1, 9, 9, fill=dot_color, outline="")
        tk.Label(frm, text=tab.title, bg=T["tab_active"],
                 fg=T["text_fg"], font=("Segoe UI", 10), padx=2).pack(side="left")
        tk.Label(frm, text="x", bg=T["tab_active"],
                 fg=T["close_fg"], font=("Segoe UI", 11, "bold"), padx=7).pack(side="left")
        return ghost

    def _move_ghost(self, x, y):
        if self._ghost:
            self._ghost.geometry("+%d+%d" % (x + 12, y - 10))

    def _destroy_ghost(self):
        if self._ghost:
            try:
                self._ghost.destroy()
            except Exception:
                pass
            self._ghost = None

    # ------------------------------------------------------------------
    # Tab drag-and-drop
    # ------------------------------------------------------------------
    def _on_press(self, event, tab, dot=False):
        self._drag_tab     = tab
        self._drag_start_x = event.x_root
        self._drag_moved   = False
        self._press_on_dot = dot
        self._activate(tab)

    def _on_drag(self, event, tab):
        if abs(event.x_root - self._drag_start_x) > 6:
            self._drag_moved = True
        if not self._drag_moved:
            return
        if self._ghost is None:
            self._ghost = self._create_ghost(tab)
        self._move_ghost(event.x_root, event.y_root)
        self._update_drop_indicator(event.x_root)

    def _on_release(self, event, tab):
        self._destroy_ghost()
        if not self._drag_moved:
            if self._press_on_dot:
                self._show_tab_color_picker(tab)
            self._drag_tab   = None
            self._drag_moved = False
            self._clear_drop_indicator()
            return

        result = self._find_drop_target(event.x_root, tab)
        self._clear_drop_indicator()

        if result:
            kind, payload = result
            if kind == "reorder":
                self._do_reorder(tab, payload)
            elif kind == "group":
                self._do_group(tab, payload)
            elif kind == "make_group":
                new_grp = TabGroup()
                tab.group = new_grp
                payload.group = new_grp
                self._rebuild_tab_buttons()
        else:
            if tab.group is not None:
                self._do_ungroup_tab(tab)

        self._drag_tab   = None
        self._drag_moved = False

    def _find_drop_target(self, x_root, drag_tab):
        """
        Returns ("reorder", idx), ("group", TabGroup),
                ("make_group", Tab), or None.
        """
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
                        zones.append((bx, bx + bw, "tab", tab, li, li + 1))
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
                            idxs = [i for i, t in enumerate(self._tabs)
                                    if t.group is grp]
                            zones.append((bx, bx + bw, "group", grp,
                                          min(idxs), max(idxs) + 1))
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
        self._clear_drop_indicator()
        canvas = self._bar_canvas
        T = self._T

        zones = []
        seen_groups = set()
        for tab in self._tabs:
            if tab is self._drag_tab:
                continue
            if tab.group is None:
                if tab.btn_frame:
                    try:
                        bx = tab.btn_frame.winfo_rootx()
                        bw = tab.btn_frame.winfo_width()
                        zones.append((bx, bx + bw, "tab", tab))
                    except Exception:
                        pass
            else:
                grp = tab.group
                if grp not in seen_groups:
                    seen_groups.add(grp)
                    con = grp.container
                    if con:
                        try:
                            bx = con.winfo_rootx()
                            bw = con.winfo_width()
                            zones.append((bx, bx + bw, "group", grp))
                        except Exception:
                            pass

        for bx, bx_end, kind, payload in zones:
            if bx <= x_root <= bx_end:
                rel = (x_root - bx) / max(bx_end - bx, 1)
                if 0.2 <= rel <= 0.8:
                    try:
                        rx  = bx - canvas.winfo_rootx()
                        rw  = bx_end - bx
                        if kind == "group":
                            col = payload.color
                            rh  = payload.container.winfo_height()
                        else:
                            col = T["drop_line"]
                            rh  = 38
                        self._drop_item = canvas.create_rectangle(
                            rx, 2, rx + rw, rh + 2,
                            outline=col, width=3, fill="")
                    except Exception:
                        pass
                else:
                    cx = bx if rel < 0.5 else bx_end
                    try:
                        lx = cx - canvas.winfo_rootx()
                        self._drop_item = canvas.create_line(
                            lx, 2, lx, 38, fill=T["drop_line"], width=3)
                    except Exception:
                        pass
                return

        if zones:
            try:
                lx = zones[-1][1] - canvas.winfo_rootx()
                self._drop_item = canvas.create_line(
                    lx, 2, lx, 38, fill=T["drop_line"], width=3)
            except Exception:
                pass

    def _clear_drop_indicator(self):
        if self._drop_item is not None:
            try:
                self._bar_canvas.delete(self._drop_item)
            except Exception:
                pass
            self._drop_item = None

    def _do_reorder(self, tab, new_idx):
        if tab.group is not None:
            tmp   = [t for t in self._tabs if t is not tab]
            left  = tmp[new_idx - 1] if 0 < new_idx <= len(tmp) else None
            right = tmp[new_idx]     if new_idx < len(tmp)       else None
            same  = ((left  is not None and left.group  is tab.group) or
                     (right is not None and right.group is tab.group))
            if not same:
                tab.group = None
        self._tabs.remove(tab)
        idx = min(new_idx, len(self._tabs))
        self._tabs.insert(idx, tab)
        self._rebuild_tab_buttons()

    def _do_group(self, tab, target_group):
        tab.group = target_group
        self._rebuild_tab_buttons()

    def _do_ungroup_tab(self, tab, rebuild=True):
        grp = tab.group
        if grp is None:
            return
        tab.group = None
        remaining = [t for t in self._tabs if t.group is grp]
        if len(remaining) == 1:
            remaining[0].group = None
        if rebuild:
            self._rebuild_tab_buttons()

    # ------------------------------------------------------------------
    # Group drag-and-drop
    # ------------------------------------------------------------------
    def _on_group_press(self, event, group):
        self._drag_group       = group
        self._drag_grp_start_x = event.x_root
        self._drag_grp_moved   = False

    def _on_group_drag(self, event, group):
        if abs(event.x_root - self._drag_grp_start_x) > 8:
            self._drag_grp_moved = True
        if not self._drag_grp_moved:
            return
        if self._ghost is None:
            self._ghost = self._create_group_ghost(group)
        self._ghost.geometry("+%d+%d" % (event.x_root + 12, event.y_root - 10))
        self._update_group_drop_indicator(event.x_root)

    def _on_group_release(self, event, group):
        self._destroy_ghost()
        if not self._drag_grp_moved:
            self._toggle_collapse(group)
            self._clear_drop_indicator()
            self._drag_group = None
            return

        result = self._find_group_drop_target(event.x_root)
        self._clear_drop_indicator()

        if result:
            action, payload = result
            if action == "reorder":
                self._do_group_reorder(group, payload)
            elif action == "merge":
                self._do_merge_groups(group, payload)

        self._drag_group     = None
        self._drag_grp_moved = False

    def _create_group_ghost(self, group):
        T = self._T
        ghost = tk.Toplevel(self)
        ghost.overrideredirect(True)
        ghost.attributes("-topmost", True)
        try:
            ghost.attributes("-alpha", 0.80)
        except Exception:
            pass
        outer = tk.Frame(ghost, bg=group.color, pady=3)
        outer.pack()
        tk.Label(outer, text="  %s  " % group.label,
                 bg=group.color, fg="#ffffff",
                 font=("Segoe UI", 9, "bold")).pack()
        return ghost

    def _find_group_drop_target(self, x_root):
        drag   = self._drag_group
        canvas = self._bar_canvas

        items = []
        seen  = set()
        for tab in self._tabs:
            if tab.group is None:
                btn = tab.btn_frame
                if not btn:
                    continue
                try:
                    bx = btn.winfo_rootx()
                    bw = btn.winfo_width()
                    items.append((bx, bx + bw, "tab", tab))
                except Exception:
                    pass
            else:
                grp = tab.group
                if grp in seen or grp is drag:
                    continue
                seen.add(grp)
                con = grp.container
                if not con:
                    continue
                try:
                    bx = con.winfo_rootx()
                    bw = con.winfo_width()
                    items.append((bx, bx + bw, "group", grp))
                except Exception:
                    pass

        for bx, bx_end, kind, payload in items:
            if bx <= x_root <= bx_end:
                rel = (x_root - bx) / max(bx_end - bx, 1)
                if kind == "group" and 0.2 <= rel <= 0.8:
                    return ("merge", payload)
                if rel < 0.5:
                    return ("reorder", bx)
                else:
                    return ("reorder", bx_end)

        if items:
            return ("reorder", items[-1][1] + 1)
        return None

    def _update_group_drop_indicator(self, x_root):
        self._clear_drop_indicator()
        result = self._find_group_drop_target(x_root)
        if not result:
            return
        action, payload = result
        canvas = self._bar_canvas
        T = self._T

        if action == "reorder":
            try:
                lx = payload - canvas.winfo_rootx()
                self._drop_item = canvas.create_line(
                    lx, 2, lx, 38, fill=T["drop_line"], width=3)
            except Exception:
                pass
        elif action == "merge":
            grp = payload
            con = grp.container
            if con:
                try:
                    bx = con.winfo_rootx() - canvas.winfo_rootx()
                    bw = con.winfo_width()
                    bh = con.winfo_height()
                    self._drop_item = canvas.create_rectangle(
                        bx, 2, bx + bw, bh + 2,
                        outline=grp.color, width=3, fill="")
                except Exception:
                    pass

    def _do_group_reorder(self, group, screen_x_boundary):
        best_idx  = len(self._tabs)
        best_dist = float("inf")
        for i, tab in enumerate(self._tabs):
            if tab.group is group:
                continue
            btn = tab.btn_frame
            if not btn:
                continue
            try:
                bx = btn.winfo_rootx()
                for px, ii in ((bx, i), (bx + btn.winfo_width(), i + 1)):
                    d = abs(px - screen_x_boundary)
                    if d < best_dist:
                        best_dist = d
                        best_idx  = ii
            except Exception:
                pass

        seen = set()
        for tab in self._tabs:
            if tab.group is None or tab.group is group or tab.group in seen:
                continue
            seen.add(tab.group)
            con = tab.group.container
            if not con:
                continue
            try:
                bx  = con.winfo_rootx()
                bw  = con.winfo_width()
                fi  = next(i for i, t in enumerate(self._tabs) if t.group is tab.group)
                li  = max(i for i, t in enumerate(self._tabs) if t.group is tab.group)
                for px, ii in ((bx, fi), (bx + bw, li + 1)):
                    d = abs(px - screen_x_boundary)
                    if d < best_dist:
                        best_dist = d
                        best_idx  = ii
            except Exception:
                pass

        grp_tabs = [t for t in self._tabs if t.group is group]
        for t in grp_tabs:
            self._tabs.remove(t)
        ins = min(best_idx, len(self._tabs))
        for j, t in enumerate(grp_tabs):
            self._tabs.insert(ins + j, t)
        self._rebuild_tab_buttons()

    def _do_merge_groups(self, src_group, tgt_group):
        for tab in self._tabs:
            if tab.group is src_group:
                tab.group = tgt_group
        self._rebuild_tab_buttons()

    # ------------------------------------------------------------------
    # Group actions
    # ------------------------------------------------------------------
    def _toggle_collapse(self, group):
        group.collapsed = not group.collapsed
        self._rebuild_tab_buttons()

    def _group_context(self, event, group):
        T  = self._T
        kw = dict(tearoff=0, bg=T["menu_bg"], fg=T["menu_fg"],
                  activebackground=T["menu_sel"], activeforeground=T["menu_fg"])
        m = tk.Menu(self, **kw)
        lbl = "Expand" if group.collapsed else "Collapse"
        m.add_command(label=lbl,           command=lambda: self._toggle_collapse(group))
        m.add_command(label="Rename...",   command=lambda: self._rename_group(group))
        m.add_command(label="Change Color...", command=lambda: self._pick_group_color(group))
        m.add_separator()
        m.add_command(label="Ungroup All", command=lambda: self._ungroup(group))
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def _rename_group(self, group):
        name = simpledialog.askstring(
            "Rename Group", "Enter group name:",
            initialvalue=group.label, parent=self)
        if name and name.strip():
            group.label = name.strip()
            if group.label_lbl:
                group.label_lbl.config(text=group.label)

    def _pick_group_color(self, group):
        result = colorchooser.askcolor(color=group.color, parent=self,
                                       title="Group Color")
        if result and result[1]:
            group.color = result[1]
            self._rebuild_tab_buttons()

    def _ungroup(self, group):
        for tab in self._tabs:
            if tab.group is group:
                tab.group = None
        self._rebuild_tab_buttons()

    # ------------------------------------------------------------------
    # Tab context menu
    # ------------------------------------------------------------------
    def _tab_context(self, event, tab):
        T  = self._T
        kw = dict(tearoff=0, bg=T["menu_bg"], fg=T["menu_fg"],
                  activebackground=T["menu_sel"], activeforeground=T["menu_fg"])
        m = tk.Menu(self, **kw)
        m.add_command(label="Rename...",      command=lambda: self._rename_tab(tab))
        m.add_command(label="Change Color...",command=lambda: self._show_tab_color_picker(tab))
        m.add_separator()
        m.add_command(label="Close",          command=lambda: self.cmd_close_tab(tab))
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def _rename_tab(self, tab):
        name = simpledialog.askstring(
            "Rename Tab", "Enter tab name:",
            initialvalue=tab.title.rstrip(" *"), parent=self)
        if name and name.strip():
            tab.title = name.strip()
            if tab.title_lbl:
                tab.title_lbl.config(text=tab.title)

    def _show_tab_color_picker(self, tab):
        T      = self._T
        colors = _ACCENT_CYCLE
        win    = tk.Toplevel(self)
        win.title("Tab Color")
        win.configure(bg=T["tab_bar"])
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="Choose a color:", bg=T["tab_bar"],
                 fg=T["text_fg"], font=("Segoe UI", 10), pady=8).pack()

        row = tk.Frame(win, bg=T["tab_bar"])
        row.pack(padx=12, pady=(0, 8))

        def pick(c):
            tab.color = c
            if tab.dot_canvas and tab.oval_id:
                tab.dot_canvas.itemconfig(tab.oval_id, fill=c)
            win.destroy()

        for c in colors:
            b = tk.Canvas(row, width=24, height=24, bg=T["tab_bar"],
                          highlightthickness=0, cursor="hand2")
            b.pack(side="left", padx=3)
            b.create_oval(3, 3, 21, 21, fill=c, outline="")
            b.bind("<Button-1>", lambda e, col=c: pick(col))

        def custom():
            r = colorchooser.askcolor(color=tab.color or T["default_dot"],
                                      parent=win, title="Custom Color")
            if r and r[1]:
                pick(r[1])

        tk.Button(win, text="Custom...", command=custom,
                  bg=T["tab_idle"], fg=T["text_fg"],
                  relief="flat", pady=4).pack(pady=(0, 10))

    # ------------------------------------------------------------------
    # About dialog
    # ------------------------------------------------------------------
    def _show_about(self):
        T   = self._T
        win = tk.Toplevel(self)
        win.title("About Jotter")
        win.configure(bg=T["bg"])
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        # Header
        hdr = tk.Frame(win, bg="#007acc", pady=18)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Jotter", bg="#007acc", fg="#ffffff",
                 font=("Segoe UI", 22, "bold")).pack()
        tk.Label(hdr, text="Version 1.0", bg="#007acc", fg="#cce4f7",
                 font=("Segoe UI", 10)).pack()

        # Body
        body = tk.Frame(win, bg=T["bg"], padx=28, pady=18)
        body.pack(fill="both")

        # Description
        tk.Label(body,
                 text="Jotter is a lightweight, dark-mode text editor built for speed and"
                      " organisation. Open as many tabs as you like, drag them to reorder,"
                      " and group related tabs together visually.",
                 bg=T["bg"], fg=T["text_fg"], font=("Segoe UI", 10),
                 wraplength=460, justify="left").pack(anchor="w", pady=(0, 12))

        # Controls reference
        tk.Label(body, text="Controls", bg=T["bg"], fg=T["text_fg"],
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")

        controls = (
            ("Drag a tab",              "Reorder it in the bar"),
            ("Drag onto another tab",   "Group the two tabs together"),
            ("Drag out of a group",     "Ungroup that tab"),
            ("Drag one group onto another", "Merge the groups"),
            ("Click group strip/label", "Collapse / expand the group"),
            ("Double-click group label","Rename the group"),
            ("Right-click a tab",       "Rename, recolour, or close it"),
            ("Right-click group strip", "Recolour, rename, or ungroup"),
            ("Click the colour dot",    "Pick a tab accent colour"),
            ("Ctrl+N / Ctrl+W",         "New tab / close tab"),
            ("Ctrl+O / Ctrl+S",         "Open file / save file"),
        )
        grid = tk.Frame(body, bg=T["bg"])
        grid.pack(anchor="w", pady=(4, 12))
        for row, (action, result) in enumerate(controls):
            tk.Label(grid, text=action, bg=T["bg"], fg="#007acc",
                     font=("Segoe UI", 9, "bold"), anchor="w", width=30
                     ).grid(row=row, column=0, sticky="w")
            tk.Label(grid, text=result, bg=T["bg"], fg=T["text_fg"],
                     font=("Segoe UI", 9), anchor="w"
                     ).grid(row=row, column=1, sticky="w", padx=(8, 0))

        tk.Frame(body, bg=T["border"], height=1).pack(fill="x", pady=(0, 14))

        # Author
        tk.Label(body, text="Chris Lutz", bg=T["bg"], fg=T["text_fg"],
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(body, text="chrismlutz@gmail.com", bg=T["bg"], fg="#007acc",
                 font=("Segoe UI", 10), cursor="hand2").pack(anchor="w")
        gh = tk.Label(body, text="github.com/chrismlutz-gif/Jotter",
                      bg=T["bg"], fg="#007acc", font=("Segoe UI", 10),
                      cursor="hand2")
        gh.pack(anchor="w")
        gh.bind("<Button-1>", lambda _e: __import__("webbrowser").open(
            "https://github.com/chrismlutz-gif/Jotter"))

        tk.Frame(body, bg=T["border"], height=1).pack(fill="x", pady=14)

        license_text = (
            "MIT License\n\n"
            "Copyright (c) 2026 Chris Lutz\n\n"
            "Permission is hereby granted, free of charge, to any person obtaining\n"
            "a copy of this software and associated documentation files (the\n"
            "\"Software\"), to deal in the Software without restriction, including\n"
            "without limitation the rights to use, copy, modify, merge, publish,\n"
            "distribute, sublicense, and/or sell copies of the Software, and to\n"
            "permit persons to whom the Software is furnished to do so, subject to\n"
            "the following conditions:\n\n"
            "The above copyright notice and this permission notice shall be included\n"
            "in all copies or substantial portions of the Software.\n\n"
            "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND,\n"
            "EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF\n"
            "MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.\n"
            "IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY\n"
            "CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,\n"
            "TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE\n"
            "SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."
        )
        txt = tk.Text(body, bg=T["tab_bar"], fg=T["text_fg"], relief="flat",
                      font=("Segoe UI", 9), width=58, height=16,
                      wrap="word", bd=6, state="normal", cursor="arrow")
        txt.insert("1.0", license_text)
        txt.configure(state="disabled")
        txt.pack(fill="x")

        tk.Button(win, text="Close", command=win.destroy,
                  bg="#007acc", fg="#ffffff", relief="flat",
                  font=("Segoe UI", 10), padx=24, pady=6,
                  activebackground="#005f9e", activeforeground="#ffffff",
                  cursor="hand2").pack(pady=14)

    # ------------------------------------------------------------------
    # File commands
    # ------------------------------------------------------------------
    def _refresh_tab_label(self, tab):
        title = tab.title.rstrip(" *")
        if tab.modified:
            title += " *"
        tab.title = title
        if tab.title_lbl:
            tab.title_lbl.config(text=title)

    def cmd_open(self, event=None):
        path = filedialog.askopenfilename(
            parent=self,
            title="Open file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Open failed", str(e), parent=self)
            return
        import os as _os
        tab = self.cmd_new_tab(title=_os.path.basename(path))
        tab.path     = path
        tab.modified = False
        if tab.text:
            tab.text.delete("1.0", "end")
            tab.text.insert("1.0", content)
            tab.text.edit_reset()
        self._refresh_tab_label(tab)

    def cmd_save(self, tab=None, event=None):
        if tab is None:
            tab = self._active
        if tab is None:
            return
        if tab.path is None:
            self.cmd_save_as(tab)
            return
        try:
            with open(tab.path, "w", encoding="utf-8") as f:
                f.write(tab.text.get("1.0", "end-1c"))
            tab.modified = False
            self._refresh_tab_label(tab)
        except Exception as e:
            messagebox.showerror("Save failed", str(e), parent=self)

    def cmd_save_as(self, tab=None, event=None):
        if tab is None:
            tab = self._active
        if tab is None:
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save As",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        import os as _os
        tab.path  = path
        tab.title = _os.path.basename(path)
        self.cmd_save(tab)

    def cmd_toggle_theme(self):
        self._dark = not self._dark
        self._T    = DARK if self._dark else LIGHT
        # rebuild the whole UI by destroying children and re-running builds
        for w in self.winfo_children():
            w.destroy()
        self.configure(bg=self._T["bg"])
        self._find_frame  = None
        self._active      = None
        tabs_backup = [(t.title.rstrip(" *"), t.path, t.color,
                        t.text.get("1.0", "end-1c") if t.text else "",
                        t.group) for t in self._tabs]
        self._tabs = []
        self._build_menu()
        self._build_tab_bar()
        self._build_body()
        self._build_statusbar()
        self._build_findbar()
        for title, path, color, content, grp in tabs_backup:
            tab = self.cmd_new_tab(title=title)
            tab.path  = path
            tab.color = color
            if tab.text:
                tab.text.insert("1.0", content)
                tab.text.edit_reset()
                tab.modified = False
            if grp is not None:
                tab.group = grp
        self._rebuild_tab_buttons()
        if self._tabs:
            self._activate(self._tabs[0])

    # ------------------------------------------------------------------
    # Find / Replace bar
    # ------------------------------------------------------------------
    def _build_findbar(self):
        T   = self._T
        bar = tk.Frame(self, bg=T["tab_bar"], bd=0)
        self._find_frame = bar
        # not packed yet — shown on demand

        # Close button
        close = tk.Label(bar, text="  ×  ", bg=T["tab_bar"], fg=T["close_fg"],
                         font=("Segoe UI", 13), cursor="hand2")
        close.pack(side="right", padx=4)
        close.bind("<Button-1>", lambda _e: self._hide_find_bar())

        # Find row
        find_row = tk.Frame(bar, bg=T["tab_bar"])
        find_row.pack(side="top", fill="x", padx=8, pady=(4, 2))
        tk.Label(find_row, text="Find:", bg=T["tab_bar"], fg=T["text_fg"],
                 font=("Segoe UI", 10), width=7, anchor="e").pack(side="left")
        self._find_var = tk.StringVar()
        fe = tk.Entry(find_row, textvariable=self._find_var, width=30,
                      bg=T["text_bg"], fg=T["text_fg"],
                      insertbackground=T["text_fg"],
                      relief="flat", bd=4, font=("Segoe UI", 10))
        fe.pack(side="left", padx=(4, 0))
        self._find_entry = fe
        self._find_count_lbl = tk.Label(find_row, text="", bg=T["tab_bar"],
                                        fg=T["ln_fg"], font=("Segoe UI", 9), padx=6)
        self._find_count_lbl.pack(side="left")
        tk.Button(find_row, text="▲", command=lambda: self._find_step(-1),
                  bg=T["tab_idle"], fg=T["text_fg"], relief="flat",
                  font=("Segoe UI", 9), padx=6, pady=1,
                  cursor="hand2").pack(side="left", padx=2)
        tk.Button(find_row, text="▼", command=lambda: self._find_step(1),
                  bg=T["tab_idle"], fg=T["text_fg"], relief="flat",
                  font=("Segoe UI", 9), padx=6, pady=1,
                  cursor="hand2").pack(side="left", padx=2)
        self._find_var.trace_add("write", lambda *_: self._run_find())

        # Replace row (hidden until replace mode)
        rep_row = tk.Frame(bar, bg=T["tab_bar"])
        self._replace_row = rep_row
        tk.Label(rep_row, text="Replace:", bg=T["tab_bar"], fg=T["text_fg"],
                 font=("Segoe UI", 10), width=7, anchor="e").pack(side="left")
        self._replace_var = tk.StringVar()
        tk.Entry(rep_row, textvariable=self._replace_var, width=30,
                 bg=T["text_bg"], fg=T["text_fg"],
                 insertbackground=T["text_fg"],
                 relief="flat", bd=4, font=("Segoe UI", 10)).pack(side="left", padx=(4, 8))
        tk.Button(rep_row, text="Replace", command=self._do_replace,
                  bg=T["tab_idle"], fg=T["text_fg"], relief="flat",
                  font=("Segoe UI", 9), padx=8, pady=1,
                  cursor="hand2").pack(side="left", padx=2)
        tk.Button(rep_row, text="Replace All", command=self._do_replace_all,
                  bg=T["tab_idle"], fg=T["text_fg"], relief="flat",
                  font=("Segoe UI", 9), padx=8, pady=1,
                  cursor="hand2").pack(side="left", padx=2)
        self._replace_lbl = tk.Label(rep_row, text="", bg=T["tab_bar"],
                                     fg=T["ln_fg"], font=("Segoe UI", 9), padx=6)
        self._replace_lbl.pack(side="left")

        # internal state
        self._find_matches = []   # list of (start, end) index strings
        self._find_idx     = -1

        fe.bind("<Return>",          lambda _e: self._find_step(1))
        fe.bind("<Shift-Return>",    lambda _e: self._find_step(-1))
        fe.bind("<Escape>",          lambda _e: self._hide_find_bar())

    def _show_find_bar(self, replace=False):
        self._find_frame.pack(side="bottom", fill="x",
                              before=self._status_left.master)
        if replace:
            self._replace_row.pack(side="top", fill="x", padx=8, pady=(0, 4))
        else:
            self._replace_row.pack_forget()
        self._find_entry.focus_set()
        self._find_entry.select_range(0, "end")
        self._run_find()

    def _hide_find_bar(self):
        self._find_frame.pack_forget()
        self._clear_find_highlights()
        self._find_matches = []
        self._find_idx     = -1
        self._find_count_lbl.config(text="")
        if self._active and self._active.text:
            self._active.text.focus_set()

    def _run_find(self):
        self._clear_find_highlights()
        self._find_matches = []
        self._find_idx     = -1
        if not self._active or not self._active.text:
            return
        pattern = self._find_var.get()
        if not pattern:
            self._find_count_lbl.config(text="")
            return
        txt = self._active.text
        txt.tag_configure("find_match",    background="#515c6a", foreground="#ffffff")
        txt.tag_configure("find_current",  background="#f6b73c", foreground="#000000")
        pos = "1.0"
        while True:
            idx = txt.search(pattern, pos, stopindex="end", nocase=True)
            if not idx:
                break
            end = "%s+%dc" % (idx, len(pattern))
            txt.tag_add("find_match", idx, end)
            self._find_matches.append((idx, end))
            pos = end
        n = len(self._find_matches)
        if n:
            self._find_count_lbl.config(text="%d match%s" % (n, "es" if n != 1 else ""))
            self._find_step(1)
        else:
            self._find_count_lbl.config(text="No matches")

    def _find_step(self, direction):
        if not self._find_matches:
            return
        n = len(self._find_matches)
        self._find_idx = (self._find_idx + direction) % n
        start, end = self._find_matches[self._find_idx]
        txt = self._active.text
        txt.tag_remove("find_current", "1.0", "end")
        txt.tag_add("find_current", start, end)
        txt.see(start)
        self._find_count_lbl.config(
            text="%d / %d" % (self._find_idx + 1, n))

    def _clear_find_highlights(self):
        if self._active and self._active.text:
            self._active.text.tag_remove("find_match",   "1.0", "end")
            self._active.text.tag_remove("find_current", "1.0", "end")

    def _do_replace(self):
        if not self._find_matches or self._find_idx < 0:
            return
        txt         = self._active.text
        start, end  = self._find_matches[self._find_idx]
        replacement = self._replace_var.get()
        txt.delete(start, end)
        txt.insert(start, replacement)
        self._replace_lbl.config(text="Replaced.")
        self.after(1500, lambda: self._replace_lbl.config(text=""))
        self._run_find()

    def _do_replace_all(self):
        if not self._active or not self._active.text:
            return
        pattern     = self._find_var.get()
        replacement = self._replace_var.get()
        if not pattern:
            return
        txt   = self._active.text
        count = 0
        pos   = "1.0"
        while True:
            idx = txt.search(pattern, pos, stopindex="end", nocase=True)
            if not idx:
                break
            end = "%s+%dc" % (idx, len(pattern))
            txt.delete(idx, end)
            txt.insert(idx, replacement)
            pos = "%s+%dc" % (idx, len(replacement))
            count += 1
        self._replace_lbl.config(text="%d replaced." % count)
        self.after(2000, lambda: self._replace_lbl.config(text=""))
        self._run_find()

    # ------------------------------------------------------------------
    # Body (text area + line numbers)
    # ------------------------------------------------------------------
    def _build_body(self):
        T = self._T
        body = tk.Frame(self, bg=T["bg"])
        body.pack(side="top", fill="both", expand=True)
        self._body = body

    def _make_text_area(self, tab):
        T    = self._T
        frm  = tk.Frame(self._body, bg=T["bg"])
        tab.text_frame = frm

        ln = tk.Text(frm, width=4, bg=T["ln_bg"], fg=T["ln_fg"],
                     font=("Consolas", 11), state="disabled", cursor="arrow",
                     relief="flat", bd=0, wrap="none", takefocus=0,
                     selectbackground=T["ln_bg"])
        ln.pack(side="left", fill="y")
        tab.linenos = ln

        txt = tk.Text(frm, bg=T["text_bg"], fg=T["text_fg"],
                      insertbackground=T["text_fg"],
                      selectbackground=T["text_sel"],
                      font=("Consolas", 11), relief="flat", bd=8,
                      undo=True, wrap="none")
        txt.pack(side="left", fill="both", expand=True)
        tab.text = txt

        sb = tk.Scrollbar(frm, command=txt.yview, bg=T["tab_bar"])
        sb.pack(side="right", fill="y")
        txt.configure(yscrollcommand=sb.set)

        txt.bind("<<Modified>>", lambda e, t=tab: self._on_modified(t))
        txt.bind("<KeyRelease>", lambda e, t=tab: self._update_linenos(t))
        txt.bind("<MouseWheel>", lambda e, t=tab: self.after(1, lambda: self._update_linenos(t)))

    def _on_modified(self, tab):
        if tab.text and tab.text.edit_modified():
            if not tab.modified:
                tab.modified = True
                tab.title    = tab.title.rstrip(" *") + " *"
                if tab.title_lbl:
                    tab.title_lbl.config(text=tab.title)
            tab.text.edit_modified(False)
            self._update_linenos(tab)
            self._refresh_status()

    def _update_linenos(self, tab):
        if not tab.linenos or not tab.text:
            return
        ln  = tab.linenos
        txt = tab.text
        ln.configure(state="normal")
        ln.delete("1.0", "end")
        nlines = int(txt.index("end-1c").split(".")[0])
        ln.insert("1.0", "\n".join(str(i) for i in range(1, nlines + 1)))
        ln.configure(state="disabled")

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------
    def _build_statusbar(self):
        T   = self._T
        bar = tk.Frame(self, bg=T["status_bg"], height=22)
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)

        self._status_left  = tk.Label(bar, text="", bg=T["status_bg"],
                                      fg=T["status_fg"], font=("Segoe UI", 9),
                                      anchor="w", padx=8)
        self._status_left.pack(side="left")

        self._status_right = tk.Label(bar, text="", bg=T["status_bg"],
                                      fg=T["status_fg"], font=("Segoe UI", 9),
                                      anchor="e", padx=8)
        self._status_right.pack(side="right")

    def _refresh_status(self):
        if not self._active or not self._active.text:
            return
        txt  = self._active.text
        body = txt.get("1.0", "end-1c")
        words = len(body.split()) if body.strip() else 0
        chars = len(body)
        try:
            row, col = txt.index("insert").split(".")
        except Exception:
            row, col = "1", "0"
        self._status_left.configure(
            text="Ln %s, Col %s" % (row, int(col) + 1))
        self._status_right.configure(
            text="Words: %d   Chars: %d" % (words, chars))

    # ------------------------------------------------------------------
    # Tab commands
    # ------------------------------------------------------------------
    def cmd_new_tab(self, title="Untitled", content=""):
        tab   = Tab(title=title)
        color = _ACCENT_CYCLE[self._accent_idx % len(_ACCENT_CYCLE)]
        self._accent_idx += 1
        tab.color = color
        self._make_text_area(tab)
        if content:
            tab.text.insert("1.0", content)
            tab.text.edit_modified(False)
        self._tabs.append(tab)
        self._activate(tab)
        self._rebuild_tab_buttons()
        self._update_linenos(tab)
        return tab


    def cmd_close_tab(self, tab=None):
        if tab is None:
            tab = self._active
        if tab is None:
            return
        if tab.modified:
            name = tab.title.rstrip(" *")
            ans  = messagebox.askyesnocancel(
                "Unsaved changes",
                'Save "%s" before closing?' % name,
                parent=self)
            if ans is None:
                return
            if ans:
                self.cmd_save(tab)

        grp = tab.group
        self._tabs.remove(tab)
        if tab.text_frame:
            tab.text_frame.destroy()

        if grp is not None:
            remaining = [t for t in self._tabs if t.group is grp]
            if len(remaining) == 1:
                remaining[0].group = None

        if self._active is tab:
            self._active = None
            if self._tabs:
                self._activate(self._tabs[-1])

        self._rebuild_tab_buttons()

        if not self._tabs:
            self.cmd_new_tab()

    # ------------------------------------------------------------------
    # Quit / session
    # ------------------------------------------------------------------
    def _on_quit(self):
        self._save_session()
        self.destroy()

    def _save_session(self):
        data = {"tabs": [], "groups": {}}
        grp_map = {}
        for tab in self._tabs:
            grp_id = None
            if tab.group is not None:
                grp_id = id(tab.group)
                if grp_id not in grp_map:
                    grp_map[grp_id] = {
                        "name":      tab.group.label,
                        "color":     tab.group.color,
                        "collapsed": tab.group.collapsed,
                    }
                    data["groups"][str(grp_id)] = grp_map[grp_id]
            data["tabs"].append({
                "title":    tab.title.rstrip(" *"),
                "filepath": tab.filepath,
                "color":    tab.color,
                "group_id": str(grp_id) if grp_id is not None else None,
                "content":  tab.text.get("1.0", "end-1c") if tab.text else "",
            })
        try:
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load_session(self):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return False
        groups_by_id = {}
        for gid, gdata in data.get("groups", {}).items():
            grp = TabGroup()
            grp.label     = gdata.get("name", "Group")
            grp.color     = gdata.get("color")
            grp.collapsed = gdata.get("collapsed", False)
            groups_by_id[gid] = grp
        tabs_data = data.get("tabs", [])
        if not tabs_data:
            return False
        for td in tabs_data:
            tab = self.cmd_new_tab(title=td.get("title", "Untitled"))
            if tab and tab.text:
                tab.text.insert("1.0", td.get("content", ""))
                tab.text.edit_reset()
                tab.modified  = False
                tab.filepath  = td.get("filepath")
                tab.color     = td.get("color")
                gid = td.get("group_id")
                if gid and gid in groups_by_id:
                    tab.group = groups_by_id[gid]
                self._refresh_tab_label(tab)
        self._rebuild_tab_buttons()
        if self._tabs:
            self._activate(self._tabs[0])
        return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
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
