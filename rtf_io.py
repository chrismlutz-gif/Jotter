"""rtf_io.py  -  Basic RTF read/write for Jotter.

Supported: bold, italic, underline, font family/size,
           foreground colour, background highlight, paragraph alignment.
"""
import re


# ---------------------------------------------------------------------------
# Tag-name conventions  (shared between parser and writer)
# ---------------------------------------------------------------------------
def tag_bold():          return "fmt_bold"
def tag_italic():        return "fmt_italic"
def tag_underline():     return "fmt_underline"
def tag_strikethrough(): return "fmt_strike"
def tag_bold_italic():   return "fmt_bold_italic"
def tag_fg(color):      return "fmt_fg_" + color.lstrip("#").lower()
def tag_bg(color):      return "fmt_bg_" + color.lstrip("#").lower()
def tag_font(name):     return "fmt_fn_" + re.sub(r'\W+', '_', name).strip('_')
def tag_size(pt):       return "fmt_sz_%d" % int(pt)
def tag_align(a):       return "fmt_al_" + a


def color_from_tag(t):
    """Return '#rrggbb' from a fmt_fg_* or fmt_bg_* tag, else None."""
    if t.startswith("fmt_fg_") or t.startswith("fmt_bg_"):
        return "#" + t[7:]
    return None


def font_from_tag(t):
    """Return family name from a fmt_fn_* tag, else None."""
    if t.startswith("fmt_fn_"):
        return t[7:].replace('_', ' ')
    return None


def size_from_tag(t):
    """Return int pt size from a fmt_sz_* tag, else None."""
    if t.startswith("fmt_sz_"):
        try:
            return int(t[7:])
        except ValueError:
            pass
    return None


def align_from_tag(t):
    """Return alignment string from a fmt_al_* tag, else None."""
    if t.startswith("fmt_al_"):
        return t[7:]
    return None


# ---------------------------------------------------------------------------
# RTF PARSER
# ---------------------------------------------------------------------------
_TOK = re.compile(
    r'\{|\}|\\([a-zA-Z]+)(-?\d+)? ?|\\'
    r"'([0-9a-fA-F]{2})|\\([\\{}*-])|([^\\{}\r\n]+)|[\r\n]",
    re.DOTALL
)


def _rgb(r, g, b):
    return "#%02x%02x%02x" % (int(r), int(g), int(b))


def _extract_tables(rtf):
    fonts  = {0: "Consolas"}
    colors = [None]          # index 0 = auto

    ft = re.search(r'\{\\fonttbl(.*?)\}(?=\s*[\{\\])', rtf, re.DOTALL)
    if ft:
        for m in re.finditer(r'\{\\f(\d+)\b[^}]*?([A-Za-z][A-Za-z0-9 ]*);?\s*\}',
                             ft.group(1)):
            fonts[int(m.group(1))] = m.group(2).strip().rstrip(';').strip()

    ct = re.search(r'\{\\colortbl([^}]*)\}', rtf)
    if ct:
        r = g = b = 0
        for entry in re.split(r';', ct.group(1)):
            entry = entry.strip()
            if not entry:
                colors.append(None)
                continue
            rm = re.search(r'\\red(\d+)',   entry)
            gm = re.search(r'\\green(\d+)', entry)
            bm = re.search(r'\\blue(\d+)',  entry)
            if rm: r = int(rm.group(1))
            if gm: g = int(gm.group(1))
            if bm: b = int(bm.group(1))
            colors.append(_rgb(r, g, b))
            r = g = b = 0

    return fonts, colors


