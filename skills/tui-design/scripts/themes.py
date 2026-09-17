#!/usr/bin/env python3
"""themes.py — the termcraft theme bank. Importable data, stdlib only.

A Theme is everything a terminal surface needs to look like one designed thing:
  palette   six roles (ink, dim, accent, ok, warn, stop) as #rrggbb for truecolor, with a 16-colour ANSI fallback per role
  light     the same roles tuned for a LIGHT terminal background (never assume dark — see detect_background())
  box       one box-drawing weight: light | rounded | heavy | double | ascii
  glyphs    spinner frames, meter ramp, marks (done/todo/blocked/unknown/waiting), rule character, bullet
  banner    how the name is set: block (built-in block font, ANSI shadow) | slab | shade | plain
  mood      one line: what it is for
  recipe    the termcraft recipe line for the record

    python3 themes.py            # list themes
    python3 themes.py noir       # print one as JSON
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict

ANSI16 = {  # role → (dark-bg code, light-bg code) in the 16-colour ladder
    "ink": ("37", "30"), "dim": ("90", "90"), "accent": ("36", "34"), "ok": ("32", "32"), "warn": ("33", "33"), "stop": ("31", "31"),
}

@dataclass
class Glyphs:
    spinner: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    meter: str = "█▓▒░"
    marks: dict = field(default_factory=lambda: {"done": "✓", "todo": "•", "blocked": "✗", "unknown": "?", "waiting": "…", "skip": "·"})
    rule: str = "─"
    bullet: str = "·"
    ascii_fallback: dict = field(default_factory=lambda: {"spinner": "|/-\\", "meter": "#=-.", "marks": {"done": "+", "todo": "*", "blocked": "x", "unknown": "?", "waiting": "~", "skip": "-"}, "rule": "-", "bullet": "-"})

@dataclass
class Theme:
    id: str
    name: str
    mood: str
    palette: dict            # dark background
    light: dict              # light background
    box: str = "rounded"
    banner: str = "block"
    glyphs: Glyphs = field(default_factory=Glyphs)
    recipe: str = ""
    ansi16: dict = field(default_factory=lambda: dict(ANSI16))

    def roles(self, background: str = "dark") -> dict:
        return dict(self.light if background == "light" else self.palette)


THEMES: dict[str, Theme] = {}
def _t(**kw): t = Theme(**kw); THEMES[t.id] = t; return t

_t(id="noir", name="Terminal noir", mood="operator consoles, ops/data/finance tools — sepia ink on black, one amber accent",
   palette={"ink": "#d9c9a1", "dim": "#7b7466", "accent": "#d9a441", "ok": "#8bac0f", "warn": "#e0b04a", "stop": "#e06b6b"},
   light={"ink": "#2b2418", "dim": "#5f584c", "accent": "#9a6a10", "ok": "#3d6b0a", "warn": "#9a6a10", "stop": "#a83a3a"},
   box="light", banner="block", recipe='recipe:v1:{"style":"block","palette":"sepia","fx":["vignette"],"anim":"none"}')

_t(id="blueprint", name="Blueprint", mood="architecture and infra tooling — navy ground, ice ink, cross glyphs",
   palette={"ink": "#dfe9ff", "dim": "#7d8db0", "accent": "#8fc1ff", "ok": "#7fd0a8", "warn": "#e0c07a", "stop": "#ff8a8a"},
   light={"ink": "#0a2a5e", "dim": "#5b6b8a", "accent": "#1d5fb8", "ok": "#1f7a4d", "warn": "#8a6a10", "stop": "#b03030"},
   box="light", banner="shade", glyphs=Glyphs(meter="╬╪┼·", bullet="+", marks={"done": "✓", "todo": "•", "blocked": "✗", "unknown": "?", "waiting": "…", "skip": "·"}),  # todo was "+", which is the ASCII *done* mark — same glyph, opposite meaning across terminals
   recipe='recipe:v1:{"style":"cross","palette":"blueprint","fx":["scanlines"],"anim":"none"}')

_t(id="phosphor", name="Green phosphor", mood="retro terminals, monitoring, anything that wants to feel like a P1 CRT",
   palette={"ink": "#33ff33", "dim": "#1f8f1f", "accent": "#b6ff8a", "ok": "#33ff33", "warn": "#d6e35a", "stop": "#ff6b6b"},
   light={"ink": "#0f4f0f", "dim": "#4f7f4f", "accent": "#1a7f1a", "ok": "#1a7f1a", "warn": "#7f6a10", "stop": "#a83a3a"},
   box="light", banner="block", glyphs=Glyphs(spinner="⡀⡄⡆⡇⣇⣧⣷⣿", meter="█▓▒░"),
   recipe='recipe:v1:{"style":"characters","palette":"phosphor","fx":["scanlines","bloom"],"anim":"none"}')

_t(id="amber", name="Amber phosphor", mood="the same CRT, warmer — long sessions, night use",
   palette={"ink": "#ffb000", "dim": "#8f6300", "accent": "#ffd27a", "ok": "#c8e06b", "warn": "#ffb000", "stop": "#ff7a5a"},
   light={"ink": "#5a3a00", "dim": "#8f6300", "accent": "#a06a00", "ok": "#3d6b0a", "warn": "#a06a00", "stop": "#a83a3a"},
   box="light", banner="block", recipe='recipe:v1:{"style":"characters","palette":"amber","fx":["scanlines"],"anim":"none"}')

_t(id="paper", name="Paper", mood="LIGHT terminals and printouts — ink on paper; the theme to reach for when COLORFGBG says light",
   palette={"ink": "#e8e4dc", "dim": "#9a948a", "accent": "#c96a2b", "ok": "#5a8f3a", "warn": "#b07a1a", "stop": "#b04040"},
   light={"ink": "#1f1d1a", "dim": "#6f6a62", "accent": "#b3511b", "ok": "#3d6b0a", "warn": "#8a5a10", "stop": "#a83a3a"},
   box="rounded", banner="slab", glyphs=Glyphs(meter="■▣▢·", spinner="◐◓◑◒", bullet="•"),
   recipe='recipe:v1:{"style":"dots","palette":"paper","fx":[],"anim":"none"}')

_t(id="cyber", name="Cyber", mood="dev tools that want an edge — magenta/cyan on black, heavy boxes; use sparingly",
   palette={"ink": "#e6e6ff", "dim": "#6f6f9a", "accent": "#ff5fd2", "ok": "#5fffd2", "warn": "#ffd25f", "stop": "#ff5f5f"},
   light={"ink": "#1a1a2e", "dim": "#6f6f9a", "accent": "#a8137a", "ok": "#0f7f5f", "warn": "#8a6a10", "stop": "#b03030"},
   box="heavy", banner="block", glyphs=Glyphs(meter="█▉▊▋", spinner="▁▂▃▄▅▆▇█▇▆▅▄▃▂"),
   recipe='recipe:v1:{"style":"block","palette":"cga","fx":["chromatic","scanlines"],"anim":"none"}')

_t(id="slate", name="Slate", mood="neutral, corporate-safe — grey-blue, one accent; the default when nothing else is justified",
   palette={"ink": "#d7dde3", "dim": "#7b8590", "accent": "#7fb2e0", "ok": "#8bc48a", "warn": "#e0b04a", "stop": "#e06b6b"},
   light={"ink": "#1e2328", "dim": "#6b7580", "accent": "#1f5f9a", "ok": "#2f7a2f", "warn": "#8a6a10", "stop": "#a83a3a"},
   box="rounded", banner="slab", recipe='recipe:v1:{"style":"characters","palette":"mono","fx":[],"anim":"none"}')

_t(id="mono", name="Mono", mood="no colour at all by design — hierarchy from weight and glyph density only; what NO_COLOR users see",
   palette={"ink": "#e0e0e0", "dim": "#8a8a8a", "accent": "#ffffff", "ok": "#e0e0e0", "warn": "#e0e0e0", "stop": "#ffffff"},
   light={"ink": "#202020", "dim": "#707070", "accent": "#000000", "ok": "#202020", "warn": "#202020", "stop": "#000000"},
   ansi16={role: ("90", "90") if role == "dim" else ("37", "30") for role in ANSI16},
   box="double", banner="shade", glyphs=Glyphs(meter="█▓▒░", marks={"done": "[x]", "todo": "[ ]", "blocked": "[!]", "unknown": "[?]", "waiting": "[~]", "skip": "[-]"}),
   recipe='recipe:v1:{"style":"block","palette":"1-bit","fx":[],"anim":"none"}')


def detect_background() -> str:
    """'light' | 'dark' | 'unknown'. Uses COLORFGBG (rxvt/konsole/iTerm set it as 'fg;bg'); 15 = white bg."""
    v = os.environ.get("COLORFGBG", "")
    if ";" in v:
        bg = v.split(";")[-1]
        if bg.isdigit(): return "light" if int(bg) in (7, 15) else "dark"
    if os.environ.get("TERMCRAFT_BG") in ("light", "dark"): return os.environ["TERMCRAFT_BG"]
    return "unknown"


def unicode_ok() -> bool:
    enc = (sys.stdout.encoding or "").lower()
    return "utf" in enc and os.environ.get("TERMCRAFT_ASCII") != "1"


if __name__ == "__main__":
    if len(sys.argv) > 1:
        t = THEMES.get(sys.argv[1]); print(json.dumps(asdict(t), indent=2, ensure_ascii=False) if t else f"unknown theme; choose from {', '.join(THEMES)}")
    else:
        for t in THEMES.values(): print(f"{t.id:<10} {t.name:<16} box={t.box:<8} banner={t.banner:<8} {t.mood}")
