#!/usr/bin/env python3
"""tui_frame.py — minimal terminal frame buffer for the termcraft plugin.

Import it (Frame, box, meter, sparkline, Spinner, reveal, table, kv, badge, columns, tree, tabs, wrap) or run it for a demo:
  python tui_frame.py            # animated splash + dashboard demo
  NO_COLOR=1 python tui_frame.py # monochrome
  python tui_frame.py | cat      # non-TTY: prints the final frame once

Design rules baked in: diff-based redraw (only changed cells are rewritten), terminal
state restored on exit / Ctrl-C, colour capability ladder (NO_COLOR → truecolor → 256 → 16),
box drawing, ▁▂▃▄▅▆▇█ sparklines, █▓▒░ meters, Braille spinner, Reveal animation.
Zero dependencies.
"""
import atexit
import os
import shutil
import signal
import sys
import time

BOX = {
    "light": "┌─┐│└┘├┤┬┴┼",
    "rounded": "╭─╮│╰╯├┤┬┴┼",
    "heavy": "┏━┓┃┗┛┣┫┳┻╋",
    "double": "╔═╗║╚╝╠╣╦╩╬",
}
SPARK = "▁▂▃▄▅▆▇█"
METER = "█▓▒░"
BRAILLE_SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


# ---------------------------------------------------------------- colour

def color_mode():
    if "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb" or not sys.stdout.isatty():
        return "none"
    if os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return "truecolor"
    if "256color" in os.environ.get("TERM", ""):
        return "256"
    return "16"


MODE = color_mode()


