# CLI / TUI surfaces

## Grid

- Design on 80×24 first, enhance at ≥120 columns. Read `shutil.get_terminal_size()` (Python) / `process.stdout.columns` (Node) at start and on `SIGWINCH`; re-layout, don't crop.
- Box drawing weights — one per screen, heavy reserved for the focused panel:
  - light `┌ ─ ┐ │ └ ┘ ├ ┤ ┬ ┴ ┼`
  - rounded `╭ ─ ╮ │ ╰ ╯`
  - heavy `┏ ━ ┓ ┃ ┗ ┛`
  - double `╔ ═ ╗ ║ ╚ ╝`
- Hierarchy by density: title in Block glyphs or a FIGlet font, section rules `─`, body plain. Colour is the last lever.
- Meters: `█▓▒░` ramp or `━╺` with a bright head. Sparklines: `▁▂▃▄▅▆▇█`. Braille sparklines get 2× horizontal resolution.
- Spinners: Braille `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` (80 ms), Block `▖▘▝▗`, Lines `|/-\`.
- Never use emoji as structure; width is unpredictable across terminals. Stick to Block, Braille, box drawing, and the ASCII ramp.

## Theme

Every surface uses one theme from `tui-themes.md` (`scripts/themes.py`): six colour roles for dark *and* light backgrounds, one box weight, one glyph set, one banner style. `make_theme.py` writes `theme.py`; the kit's `UI(theme=…)` applies it and handles `NO_COLOR`, 16-colour terminals, light backgrounds (`COLORFGBG`/`HARNESS_BG`) and non-UTF terminals (`HARNESS_ASCII`). Never hand-pick hex values on a surface; pick a theme and override at most the accent.

## Colour

Capability ladder, checked once at startup:

1. `NO_COLOR` set or not a TTY → monochrome.
2. `COLORTERM` in `truecolor|24bit` → 24-bit: `\x1b[38;2;R;G;Bm` (fg), `\x1b[48;2;R;G;Bm` (bg).
3. `TERM` contains `256color` → `\x1b[38;5;Nm`; map RGB to the 6×6×6 cube: `16 + 36·r + 6·g + b` with r,g,b in 0–5; greys 232–255.
4. Otherwise 16 colours.

Reset `\x1b[0m` after each run of colour, dim `\x1b[2m`, bold `\x1b[1m`. Batch cells with the same colour into one escape sequence; escape-per-cell doubles output size.

Palettes: take them from `dither.md` (Game Boy, C64, CGA, amber, green phosphor). A TUI with a 4-colour palette looks designed; a TUI with 40 colours looks like a log file.

Post-FX in the terminal reduce to: Vignette (dim toward edges), Scan Lines (dim alternate rows), Color Overlay (multiply the palette), Bloom (bold above threshold). Chromatic/RGB Split is a splash-screen trick only.

## Rendering images

Resolve `scripts/...` and tool basenames against the loaded tui-design skill directory to absolute paths before execution; reference files do not set a shell plugin-root variable. Post-FX above are conceptual techniques, not bundled renderer switches.

- Monochrome, max detail → Braille (`scripts/ascii_render.py --style braille`). Banners for names: `scripts/banner.py` (built-in block font).
- Truecolor → half-block: `▀` with fg = upper pixel, bg = lower pixel; two vertical pixels per cell, square-ish result.
- Copy-pastable → Characters with the default ramp; output width ≤ 80 so it survives a README code block.

## Animation

See `animation.md` for implemented behavior and limitations. These are integration requirements, not unconditional guarantees of `tui_frame.run`; the runner gates `NO_COLOR`, supports `animate=False`, and restores state on errors; callers must gate prompts. Mechanics:

- Enter: hide cursor `\x1b[?25l`, optionally alternate screen `\x1b[?1049h`.
- Frame: home `\x1b[H`, write only changed cells (`scripts/tui_frame.py` diff), flush once.
- Exit (normal, exception, SIGINT): show cursor `\x1b[?25h`, leave alt screen `\x1b[?1049l`, reset `\x1b[0m`. Register with `atexit` and a signal handler; a terminal left in a broken state is the one thing users remember.

## Libraries

Emit raw ANSI when the project has no TUI dependency (the bundled `tui_frame.py` is enough for banners, dashboards and splash screens). Otherwise match what's installed: Python `rich` / `textual` / `blessed`; Node `ink` / `blessed` / `chalk`; Go `bubbletea` + `lipgloss`; Rust `ratatui`. Don't add a framework for a banner.

## Checklist

- [ ] Looks intentional at 80 columns, not cropped
- [ ] `NO_COLOR=1` and piped output (`| cat`) both produce sane text
- [ ] Cursor visible and colours reset after Ctrl-C
- [ ] Glyphs limited to Block / Braille / box drawing / ASCII
- [ ] ≤ 4 palette colours on interactive screens; animation only on non-interactive surfaces
- [ ] Theme id and recipe line noted in `HARNESS.md` / `--help` epilogue; previews rendered dark, light and `--ascii`
