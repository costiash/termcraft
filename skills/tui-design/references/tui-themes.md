# TUI themes — the bank, how to pick, how to extend

A terminal theme is six colour roles, one box weight, a glyph set and a banner style — and a second palette for light backgrounds, because operators may use light terminals and "dark by default" is how amber text ends up invisible on white.

## The bank (`scripts/themes.py`)

| id | name | mood | box | banner | notes |
|---|---|---|---|---|---|
| `noir` | Terminal noir | operator consoles; ops, data, finance | light | block | sepia ink, one amber accent — the default for harnesses |
| `blueprint` | Blueprint | architecture / infra tooling | light | shade | ice on navy, cross glyphs `╬╪┼` in meters |
| `phosphor` | Green phosphor | retro terminals, monitoring | light | block | P1 green; Braille spinner `⡀⡄⡆⡇…` |
| `amber` | Amber phosphor | night use, long sessions | light | block | warmer sibling of phosphor |
| `paper` | Paper | **light terminals**, printouts | rounded | slab | ink-on-paper; `◐◓◑◒` spinner, `■▣▢·` meter |
| `cyber` | Cyber | dev tools with an edge | heavy | block | magenta/cyan; use sparingly, never for finance |
| `slate` | Slate | neutral, corporate-safe | rounded | slab | the choice when nothing is justified |
| `mono` | Mono | no colour by design | double | shade | `[x] [ ] [!]` marks; what `NO_COLOR` users see anyway |

Every theme carries: `palette` (dark bg), `light` (light bg), `ansi16` (per-role 16-colour fallback for terminals without truecolor), `glyphs` (spinner, meter ramp, marks, rule, bullet) and an `ascii_fallback` glyph set for non-UTF terminals.

## Picking (the tui-designer's rule)

1. **Mood from the product**, never from taste: ops/data/finance → noir or slate; infra/architecture → blueprint; dev tool → phosphor/amber, cyber only if the product already has that voice; anything printed or read on light terminals → paper.
2. **Show three, not one.** `preview_theme.py --name <NAME> --theme a b c --out previews/` renders the plan, invariants, question and progress screens per theme at the operator's column width. The person picks; the designer doesn't.
3. **Always render the `mono` and `--ascii` variants** of the chosen theme too — that is what CI logs, `NO_COLOR` users and `TERM=dumb` sessions get, and it must still read.
4. **Light check**: `--bg light`. If the theme's light palette is unreadable on the operator's terminal, switch to `paper` rather than tuning colours by eye.

## Generating `theme.py`

Resolve `scripts/...` and script basenames here against the loaded tui-design skill directory to absolute paths before execution, not cwd. Reference files do not export `CLAUDE_PLUGIN_ROOT`; output paths belong in the target project. When running as a subagent, return candidates to the parent for user choice and resume with that choice. Use the optional import pattern in the sibling cli-harness skill's `references/harness-design.md`, so a missing `theme.py` remains supported.

```
python3 scripts/make_theme.py --theme noir --name PB --out ./theme.py
python3 scripts/make_theme.py --theme slate --name acme --banner shade --accent "#7fb2e0" --out ./theme.py
```

The file is self-contained (no plugin import at runtime) and exposes `THEME` (roles(bg), glyphs, box, banner, ansi16), `BANNER`, `BANNER_ASCII`, plus the legacy `PALETTE`/`BOX`. The harness does `UI(name, banner=BANNER, theme=THEME)`; the kit picks the light palette when `COLORFGBG` or `HARNESS_BG=light` says so, and the ASCII glyph set when stdout isn't UTF-8 or `HARNESS_ASCII=1`.

## Banners (`scripts/banner.py`)

Built-in 5×5 cap font, doubled cells, no FIGlet. Styles: `block` (ANSI-shadow `█╗╝`), `slab` (solid), `shade` (`▒` fill, half the weight — light terminals, Mono), `plain`. ≤ 80 columns or `fit()` falls back to plain text; ≈ 7 letters max in block. Banners are for the header only; never inside a panel or beside a prompt.

## Glyph sets and where each goes

| Element | Default | Alternatives (by theme) | ASCII |
|---|---|---|---|
| spinner | `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` | `⡀⡄⡆⡇⣇⣧⣷⣿` (phosphor) · `◐◓◑◒` (paper) · `▁▂▃▄▅▆▇█` (cyber) | `\|/-\` |
| meter | `█▓▒░` | `╬╪┼·` (blueprint) · `■▣▢·` (paper) · `█▉▊▋` (cyber) | `#=-.` |
| marks | `✓ • ✗ ? … ·` | `[x] [ ] [!] [?] [~] [-]` (mono) | `+ * x ? ~ -` |
| box | rounded `╭╮╰╯` | light `┌┐└┘` · heavy `┏┓┗┛` · double `╔╗╚╝` | `+-+|` |
| sparkline | `▁▂▃▄▅▆▇█` | Braille for 2× resolution | `_.-=^` |

One box weight per screen; heavy only for the focused panel. Never emoji as structure.

## Adding a theme

Add a `_t(...)` entry in `themes.py` with all six roles in both palettes, run `preview_theme.py --theme <id>` dark, light and `--ascii`, and add the row above. Contrast: ink vs ground ≥ 7:1, dim ≥ 3:1, accent ≥ 4.5:1 on the background it is meant for.

Saved previews include `.ansi` color candidates and `.txt` plain counterparts. `NO_COLOR` removes colors from the selected theme; it does not switch its glyphs to the `mono` theme. The ASCII variant is a separate capability check. Recipe `fx` fields describe inspiration, not effects executed by the runtime.
