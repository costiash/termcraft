# Voxel Grove

Voxel / pixel-art / block inspiration, informed by [ASCII Magic’s styles](https://www.ascii-magic.com/styles) and the supplied `Context.md`. Original artwork generated with built-in imagegen; no gallery image was copied.

![Voxel Grove source](source.png)

The source image contains the voxel geometry. Termcraft samples that image; it does not construct 3D cubes. Prefer the CGA halfblock sample for color separation. ASCII and Lines deliberately expose the loss of dark trunk/underside detail; they are fallback and texture references, not equivalent visual reproductions.

## Files and reproduction

Run from the plugin root with Python + Pillow + numpy. Pre-rendered text/ANSI files need no image dependencies.

**[characters-40.txt](characters-40.txt) — 40×12 cells.**

```sh
python3 skills/tui-design/scripts/ascii_render.py skills/tui-design/assets/voxel-grove/source.png --style characters --cols 40 --invert --contrast 1.2 --brightness 0.05 --out text
```

**[lines-40.txt](lines-40.txt) — 40×12 cells.**

```sh
python3 skills/tui-design/scripts/ascii_render.py skills/tui-design/assets/voxel-grove/source.png --style lines --cols 40 --invert --contrast 1.2 --brightness 0.05 --out text
```

**[braille-80.txt](braille-80.txt) — 80×24 cells.**

```sh
python3 skills/tui-design/scripts/ascii_render.py skills/tui-design/assets/voxel-grove/source.png --style braille --cols 80 --invert --contrast 1.2 --brightness 0.05 --dither fs --out text
```

**[halfblock-40.ansi](halfblock-40.ansi) — 40×12 cells.**

```sh
python3 skills/tui-design/scripts/ascii_render.py skills/tui-design/assets/voxel-grove/source.png --style halfblock --cols 40 --palette cga --out ansi
```

The 40×12 variants are compact splash candidates. The 80×24 Braille file is a full-screen/detail reference: do not place it above an interactive plan. Width counts assume a font with single-cell glyphs.

ANSI color output requires a compatible TTY with `NO_COLOR` unset. Redirection automatically degrades to text; the shipped ANSI file was captured through a PTY. Use a text variant for pipes and no-color environments. Palette and shading choices are examples, not default product branding.

[Exact image-generation prompt](prompt.txt) · [Recipes, dimensions and hashes](manifest.json). The original PNG is retained unchanged; character output comes from the actual bundled renderer. Generation is stochastic; the saved image is the reproducible conversion input.
