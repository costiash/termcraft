---
name: tui-design
description: Design terminal interfaces that look like one deliberate thing — CLI/TUI surfaces for harnesses, installers, dashboards, splash screens and banners — from a theme bank (Terminal noir, Blueprint, Green/Amber phosphor, Paper for light terminals, Cyber, Slate, Mono) with light/dark palettes, 16-colour and ASCII fallbacks, a built-in block-letter banner font, glyph sets (spinners, meters, marks, box weights), image→glyph rendering (Characters/Block/Braille/halfblock, dithering, palettes) and a preview tool that renders the real screens per theme so a person can pick. Use whenever a CLI, TUI, terminal program, installer or harness needs a look, a banner, a colour scheme, a splash, ASCII/retro/CRT/text-mode styling, or an existing terminal UI should be restyled — even if the user never says "ASCII".
---

# tui-design

A terminal surface reads as designed when four things agree: **one theme** (six colour roles with a light-background twin), **one box weight**, **one glyph set** (spinner, meter, marks) and **one banner style** — and when all of it still reads with `NO_COLOR`, in a pipe, on a light terminal and in a non-UTF terminal. This skill provides the bank, the tools and the rules; the `tui-designer` agent applies them.

## Bundled resources

| Path | Read / run when |
|---|---|
| `references/tui-themes.md` | choosing a theme: the bank, the picking rule (show three, render mono/ascii/light), how to generate `theme.py`, glyph sets, adding a theme |
| `references/cli-mode.md` | building any terminal surface: grid, theme, colour ladder, images, animation, libraries, checklist |
| `references/style-catalogue.md` | rendering an image/logo to glyphs: styles, glyph sets, cell geometry, edge emphasis |
| `references/dither.md` | limited-palette / retro rendering: kernels, Bayer matrices, palette hex, terminal notes |
| `references/recipes.md` | surface recipes (→ themes) and render recipes for `ascii_render.py` |
| `references/animation.md` | the little motion a terminal surface may have (Reveal, progress) and its mechanics |
| `assets/README.md` | four optional source-art sets and 15 real terminal conversions: amber terminal, retro lunar relay, organic Nautilus and colorful voxel grove; exact prompts/recipes, polarity guidance and detail-loss notes; never apply as default branding |
| `scripts/themes.py` | the theme bank (importable data); `python3 "${CLAUDE_PLUGIN_ROOT}/skills/tui-design/scripts/themes.py"` lists, `themes.py <id>` dumps |
| `scripts/preview_theme.py` | render the harness screens per theme: `--name PB --theme noir slate mono --out previews/`, `--bg light`, `--ascii`, `--cols 80` |
| `scripts/make_theme.py` | write a self-contained `theme.py`: `--theme noir --name PB --out theme.py` (`--banner`, `--accent` overrides) |
| `scripts/banner.py` | block-letter banners without FIGlet: `block` (ANSI shadow), `slab`, `shade`, `plain`; ASCII fallback; `--fit` |
| `scripts/ascii_render.py` | image → Characters/Block/Braille/halfblock/dots/lines, dither, palettes, ANSI/text/HTML output |
| `scripts/tui_frame.py` | dependency-free widgets: diff-redraw `Frame`, `box`, `meter`, `sparkline`, `Spinner`, `reveal`, `table`, `kv`, `badge`, `columns`, `tree`, `tabs`, `wrap`, terminal hygiene |
| `scripts/test_tools.py` | regression tests for the renderer and the pty driver |

Paths above are relative to this skill's directory (`${CLAUDE_PLUGIN_ROOT}/skills/tui-design/`). Resolve them to absolute paths when running; a reference file does not export `CLAUDE_PLUGIN_ROOT`.

## Workflow

1. **Recon the product, not the taste.** What the tool does, who runs it, on what terminal (dark/light, truecolor/16, UTF/ASCII, CI pipes), brand colour if any. The mood decides the theme family (`tui-themes.md` §Picking).
2. **Show three candidates.** `python3 "${CLAUDE_PLUGIN_ROOT}/skills/tui-design/scripts/preview_theme.py" --name <NAME> --theme a b c --out previews/` — real screens (plan, invariants, prompt, progress, outcome) at the operator's width. Also render `mono` and `--ascii`; also `--bg light` if there is any chance of a light terminal. Let the person choose: running as a subagent, return the candidate previews and rationales to the parent for user selection instead of asking directly, then resume with the choice.
3. **Generate `theme.py`** with `python3 "${CLAUDE_PLUGIN_ROOT}/skills/tui-design/scripts/make_theme.py"`; override at most the accent (brand colour). Use the optional import pattern in `${CLAUDE_PLUGIN_ROOT}/skills/cli-harness/references/harness-design.md`, then wire `UI(name, banner=BANNER, theme=THEME)`.
4. **Banner** from `python3 "${CLAUDE_PLUGIN_ROOT}/skills/tui-design/scripts/banner.py"` — ≤ 80 columns, ≤ 6 lines, header only. Logos/images via `python3 "${CLAUDE_PLUGIN_ROOT}/skills/tui-design/scripts/ascii_render.py"` at ≤ 12 rows.
5. **Verify** with the harness's pty scenarios (`python3 "${CLAUDE_PLUGIN_ROOT}/skills/cli-harness/scripts/drive_harness.py"`): 80 columns, `NO_COLOR=1`, `| cat`, `HARNESS_ASCII=1`, `HARNESS_BG=light`; read the transcripts. A theme that breaks a scenario is not applied.
6. **Record** the theme id and its recipe line in `HARNESS.md`.

## Rules

- One theme, one box weight, one glyph set, one banner style per program. ≤ 4 colours on any interactive screen (the six roles are a budget, not a requirement).
- Both palettes are mandatory: never ship a theme that is unreadable on a light terminal — pick `paper` before hand-tuning.
- No animation while a prompt is open; no motion in pipes.
- Glyphs from Block Elements, Braille, box drawing and ASCII only; emoji is never structure.
- The look never carries behaviour: deleting `theme.py` must leave a working, plain harness.