def fg(hexcol):
    """Return an ANSI fg escape for #rrggbb under the detected capability."""
    if MODE == "none" or hexcol is None:
        return ""
    r, g, b = (int(hexcol.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    if MODE == "truecolor":
        return f"\x1b[38;2;{r};{g};{b}m"
    if MODE == "256":
        n = 16 + 36 * round(r / 51) + 6 * round(g / 51) + round(b / 51)
        return f"\x1b[38;5;{n}m"
    return "\x1b[37m" if (r + g + b) > 380 else "\x1b[90m"


RESET = "\x1b[0m" if MODE != "none" else ""
DIM = "\x1b[2m" if MODE != "none" else ""
BOLD = "\x1b[1m" if MODE != "none" else ""


# ---------------------------------------------------------------- frame buffer

class Frame:
    """Grid of (char, style) cells with diff-based flushing."""

    def __init__(self, cols=None, rows=None):
        size = shutil.get_terminal_size((80, 24))
        self.cols = cols or size.columns
        self.rows = rows or size.lines
        self.cells = [[(" ", "")] * self.cols for _ in range(self.rows)]
        self._prev = None
        self.tty = sys.stdout.isatty()

    def put(self, x, y, text, style=""):
        if not (0 <= y < self.rows):
            return
        for i, ch in enumerate(text):
            if 0 <= x + i < self.cols:
                self.cells[y][x + i] = (ch, style)

    def clear(self):
        self.cells = [[(" ", "")] * self.cols for _ in range(self.rows)]

    def render(self):
        return "\n".join("".join(f"{s}{c}{RESET if s else ''}" for c, s in row).rstrip() for row in self.cells)

    def flush(self):
        """Write only cells that changed since the last flush (full write the first time)."""
        if not self.tty:
            return
        out = []
        if self._prev is None:
            out.append("\x1b[H\x1b[2J")
            for y, row in enumerate(self.cells):
                out.append(f"\x1b[{y + 1};1H" + "".join(f"{s}{c}{RESET if s else ''}" for c, s in row))
        else:
            for y, row in enumerate(self.cells):
                prev = self._prev[y]
                x = 0
                while x < self.cols:
                    if row[x] == prev[x]:
                        x += 1
                        continue
                    start = x
                    seg = []
                    while x < self.cols and row[x] != prev[x]:
                        c, s = row[x]
                        seg.append(f"{s}{c}{RESET if s else ''}")
                        x += 1
                    out.append(f"\x1b[{y + 1};{start + 1}H" + "".join(seg))
        self._prev = [list(r) for r in self.cells]
        sys.stdout.write("".join(out))
        sys.stdout.flush()


# ---------------------------------------------------------------- widgets

def box(frame, x, y, w, h, weight="light", title=None, style=""):
    tl, hz, tr, vt, bl, br = BOX[weight][:6]
    frame.put(x, y, tl + hz * (w - 2) + tr, style)
    for yy in range(y + 1, y + h - 1):
        frame.put(x, yy, vt, style)
        frame.put(x + w - 1, yy, vt, style)
    frame.put(x, y + h - 1, bl + hz * (w - 2) + br, style)
    if title:
        frame.put(x + 2, y, f" {title} ", style + BOLD)


def meter(value, width, ramp=METER):
    """0..1 → bar of `width` cells using the █▓▒░ ramp with a soft head."""
    if width <= 0: return ""
    value = max(0, min(1, value))
    full = int(value * width)
    frac = value * width - full
    head = ramp[min(len(ramp) - 1, int((1 - frac) * (len(ramp) - 1)))] if full < width else ""
    return (ramp[0] * full + head).ljust(width, ramp[-1])


def sparkline(values, width=None):
    vals = list(values)
    if width is not None: vals = vals[-width:] if width > 0 else []
    if not vals: return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    return "".join(SPARK[int((v - lo) / rng * (len(SPARK) - 1))] for v in vals)


class Spinner:
    def __init__(self, frames=BRAILLE_SPIN, interval=0.08):
        self.frames, self.interval, self.t0 = frames, interval, time.perf_counter()

    def __str__(self):
        return self.frames[int((time.perf_counter() - self.t0) / self.interval) % len(self.frames)]


def reveal(lines, progress, crest="░▒▓"):
    """Reveal animation over a list of strings: cells appear in reading order with a bright crest."""
    if progress >= 1:
        return list(lines)
    total = sum(len(l) for l in lines)
    shown = int(progress * total)
    out, count = [], 0
    for line in lines:
        row = []
        for ch in line:
            if count < shown - len(crest):
                row.append(ch)
            elif count < shown:
                row.append(crest[shown - count - 1] if ch != " " else " ")
            else:
                row.append(" ")
            count += 1
        out.append("".join(row))
    return out


# ---------------------------------------------------------------- more widgets (all return lists of strings; theme colours are applied by the caller)

def table(rows: list[list[str]], headers: list[str] | None = None, widths: list[int] | None = None, gap: int = 2, rule: str = "─") -> list[str]:
    """Plain aligned table. Column widths from content unless given; header underlined with `rule`. No vertical borders."""
    if not rows and not headers: return []
    cols = len(headers or rows[0])
    widths = widths or [max(len(str(r[i])) for r in ([headers] if headers else []) + rows) for i in range(cols)]
    fmt = lambda r: (" " * gap).join(str(c).ljust(w)[:w] for c, w in zip(r, widths))
    out = []
    if headers: out += [fmt(headers), (" " * gap).join(rule * w for w in widths)]
    return out + [fmt(r) for r in rows]

def kv(pairs: list[tuple[str, str]], key_w: int | None = None, sep: str = "  ") -> list[str]:
    """Key/value block, keys right-padded to one column."""
    if not pairs: return []
    key_w = key_w or max(len(k) for k, _ in pairs)
    return [f"{k.ljust(key_w)}{sep}{v}" for k, v in pairs]

def badge(text: str, kind: str = "ok") -> str:
    """Status badge glyph+text: ok ✓ · warn ! · stop ✗ · info i · wait …"""
    return {"ok": "✓ ", "warn": "! ", "stop": "✗ ", "info": "i ", "wait": "… "}.get(kind, "") + text

def columns(blocks: list[list[str]], width: int, gap: int = 2) -> list[str]:
    """Lay N blocks side by side in equal columns; blocks wider than a column are cut with '…'."""
    if not blocks: return []
    if width < len(blocks) + gap * (len(blocks) - 1): raise ValueError("columns do not fit width")
    n = len(blocks); cw = (width - gap * (n - 1)) // n
    h = max(len(b) for b in blocks)
    def cell(b, i): return (b[i] if i < len(b) else "")[:cw].ljust(cw) if len(b[i] if i < len(b) else "") <= cw else b[i][:cw - 1] + "…"
    return [(" " * gap).join(cell(b, i) for b in blocks) for i in range(h)]

def tree(node: dict | list | str, prefix: str = "") -> list[str]:
    """Render nested dict/list as a box-drawing tree: {'a': {'b': None, 'c': ['d']}}"""
    out = []
    items = list(node.items()) if isinstance(node, dict) else [(x, None) for x in node] if isinstance(node, list) else [(node, None)]
    for i, (name, child) in enumerate(items):
        last = i == len(items) - 1
        out.append(f"{prefix}{'└─ ' if last else '├─ '}{name}")
        if child: out += tree(child, prefix + ("   " if last else "│  "))
    return out

def tabs(names: list[str], active: int) -> str:
    """Tab strip: the active tab in brackets, others dim (caller colours it)."""
    return "  ".join(f"[{n}]" if i == active else f" {n} " for i, n in enumerate(names))

def wrap(text: str, width: int, indent: int = 0) -> list[str]:
    import textwrap
    return textwrap.wrap(text, width=width, initial_indent=" " * indent, subsequent_indent=" " * indent) or [""]


# ---------------------------------------------------------------- terminal hygiene

def enter():
    if sys.stdout.isatty():
        sys.stdout.write("\x1b[?1049h\x1b[?25l")
        sys.stdout.flush()


def leave(*_):
    if sys.stdout.isatty():
        sys.stdout.write(RESET + "\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()


def run(loop, fps=30, duration=None, animate=True):
    """Run a single-cell grid; restore terminal state even if a callback fails."""
    if not 0 < fps <= 30: raise ValueError("fps must be in (0, 30]")
    if duration is not None and duration < 0: raise ValueError("duration must be nonnegative")
    frame = Frame()
    if not frame.tty or not animate or "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb":
        loop(frame, duration or 0)
        sys.stdout.write(frame.render() + "\n")
        return
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    def stop(sig, _): raise SystemExit(128 + sig)
    try:
        for sig in previous: signal.signal(sig, stop)
        enter()
        t0 = time.perf_counter()
        while True:
            t = time.perf_counter() - t0
            size = shutil.get_terminal_size((80, 24))
            if (frame.cols, frame.rows) != (size.columns, size.lines): frame = Frame()
            loop(frame, min(t, duration) if duration is not None else t)
            frame.flush()
            if duration is not None and t >= duration: break
            time.sleep(max(0, 1 / fps - (time.perf_counter() - t0 - t)))
    finally:
        leave()
        for sig, handler in previous.items(): signal.signal(sig, handler)


# ---------------------------------------------------------------- demo

BANNER = [
    "█████╗ ███████╗ ██████╗██╗██╗",
    "██╔══██╗██╔════╝██╔════╝██║██║",
    "███████║███████╗██║     ██║██║",
    "██╔══██║╚════██║██║     ██║██║",
    "██║  ██║███████║╚██████╗██║██║",
    "╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝╚═╝",
]

if __name__ == "__main__":
    import math

    GB = ["#0f380f", "#306230", "#8bac0f", "#9bbc0f"]  # Game Boy palette from references/dither.md
    spin = Spinner()
    series = [0.0] * 40

    def demo(f, t):
        f.clear()
        prog = min(1.0, t / 1.4)  # Reveal entrance, ends in a stable frame
        for i, line in enumerate(reveal(BANNER, prog)):
            f.put(2, 1 + i, line, fg(GB[3]))
        box(f, 0, 8, min(f.cols, 60), 9, "rounded", "signals", fg(GB[2]))
        series.append(0.5 + 0.45 * math.sin(t * 2.1) * math.cos(t * 0.7))
        del series[0]
        f.put(2, 10, "load  " + meter(series[-1], 30) + f" {series[-1]:4.0%}", fg(GB[3]))
        f.put(2, 12, "trend " + sparkline(series, 40), fg(GB[2]))
        f.put(2, 14, f"{spin} rendering…", fg(GB[1]) + DIM)
        f.put(0, f.rows - 1, DIM + "recipe:v1:{\"style\":\"block\",\"palette\":\"gameboy\",\"anim\":\"reveal\"}  ctrl-c to quit"[: f.cols], "")

    run(demo, fps=30, duration=None if sys.stdout.isatty() and "--no-animation" not in sys.argv and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb" else 2, animate="--no-animation" not in sys.argv)
