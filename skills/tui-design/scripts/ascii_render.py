#!/usr/bin/env python3
"""ascii_render.py — reference image→glyph renderer for the termcraft plugin.

Styles: characters, block, halfblock (truecolor), braille, dots, lines
Dither: none, bayer2, bayer4, bayer8, fs (Floyd–Steinberg), atkinson
Palettes: mono, gameboy, cga, amber, phosphor, sepia, c64  (colour output only)
Output: ansi (default), text (no colour), html (self-contained <pre> page)

Examples:
  python ascii_render.py photo.jpg --cols 80
  python ascii_render.py photo.jpg --style braille --cols 120 --dither bayer4
  python ascii_render.py photo.jpg --style halfblock --palette gameboy --dither atkinson
  python ascii_render.py photo.jpg --edges --contrast 1.4 --invert --out text
  python ascii_render.py photo.jpg --style characters --out html > hero.html

Requires: Pillow, numpy.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

RAMPS = {
    "characters": "@#S08Xx+=-;:,. ",
    "dense": "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. ",
    "block": "█▓▒░ ",
    "dots": "●•∙· ",
    "lines": "┃║│¦| ",
}

PALETTES = {  # dark → light
    "mono": ["#000000", "#ffffff"],
    "gameboy": ["#0f380f", "#306230", "#8bac0f", "#9bbc0f"],
    "cga": ["#000000", "#55ffff", "#ff55ff", "#ffffff"],
    "amber": ["#1a0f00", "#ffb000"],
    "phosphor": ["#001a00", "#33ff33"],
    "sepia": ["#2b1d0e", "#6b4a2b", "#b08a5a", "#efe0c4"],
    "c64": ["#000000", "#ffffff", "#880000", "#aaffee", "#cc44cc", "#00cc55", "#0000aa", "#eeee77",
            "#dd8855", "#664400", "#ff7777", "#333333", "#777777", "#aaff66", "#0088ff", "#bbbbbb"],
}

BAYER2 = np.array([[0, 2], [3, 1]], dtype=np.float32)


def bayer(n):
    m = BAYER2
    while m.shape[0] < n:
        m = np.block([[4 * m, 4 * m + 2], [4 * m + 3, 4 * m + 1]])
    return (m + 0.5) / (m.shape[0] ** 2)


def hex2rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


# ---------------------------------------------------------------- sampling

def load_luma(path, cols, cell_aspect, sub_w=1, sub_h=1, contrast=1.0, brightness=0.0):
    """Return (luma[0..1] HxW, rgb HxWx3) sampled at cols*sub_w x rows*sub_h."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    rows = max(1, int(round(h / w * cols * cell_aspect)))
    img = img.resize((cols * sub_w, rows * sub_h), Image.LANCZOS)
    rgb = np.asarray(img, dtype=np.float32) / 255.0
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    lum = np.clip((lum - 0.5) * contrast + 0.5 + brightness, 0, 1)
    return lum, rgb


# ---------------------------------------------------------------- dither

