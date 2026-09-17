#!/usr/bin/env python3
"""banner.py — block-letter banners with no dependencies (no FIGlet). Styles: block (ANSI-shadow █╗╝), slab (solid █), shade (▒ fill), plain. ≤ 80 columns, ASCII fallback.

    python3 banner.py "PB" --style block            # █ letters with ╗╝ shading (the classic ANSI-shadow look)
    python3 banner.py "promoter" --style slab       # solid █ letters, no shadow — quieter
    python3 banner.py "PB" --style shade            # ▒-filled — lighter weight, for light terminals and Mono
    python3 banner.py "PB" --ascii                  # '#' letters for TERMCRAFT_ASCII / non-UTF terminals
    python3 banner.py "PB" --fit 40                 # refuse or fall back to plain if wider than N columns

Import: from banner import render;  render("PB", style="block") -> list[str]
The font is a 5-row, 5-wide cap font for A–Z 0–9 - _ . space. Lowercase is upper-cased. Unknown glyphs → '?'.
"""
from __future__ import annotations

import sys

# 5x5 bitmap font: rows of 5 chars, '#' = ink. Compact but readable at terminal sizes.
FONT = {
"A":["  #  "," # # ","#####","#   #","#   #"], "B":["#### ","#   #","#### ","#   #","#### "],
"C":[" ####","#    ","#    ","#    "," ####"], "D":["#### ","#   #","#   #","#   #","#### "],
"E":["#####","#    ","#### ","#    ","#####"], "F":["#####","#    ","#### ","#    ","#    "],
"G":[" ####","#    ","#  ##","#   #"," ####"], "H":["#   #","#   #","#####","#   #","#   #"],
"I":["#####","  #  ","  #  ","  #  ","#####"], "J":["#####","   # ","   # ","#  # "," ##  "],
"K":["#   #","#  # ","###  ","#  # ","#   #"], "L":["#    ","#    ","#    ","#    ","#####"],
"M":["#   #","## ##","# # #","#   #","#   #"], "N":["#   #","##  #","# # #","#  ##","#   #"],
"O":[" ### ","#   #","#   #","#   #"," ### "], "P":["#### ","#   #","#### ","#    ","#    "],
"Q":[" ### ","#   #","#   #","#  # "," ## #"], "R":["#### ","#   #","#### ","#  # ","#   #"],
"S":[" ####","#    "," ### ","    #","#### "], "T":["#####","  #  ","  #  ","  #  ","  #  "],
"U":["#   #","#   #","#   #","#   #"," ### "], "V":["#   #","#   #","#   #"," # # ","  #  "],
"W":["#   #","#   #","# # #","## ##","#   #"], "X":["#   #"," # # ","  #  "," # # ","#   #"],
"Y":["#   #"," # # ","  #  ","  #  ","  #  "], "Z":["#####","   # ","  #  "," #   ","#####"],
"0":[" ### ","#  ##","# # #","##  #"," ### "], "1":["  #  "," ##  ","  #  ","  #  "," ### "],
"2":[" ### ","#   #","  ## "," #   ","#####"], "3":["#### ","    #"," ### ","    #","#### "],
"4":["#  # ","#  # ","#####","   # ","   # "], "5":["#####","#    ","#### ","    #","#### "],
"6":[" ### ","#    ","#### ","#   #"," ### "], "7":["#####","   # ","  #  "," #   ","#    "],
"8":[" ### ","#   #"," ### ","#   #"," ### "], "9":[" ### ","#   #"," ####","    #"," ### "],
"-":["     ","     ","#####","     ","     "], "_":["     ","     ","     ","     ","#####"],
".":["     ","     ","     ","     ","  #  "], " ":["     ","     ","     ","     ","     "],
"?":[" ### ","#   #","  ## ","     ","  #  "],
}


def _bitmap(text: str, wide: bool = True) -> list[str]:
    """Rows of '#'/' '. wide=True doubles every cell horizontally so letters read at terminal cell aspect (~1:2)."""
    rows = ["", "", "", "", ""]
    for ch in text.upper():
        g = FONT.get(ch, FONT["?"])
        for i in range(5): rows[i] += ("".join(c * 2 for c in g[i]) if wide else g[i]) + "  "
    return [r.rstrip() for r in rows]


def render(text: str, style: str = "block", ascii_only: bool = False) -> list[str]:
    """Return banner lines. Styles: block (█ + ╗╝ shadow), slab (█ only), shade (▒ fill), plain (text)."""
    if style == "plain": return [text.upper()]
    bm = _bitmap(text)
    if ascii_only:
        return [r for r in bm]
    if style == "slab":
        return [r.replace("#", "█") for r in bm]
    if style == "block":
        # ANSI-shadow look: ink → █, the cell right of an ink run → ╗ where the run starts (no ink above) else ║, bottom row of ╝ under ink
        w = max(len(r) for r in bm) + 1; grid = [r.ljust(w) for r in bm]
        out = []
        for y, r in enumerate(grid):
            line = ""
            for x, c in enumerate(r):
                if c == "#": line += "█"
                elif x > 0 and r[x-1] == "#": line += "╗" if (y == 0 or grid[y-1][x-1] != "#") else "║"
                elif x > 0 and y > 0 and grid[y-1][x-1] == "#" and grid[y-1][x] != "#": line += "╝"   # run ended above: close its shadow
                else: line += " "
            out.append(line.rstrip())
        out.append("".join("╝" if c == "#" else (" ") for c in grid[-1]).rstrip().replace("╝╝", "╝╝"))
        return out
    if style == "shade":
        # ▒-filled letters: half the weight of slab — for light terminals, Mono, and quiet tools
        return [r.replace("#", "▒") for r in bm]
    raise ValueError(f"unknown style {style}")


def fit(lines: list[str], cols: int, text: str) -> list[str]:
    """Banner must fit in `cols`; otherwise fall back to plain."""
    if cols < 1: raise ValueError("cols must be positive")
    return lines if max(map(len, lines), default=0) <= cols else [text.upper()[:cols]]


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args: sys.exit(__doc__)
    text = args[0]; style = args[args.index("--style") + 1] if "--style" in args else "block"
    ascii_only = "--ascii" in args; cols = int(args[args.index("--fit") + 1]) if "--fit" in args else 80
    for ln in fit(render(text, style, ascii_only), cols, text): print(ln)