def _flush(widget, chars, state, fonts, colors):
    if not chars:
        return
    text = ''.join(chars)
    chars.clear()
    start = widget.index("end-1c")
    widget.insert("end", text)
    end = widget.index("end-1c")
    if start == end:
        return

    def cfg(tag, **kw):
        try:
            widget.tag_configure(tag, **kw)
        except Exception:
            pass

    b  = state.get('b',      False)
    it = state.get('i',      False)
    ul = state.get('ul',     False)
    sk = state.get('strike', False)

    if b and it:
        cfg(tag_bold_italic(), font=("Consolas", 11, "bold italic"))
        widget.tag_add(tag_bold_italic(), start, end)
    elif b:
        cfg(tag_bold(), font=("Consolas", 11, "bold"))
        widget.tag_add(tag_bold(), start, end)
    elif it:
        cfg(tag_italic(), font=("Consolas", 11, "italic"))
        widget.tag_add(tag_italic(), start, end)

    if ul:
        cfg(tag_underline(), underline=True)
        widget.tag_add(tag_underline(), start, end)

    if sk:
        cfg(tag_strikethrough(), overstrike=True)
        widget.tag_add(tag_strikethrough(), start, end)

    fs = state.get('fs', 24)
    pt = max(6, fs // 2)
    fi = state.get('f', 0)
    fn = fonts.get(fi, "Consolas")
    if pt != 11 or fn != "Consolas":
        tg = tag_font(fn) if fn != "Consolas" else tag_size(pt)
        cfg(tg, font=(fn, pt))
        widget.tag_add(tg, start, end)

    cf = state.get('cf', 0)
    if cf and 0 < cf < len(colors) and colors[cf]:
        tg = tag_fg(colors[cf])
        cfg(tg, foreground=colors[cf])
        widget.tag_add(tg, start, end)

    hl = state.get('hl', 0)
    if hl and 0 < hl < len(colors) and colors[hl]:
        tg = tag_bg(colors[hl])
        cfg(tg, background=colors[hl])
        widget.tag_add(tg, start, end)

    al = state.get('al', 'left')
    if al != 'left':
        tg = tag_align(al)
        cfg(tg, justify=al if al in ('left','center','right') else 'left')
        widget.tag_add(tg, start, end)


def parse_rtf(widget, rtf_string):
    """Parse *rtf_string* and insert formatted text into *widget*."""
    fonts, colors = _extract_tables(rtf_string)
    default = dict(b=False, i=False, ul=False, fs=24, f=0,
                   cf=0, hl=0, al='left', skip=False)
    state = dict(default)
    stack = []
    chars = []

    for m in _TOK.finditer(rtf_string):
        full  = m.group(0)
        cw    = m.group(1)
        param = m.group(2)
        hex2  = m.group(3)
        esc   = m.group(4)
        text  = m.group(5)

        if full in ('\r', '\n'):
            continue

        if full == '{':
            _flush(widget, chars, state, fonts, colors)
            stack.append(dict(state))
            continue

        if full == '}':
            _flush(widget, chars, state, fonts, colors)
            state = stack.pop() if stack else dict(default)
            continue

        if state['skip']:
            continue

        if hex2:
            chars.append(chr(int(hex2, 16)))
            continue

        if esc:
            chars.append(esc)
            continue

        if text:
            chars.append(text)
            continue

        if cw is None:
            continue

        n = int(param) if param is not None else None

        SKIP_DESTS = {'fonttbl','colortbl','stylesheet','info',
                      'pict','object','header','footer','fldinst','fldrslt'}
        if cw in SKIP_DESTS:
            state['skip'] = True
        elif cw == '*':
            state['skip'] = True
        elif cw == 'pard':
            state.update(b=False, i=False, ul=False, cf=0, hl=0, al='left')
        elif cw == 'par':
            _flush(widget, chars, state, fonts, colors)
            widget.insert("end", "\n")
        elif cw == 'line':
            _flush(widget, chars, state, fonts, colors)
            widget.insert("end", "\n")
        elif cw == 'tab':
            chars.append('\t')
        elif cw == 'b':   state['b']  = (n != 0)
        elif cw == 'i':   state['i']  = (n != 0)
        elif cw == 'ul':  state['ul'] = True
        elif cw in ('ulnone', 'ul0'): state['ul'] = False
        elif cw == 'strike': state['strike'] = (n != 0)
        elif cw == 'striked0': state['strike'] = False
        elif cw == 'fs':  state['fs'] = n if n is not None else 24
        elif cw == 'f':   state['f']  = n if n is not None else 0
        elif cw == 'cf':  state['cf'] = n if n is not None else 0
        elif cw in ('highlight', 'cb'): state['hl'] = n if n is not None else 0
        elif cw in ('ql', 'ltrpar'):    state['al'] = 'left'
        elif cw == 'qc':  state['al'] = 'center'
        elif cw == 'qr':  state['al'] = 'right'
        elif cw == 'qj':  state['al'] = 'left'   # tkinter has no justify

    _flush(widget, chars, state, fonts, colors)
    if widget.get("1.0", "1.1") == "\n":
        widget.delete("1.0", "1.1")


# ---------------------------------------------------------------------------
# RTF WRITER
# ---------------------------------------------------------------------------

def _rtf_escape(ch):
    """Escape a single character for RTF output."""
    if ch == '\\': return r'\\'
    if ch == '{':  return r'\{'
    if ch == '}':  return r'\}'
    if ch == '\n': return r'\par' + '\n'
    if ch == '\t': return r'\tab '
    code = ord(ch)
    if code <= 127:
        return ch
    # Non-ASCII: emit as \'xx
    if code <= 255:
        return "\\'%02x" % code
    # Unicode fallback
    return "\\u%d?" % code


def generate_rtf(widget):
    """Serialize *widget* content + tags back to an RTF string."""
    content = widget.get("1.0", "end-1c")
    if not content:
        return r'{\rtf1\ansi }'

    # Collect per-character tag sets
    char_tags = []
    for ci in range(len(content)):
        char_tags.append(frozenset(widget.tag_names("1.0+%dc" % ci)))

    # Discover fonts & colors used
    all_fonts  = {}    # name  -> 0-based index
    all_colors = {}    # #hex  -> 1-based index  (RTF colortbl is 1-based)

    def get_fi(name):
        if name not in all_fonts:
            all_fonts[name] = len(all_fonts)
        return all_fonts[name]

    def get_ci(color):
        c = color.lower()
        if c not in all_colors:
            all_colors[c] = len(all_colors) + 1
        return all_colors[c]

    for tags in char_tags:
        for t in tags:
            fn = font_from_tag(t)
            if fn: get_fi(fn)
            clr = color_from_tag(t)
            if clr: get_ci(clr)

    # Header
    buf = [r'{\rtf1\ansi\deff0']

    # Font table
    buf.append(r'{\fonttbl{\f0\fmodern\fcharset0 Consolas;}')
    for name, idx in sorted(all_fonts.items(), key=lambda x: x[1]):
        buf.append(r'{\f%d\froman\fcharset0 %s;}' % (idx + 1, name))
    buf.append('}')

    # Color table
    if all_colors:
        buf.append(r'{\colortbl;')
        for color, _ in sorted(all_colors.items(), key=lambda x: x[1]):
            r_v = int(color[1:3], 16)
            g_v = int(color[3:5], 16)
            b_v = int(color[5:7], 16)
            buf.append(r'\red%d\green%d\blue%d;' % (r_v, g_v, b_v))
        buf.append('}')

    # Content
    prev = dict(b=False, i=False, ul=False, strike=False,
                fg=None, bg=None, fn=None, sz=11, al='left')
    body = []
    lines = content.split('\n')
    ci = 0

    def escape(c):
        if c == '\\': return r'\\'
        if c == '{':  return r'\{'
        if c == '}':  return r'\}'
        if ord(c) > 127:
            return r"\'" + format(ord(c) & 0xFF, '02x')
        return c

    for li, line in enumerate(lines):
        if li > 0:
            body.append(r'\pard\ql' + '\n' + r'\par' + '\n')
            prev.update(b=False, i=False, ul=False, strike=False,
                        fg=None, bg=None, fn=None, sz=11, al='left')

        for char in line:
            tags = char_tags[ci] if ci < len(char_tags) else frozenset()
            ci += 1

            b  = tag_bold()          in tags or tag_bold_italic() in tags
            it = tag_italic()        in tags or tag_bold_italic() in tags
            ul = tag_underline()     in tags
            sk = tag_strikethrough() in tags

            fg  = next((color_from_tag(t) for t in tags if t.startswith("fmt_fg_")), None)
            bg  = next((color_from_tag(t) for t in tags if t.startswith("fmt_bg_")), None)
            fn  = next((font_from_tag(t)  for t in tags if t.startswith("fmt_fn_")), None)
            sz  = next((size_from_tag(t)  for t in tags if t.startswith("fmt_sz_")), 11)
            al  = next((align_from_tag(t) for t in tags if t.startswith("fmt_al_")), 'left')

            ctrl = []
            if b  != prev['b']:      ctrl.append(r'\b'      + ('' if b  else '0'));    prev['b']      = b
            if it != prev['i']:      ctrl.append(r'\i'      + ('' if it else '0'));    prev['i']      = it
            if ul != prev['ul']:     ctrl.append(r'\ul'     + ('' if ul else 'none')); prev['ul']     = ul
            if sk != prev['strike']: ctrl.append(r'\strike' + ('' if sk else '0'));    prev['strike'] = sk
            if sz != prev['sz']:  ctrl.append(r'\fs%d' % (sz * 2));           prev['sz'] = sz
            if fn != prev['fn']:
                fi = get_fi(fn) + 1 if fn else 0
                ctrl.append(r'\f%d' % fi); prev['fn'] = fn
            if fg != prev['fg']:
                ci2 = get_ci(fg) + 1 if fg else 0
                ctrl.append(r'\cf%d' % ci2); prev['fg'] = fg
            if bg != prev['bg']:
                ci2 = get_ci(bg) + 1 if bg else 0
                ctrl.append(r'\highlight%d' % ci2); prev['bg'] = bg
            if al != prev['al']:
                ql = {'left': r'\ql', 'center': r'\qc', 'right': r'\qr'}.get(al, r'\ql')
                ctrl.append(ql); prev['al'] = al

            if ctrl:
                body.append('{' + ''.join(ctrl) + ' }')
            body.append(_rtf_escape(char))

    body.append(r'\par' + '\n}')
    buf.append(r'\pard\ql' + '\n')
    return ''.join(buf) + ''.join(body)
