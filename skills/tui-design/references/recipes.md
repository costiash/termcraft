# Recipes

Two kinds now: **surface recipes** (a whole TUI look — these are the themes in `scripts/themes.py`, see `tui-themes.md`) and **render recipes** (how `ascii_render.py` turns an image or logo into glyphs for a banner, splash or README).

## Surface recipes → themes

`noir` · `blueprint` · `phosphor` · `amber` · `paper` · `cyber` · `slate` · `mono`. Pick per `tui-themes.md`; generate with `make_theme.py`; record the theme's `recipe` line in `HARNESS.md`.

## Render recipes (`ascii_render.py`)

| Name | Command | Use |
|---|---|---|
| **README classic** | `--style characters --cols 80 --out text` | copy-pastable art for READMEs, Discord, commit banners |
| **Braille mono** | `--style braille --cols 120 --dither bayer4` | highest detail in a monochrome terminal; logos, portraits |
| **Truecolor logo** | `--style halfblock --color --cols 40` | a logo in a truecolor terminal splash (two vertical pixels per cell) |
| **Game Boy** | `--style halfblock --palette gameboy --cols 40` | nostalgia splash; RGB quantization to 4 greens, no dithering |
| **Phosphor** | `--style characters --palette phosphor --cols 60 --contrast 1.3` | matches the phosphor/amber themes |
| **Blueprint** | `--style characters --edges --contrast 1.4 --out text` | edge-emphasised line art for architecture tools |
| **Poster (printout)** | `--style dots --invert --cols 100 --out text` | ink-on-paper halftone for light terminals and printing |

The command column contains arguments for `scripts/ascii_render.py`; resolve that script against the loaded tui-design skill directory to an absolute path. Other script basenames here use that same `scripts/` directory, never cwd. Every render must fit the terminal (`--cols` ≤ width, height ≤ rows − 10 so the plan still fits below it) and degrade to `--out text` for pipes. Halfblock ANSI/HTML ignores brightness, contrast, invert, dither and edges; its text fallback is luminance blocks, not RGB halfblocks (see `style-catalogue.md`).

## Tuning order

1. `--cols` (detail vs. space left for the UI) 2. `--contrast`, then `--brightness` — make it read in 1-bit first 3. style 4. palette/dither 5. `--edges` if silhouettes matter.

## Anti-recipes

- A rendered image taller than 12 rows above an interactive plan — the plan scrolls off.
- Rainbow per-cell colour on an interactive surface.
- More than one box weight, more than four colours, any glyph outside Block/Braille/box-drawing/ASCII.

## Bundled source-and-output examples

See `../assets/README.md` for four art sets with exact prompts, real renderer outputs, recipes and hashes. Lunar Relay explores Atkinson blocks and the Game Boy color palette; Nautilus explores light-background dots/Braille; Voxel Grove explores CGA halfblocks and the limitations of grayscale Lines. The voxel shape belongs to its source artwork, not a new renderer style.
