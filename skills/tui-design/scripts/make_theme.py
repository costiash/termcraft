#!/usr/bin/env python3
"""make_theme.py — write a self-contained theme.py for a harness from the theme bank.

    python3 make_theme.py --theme noir --name PB --out ./theme.py
    python3 make_theme.py --theme paper --name "promoter" --banner slab --accent "#c96a2b" --out ./theme.py

The file it writes has no dependency on this plugin: a THEME object (roles(bg), glyphs, box, banner),
BANNER lines (block font, ≤ 80 cols, ASCII fallback) and the legacy PALETTE/BOX names, so a harness does

    from theme import THEME, BANNER
    ui = UI("pb", banner=BANNER, theme=THEME)

--accent / --ink / --ok / --warn / --stop override single roles (dark palette; the light palette derives a darker shade).
"""
from __future__ import annotations

import json, sys, re
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import themes, banner

TEMPLATE = '''{doc!r}
from types import SimpleNamespace as _NS

THEME_ID = {tid!r}
_DARK = {dark}
_LIGHT = {light}
_GLYPHS = _NS(**{glyphs})

class _Theme:
    id = THEME_ID
    box = {box!r}
    banner = {bstyle!r}
    glyphs = _GLYPHS
    ansi16 = {ansi16}
    def roles(self, background="dark"):
        return dict(_LIGHT if background == "light" else _DARK)

THEME = _Theme()
BANNER = {banner_lines}
BANNER_ASCII = {banner_ascii}
THEME.banner_ascii = BANNER_ASCII   # harness_kit.UI swaps this in on non-UTF terminals / HARNESS_ASCII=1
# legacy names (harnesses generated before termcraft 0.6)
PALETTE = dict(_DARK)
BOX = {box!r}
'''

def _darken(hexcol: str, f: float = 0.55) -> str:
    h = hexcol.lstrip("#"); r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))

def main():
    a = sys.argv[1:]
    def opt(k, d=None): return a[a.index(k) + 1] if k in a else d
    tid = opt("--theme", "slate"); name = opt("--name", "harness"); out = Path(opt("--out", "theme.py"))
    if tid not in themes.THEMES: sys.exit(f"unknown theme {tid}; choose from {', '.join(themes.THEMES)}")
    t = themes.THEMES[tid]
    dark = dict(t.palette); light = dict(t.light)
    for role in ("ink", "dim", "accent", "ok", "warn", "stop"):
        v = opt(f"--{role}")
        if v:
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", v): sys.exit(f"--{role} requires #rrggbb")
            dark[role] = v; light[role] = _darken(v)
    bstyle = opt("--banner", t.banner)
    lines = banner.fit(banner.render(name, bstyle), 80, name)
    ascii_lines = banner.fit(banner.render(name, bstyle, ascii_only=True), 80, name)
    g = asdict(t.glyphs)
    text = TEMPLATE.format(doc=f"theme.py — {name} (termcraft, theme {tid}).\n{t.recipe}\n{t.mood}", name=name, tid=tid, recipe=t.recipe, mood=t.mood, dark=json.dumps(dark), light=json.dumps(light),
                           glyphs=json.dumps(g, ensure_ascii=False), box=t.box, bstyle=bstyle, ansi16=json.dumps(t.ansi16),
                           banner_lines=json.dumps(lines, ensure_ascii=False, indent=4), banner_ascii=json.dumps(ascii_lines, indent=4))
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out} (theme {tid}, banner {bstyle}, {len(lines)} lines ≤ {max(len(l) for l in lines)} cols)")

if __name__ == "__main__": main()