def dither(lum, method, levels):
    """Quantise lum to `levels` grey levels using the chosen method. Returns indices 0..levels-1."""
    if method == "none":
        return np.round(lum * (levels - 1)).astype(int)
    if method.startswith("bayer"):
        n = int(method[5:])
        m = bayer(n)
        H, W = lum.shape
        tile = np.tile(m, (H // n + 1, W // n + 1))[:H, :W]
        spread = 1.0 / (levels - 1)
        return np.clip(np.floor((lum + (tile - 0.5) * spread) * (levels - 1) + 0.5), 0, levels - 1).astype(int)
    kernels = {
        "fs": (16, [(1, 0, 7), (-1, 1, 3), (0, 1, 5), (1, 1, 1)]),
        "atkinson": (8, [(1, 0, 1), (2, 0, 1), (-1, 1, 1), (0, 1, 1), (1, 1, 1), (0, 2, 1)]),
    }
    div, k = kernels[method]
    buf = lum.astype(np.float32).copy()
    H, W = buf.shape
    out = np.zeros_like(buf, dtype=int)
    for y in range(H):
        rng = range(W) if y % 2 == 0 else range(W - 1, -1, -1)
        sgn = 1 if y % 2 == 0 else -1
        for x in rng:
            old = buf[y, x]
            q = int(np.clip(round(old * (levels - 1)), 0, levels - 1))
            out[y, x] = q
            err = (old - q / (levels - 1)) / div
            for dx, dy, wgt in k:
                xx, yy = x + sgn * dx, y + dy
                if 0 <= xx < W and 0 <= yy < H:
                    buf[yy, xx] += err * wgt
    return out


# ---------------------------------------------------------------- edges

def sobel_strokes(lum, threshold=0.25):
    gx = np.zeros_like(lum)
    gy = np.zeros_like(lum)
    gx[1:-1, 1:-1] = (lum[:-2, 2:] + 2 * lum[1:-1, 2:] + lum[2:, 2:]) - (lum[:-2, :-2] + 2 * lum[1:-1, :-2] + lum[2:, :-2])
    gy[1:-1, 1:-1] = (lum[2:, :-2] + 2 * lum[2:, 1:-1] + lum[2:, 2:]) - (lum[:-2, :-2] + 2 * lum[:-2, 1:-1] + lum[:-2, 2:])
    mag = np.hypot(gx, gy)
    ang = (np.degrees(np.arctan2(gy, gx)) + 180) % 180
    strokes = np.full(lum.shape, "", dtype=object)
    mask = mag > threshold
    strokes[mask & (ang < 22.5)] = "|"
    strokes[mask & (ang >= 22.5) & (ang < 67.5)] = "\\"
    strokes[mask & (ang >= 67.5) & (ang < 112.5)] = "-"
    strokes[mask & (ang >= 112.5) & (ang < 157.5)] = "/"
    strokes[mask & (ang >= 157.5)] = "|"
    return strokes


# ---------------------------------------------------------------- renderers

def render_ramp(lum, rgb, ramp, args):
    if args.invert:
        ramp = ramp[::-1]
    idx = dither(lum, args.dither, len(ramp))
    chars = np.array(list(ramp))[idx]
    if args.edges:
        s = sobel_strokes(lum)
        chars = np.where(s != "", s, chars)
    return chars, rgb


def render_braille(lum, args):
    H, W = lum.shape  # H = rows*4, W = cols*2
    idx = dither(lum, args.dither if args.dither != "none" else "bayer4", 2)
    on = idx.astype(bool) if args.invert else ~idx.astype(bool)  # dark pixels raise dots by default
    rows, cols = H // 4, W // 2
    bits = np.zeros((rows, cols), dtype=int)
    weights = {(0, 0): 1, (0, 1): 2, (0, 2): 4, (1, 0): 8, (1, 1): 16, (1, 2): 32, (0, 3): 64, (1, 3): 128}
    for (cx, cy), wgt in weights.items():
        bits += on[cy::4, cx::2][:rows, :cols] * wgt
    chars = np.vectorize(lambda b: chr(0x2800 + b))(bits)
    return chars


def quantise_rgb(rgb, palette):
    pal = np.stack([hex2rgb(h) / 255 for h in palette])  # P x 3
    d = ((rgb[..., None, :] - pal[None, None]) ** 2).sum(-1)
    return pal[d.argmin(-1)]


# ---------------------------------------------------------------- output

def ansi_fg(c):
    r, g, b = (int(v * 255) for v in c)
    return f"\x1b[38;2;{r};{g};{b}m"


def ansi_bg(c):
    r, g, b = (int(v * 255) for v in c)
    return f"\x1b[48;2;{r};{g};{b}m"


def emit(chars, fg=None, bg=None, out="ansi", title="ascii"):
    H, W = chars.shape
    lines = []
    if out == "text" or fg is None:
        for y in range(H):
            lines.append("".join(chars[y]))
    elif out == "ansi":
        for y in range(H):
            row, last = [], None
            for x in range(W):
                key = (tuple(fg[y, x]), tuple(bg[y, x]) if bg is not None else None)
                if key != last:
                    row.append(ansi_fg(fg[y, x]) + (ansi_bg(bg[y, x]) if bg is not None else ""))
                    last = key
                row.append(chars[y, x])
            row.append("\x1b[0m")
            lines.append("".join(row))
    elif out == "html":
        for y in range(H):
            row = []
            for x in range(W):
                r, g, b = (int(v * 255) for v in fg[y, x])
                style = f"color:rgb({r},{g},{b})"
                if bg is not None:
                    r2, g2, b2 = (int(v * 255) for v in bg[y, x])
                    style += f";background:rgb({r2},{g2},{b2})"
                ch = chars[y, x].replace("&", "&amp;").replace("<", "&lt;")
                row.append(f'<span style="{style}">{ch}</span>')
            lines.append("".join(row))
    body = "\n".join(lines)
    if out == "html":
        import html as _html; title = _html.escape(title, quote=True)
        return (f"<title>{title}</title><style>body{{background:#0b0b0c;color:#ddd;margin:0;display:grid;place-items:center;min-height:100vh}}"
                f"pre{{font:12px/1 ui-monospace,Menlo,Consolas,monospace;letter-spacing:0;margin:0}}</style><pre>{body}</pre>")
    return body


# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("image")
    p.add_argument("--style", default="characters", choices=["characters", "dense", "block", "halfblock", "braille", "dots", "lines"])
    p.add_argument("--cols", type=int, default=80)
    p.add_argument("--cell-aspect", type=float, default=0.5, help="cell width/height; 0.5 for terminals")
    p.add_argument("--dither", default="none", choices=["none", "bayer2", "bayer4", "bayer8", "fs", "atkinson"])
    p.add_argument("--palette", default=None, choices=list(PALETTES), help="quantise colours (ansi/html output)")
    p.add_argument("--color", action="store_true", help="use source colours per cell")
    p.add_argument("--contrast", type=float, default=1.0)
    p.add_argument("--brightness", type=float, default=0.0)
    p.add_argument("--invert", action="store_true", help="dark-on-light (reverse ramp)")
    p.add_argument("--edges", action="store_true", help="Sobel edge emphasis")
    p.add_argument("--out", default="ansi", choices=["ansi", "text", "html"])
    p.add_argument("--recipe", action="store_true", help="print the recipe line to stderr")
    args = p.parse_args()
    if args.cols < 1 or not 0 < args.cell_aspect < float("inf"): p.error("cols and cell-aspect must be positive and finite")

    if args.out == "ansi" and (not sys.stdout.isatty() or "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb"):
        args.out = "text"

    fg = bg = None
    if args.style == "braille":
        lum, rgb = load_luma(args.image, args.cols, args.cell_aspect, 2, 4, args.contrast, args.brightness)
        chars = render_braille(lum, args)
        if args.color or args.palette:
            rgb_c = rgb.reshape(rgb.shape[0] // 4, 4, rgb.shape[1] // 2, 2, 3).mean((1, 3))
            fg = quantise_rgb(rgb_c, PALETTES[args.palette]) if args.palette else rgb_c
    elif args.style == "halfblock":
        lum, rgb = load_luma(args.image, args.cols, args.cell_aspect, 1, 2, args.contrast, args.brightness)   # each cell shows 2 px tall × 1 px wide in a ~1:2 cell → square sampling
        if args.palette:
            rgb = quantise_rgb(rgb, PALETTES[args.palette])
        H = rgb.shape[0] // 2
        fg, bg = rgb[0::2][:H], rgb[1::2][:H]
        chars = np.full((H, rgb.shape[1]), "▀", dtype=object)
        if args.out == "text":
            # degrade to block ramp on luma
            lum2 = lum.reshape(H, 2, -1).mean(1)
            chars = np.array(list(RAMPS["block"]))[dither(1 - lum2, args.dither, 5)]
    else:
        lum, rgb = load_luma(args.image, args.cols, args.cell_aspect, 1, 1, args.contrast, args.brightness)
        chars, rgb = render_ramp(lum, rgb, RAMPS[args.style], args)
        if args.palette:
            fg = quantise_rgb(rgb, PALETTES[args.palette])
        elif args.color:
            fg = rgb
        elif args.out == "html":
            fg = np.full(rgb.shape, 0.85, dtype=np.float32)

    sys.stdout.write(emit(chars, fg, bg, args.out, title=os.path.basename(args.image)) + "\n")
    if args.recipe:
        rec = {"style": args.style, "dither": args.dither, "palette": args.palette, "contrast": args.contrast,
               "brightness": args.brightness, "invert": args.invert, "edges": args.edges, "cols": args.cols}
        sys.stderr.write("recipe:v1:" + json.dumps({k: v for k, v in rec.items() if v not in (None, False, "none", 1.0, 0.0)}) + "\n")


if __name__ == "__main__":
    main()
