# Nautilus

Dots / halftone / organic-detail inspiration, informed by [ASCII Magic’s styles](https://www.ascii-magic.com/styles) and the supplied `Context.md`. Original artwork generated with built-in imagegen; no gallery image was copied.

![Nautilus source](source.png)

Use dark glyphs on a light background. The dots output uses Unicode glyphs of different visual weights, not ASCII Magic’s variable-radius canvas circles. Braille at 80 columns retains much more of the shell’s chambers than the compact ASCII sample. This is an artistic shell study, not an anatomical reference.

## Files and reproduction

Run from the plugin root with Python + Pillow + numpy. Pre-rendered text/ANSI files need no image dependencies.

**[characters-40.txt](characters-40.txt) — 40×12 cells.**

```sh
python3 skills/tui-design/scripts/ascii_render.py skills/tui-design/assets/nautilus/source.png --style characters --cols 40 --contrast 1.5 --brightness 0.08 --out text
```

**[dots-bayer-40.txt](dots-bayer-40.txt) — 40×12 cells.**

```sh
python3 skills/tui-design/scripts/ascii_render.py skills/tui-design/assets/nautilus/source.png --style dots --dither bayer4 --cols 40 --contrast 1.5 --brightness 0.08 --out text
```

**[braille-80.txt](braille-80.txt) — 80×24 cells.**

```sh
python3 skills/tui-design/scripts/ascii_render.py skills/tui-design/assets/nautilus/source.png --style braille --cols 80 --contrast 1.5 --brightness 0.08 --dither fs --out text
```

**[halfblock-40.ansi](halfblock-40.ansi) — 40×12 cells.**

```sh
python3 skills/tui-design/scripts/ascii_render.py skills/tui-design/assets/nautilus/source.png --style halfblock --cols 40 --color --out ansi
```

The 40×12 variants are compact splash candidates. The 80×24 Braille file is a full-screen/detail reference: do not place it above an interactive plan. Width counts assume a font with single-cell glyphs.

ANSI color output requires a compatible TTY with `NO_COLOR` unset. Redirection automatically degrades to text; the shipped ANSI file was captured through a PTY. Use a text variant for pipes and no-color environments. Palette and shading choices are examples, not default product branding.

[Exact image-generation prompt](prompt.txt) · [Recipes, dimensions and hashes](manifest.json). The original PNG is retained unchanged; character output comes from the actual bundled renderer. Generation is stochastic; the saved image is the reproducible conversion input.
