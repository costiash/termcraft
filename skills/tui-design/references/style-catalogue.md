# Style catalogue

Design vocabulary for image-to-terminal rendering. The bundled `scripts/ascii_render.py` accepts exactly these `--style` values: `characters`, `dense`, `block`, `halfblock`, `braille`, `dots`, `lines`. Resolve script paths against the tui-design skill directory to absolute paths, not cwd.

Characters (including `dense`), Block, Braille, Dots and Lines below are implemented; Halfblock is the separate `halfblock` RGB mode. Diagonal, Cross, Diamond, Mixed and Pixel Art are conceptual techniques, not CLI styles. Dither is a `--dither` option, not a style. Luminance modes use different sampling grids; halfblock ANSI/HTML instead uses RGB foreground/background pairs.

| # | Style | Mechanism | Glyphs / primitives | Reads as | Best for |
|---|---|---|---|---|---|
| 1 | **Characters** | ramp index from luminance | `@#S08Xx+=-;:,.` (dark→light); alt dense ramp: `$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,"^`'. ` | typewriter ASCII | READMEs, banners, copy-pastable output |
| 2 | **Block** | ramp over block glyphs | `█▓▒░ ` plus `▀▄▌▐` for 2× vertical detail (foreground/background colours per half) | terminal pixel grid | dashboards, dense logos, truecolor terminals |
| — | **Braille** | 2×4 sub-cell threshold → dot bits | U+2800–U+28FF | halftone at 2× resolution | sparklines, plots, high-detail monochrome |
| 3 | **Dots** | circle radius ∝ luminance | `·∙•●` in text; filled circles on canvas | halftone print | posters, editorial dividers |
| 4 | **Lines** | vertical stroke weight ∝ luminance | `\| ¦ ║ │ ┃` | rain / barcode / VHS static | backgrounds, loading states |
| 5 | **Diagonal** | slash density | `/ \ ╱ ╲ ╳` | cross-hatch drawing | illustration feel |
| 6 | **Cross** | cross size/weight | `+ × ✕ ✚` | stitched grid | tech / blueprint |
| 7 | **Diamond** | diamond size ∝ luminance | `◇ ◆ ⬖ ⬗` | jewel-like | accents only |
| 8 | **Mixed** | stable hash per cell picks a family | any of the above | organic texture | large hero fills |
| 9 | **Pixel Art** | quantised colour squares | none (colour cells) | 8-bit | icons, avatars, pixelation/redaction |
| 14 | **Dither** | error diffusion / ordered threshold to a small palette | see `dither.md` | retro console / riso | nostalgia, print, GIF loops |

## Choosing

- Text must be copy-pastable (README, Discord, commit banner) → `characters` or `block`.
- Terminal, monochrome, maximum detail → `braille`.
- Terminal with truecolor → `halfblock` using `▀` with fg/bg pairs (two vertical pixels per cell).
- Privacy redaction → remove or fully cover sensitive content; neither pixelation nor blur guarantees it cannot be recovered.
- Diamond, Cross: conceptual accents and dividers, never body surfaces.

## Halfblock limitations

ANSI/HTML halfblock output quantizes RGB with `--palette` when supplied. It does **not** apply `--dither`, `--brightness`, `--contrast`, `--invert` or edge emphasis to RGB output, even though those options are accepted and may appear in recipe metadata. `--out text` falls back to luminance block glyphs rather than preserving RGB halfblocks; brightness, contrast and dither affect that fallback, but invert is not applied there. Do not advertise ignored flags as visible effects.

## Cell geometry

- Terminal / monospace: cell aspect ≈ 1:2. Sample source blocks of `(cw, 2·cw)` pixels.
- Braille: each cell = 2 columns × 4 rows of sub-pixels; dot bit order (col,row): (0,0)=1 (0,1)=2 (0,2)=4 (1,0)=8 (1,1)=16 (1,2)=32 (0,3)=64 (1,3)=128. Codepoint = 0x2800 + bits.
- Half-block: cell = 1 column × 2 rows; glyph `▀` with fg = top colour, bg = bottom colour.

## Edge emphasis

For ramp styles (`characters`, `dense`, `block`, `dots`, `lines`), `--edges` overlays Sobel strokes above magnitude 0.25: gradient angles near 0°/180°→`|`, 45°→`\`, 90°→`-`, 135°→`/`. Braille and halfblock do not use this overlay.

## Mixed hash (conceptual, not implemented)

`h = (x * 73856093 ^ y * 19349663) & 0xffff; family = h % 4`. Stable across frames so animation doesn't shimmer; change the constants to get a different but still stable texture.
