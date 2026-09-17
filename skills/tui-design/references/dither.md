# Dither

Dithering maps a continuous luminance/colour grid to a small palette while preserving the impression of tone. Two families: **error diffusion** (organic, film-like) and **ordered** (regular pattern, animatable, deterministic per pixel — cheap on GPU and in terminals).

## Algorithms

### Error diffusion (process left→right, top→bottom; push quantisation error to unprocessed neighbours)

Kernels as (dx, dy, weight), divisor shown:

| Name | Kernel | Character |
|---|---|---|
| Floyd–Steinberg | /16: (1,0,7) (-1,1,3) (0,1,5) (1,1,1) | the default; fine grain |
| Atkinson | /8: (1,0,1) (2,0,1) (-1,1,1) (0,1,1) (1,1,1) (0,2,1) — only 6/8 of error propagated | high contrast, Mac-classic look, crushes midtones on purpose |
| Stucki | /42: row0 (1,0,8)(2,0,4); row1 (-2,1,2)(-1,1,4)(0,1,8)(1,1,4)(2,1,2); row2 (-2,2,1)(-1,2,2)(0,2,4)(1,2,2)(2,2,1) | smooth, clean |
| Burkes | /32: row0 (1,0,8)(2,0,4); row1 (-2,1,2)(-1,1,4)(0,1,8)(1,1,4)(2,1,2) | Stucki without row 2; faster |
| Sierra Lite | /4: (1,0,2) (-1,1,1) (0,1,1) | very fast, slightly noisy |

Use serpentine scanning (alternate direction per row) to avoid diagonal worm artefacts.

### Ordered

Threshold matrix `M` of size n×n, normalised to (M+0.5)/n². Output = palette-quantise(lum + (M[y%n][x%n] − 0.5) · spread), spread ≈ 1/(palette levels − 1).

Bayer 2×2:
```
0 2
3 1
```
Bayer 4×4:
```
 0  8  2 10
12  4 14  6
 3 11  1  9
15  7 13  5
```
Bayer 8×8 and 16×16: recursive — `B(2n) = [[4B(n), 4B(n)+2],[4B(n)+3, 4B(n)+1]]`.

- **Halftone**: threshold = distance from cell centre (dot grows with darkness); rotate the grid 45° for print feel.
- **Blue noise**: precomputed 64×64 tile (generate once with void-and-cluster, or ship a PNG); no visible pattern, best for large smooth areas.

### Picking

- Nostalgia / handheld → Bayer 4×4 or Atkinson.
- Print / 1-bit posters → Atkinson.
- Smooth photos → Floyd–Steinberg or Stucki.
- Anything animated (Animate Matrix, terminal) → ordered only; error diffusion shimmers frame to frame.
- Large flat gradients → blue noise.

## Palettes (hex, dark→light where meaningful)

| Name | Colours |
|---|---|
| 1-bit | `#000000 #ffffff` |
| Game Boy | `#0f380f #306230 #8bac0f #9bbc0f` |
| Game Boy Pocket | `#000000 #555555 #aaaaaa #ffffff` |
| Commodore 64 | `#000000 #ffffff #880000 #aaffee #cc44cc #00cc55 #0000aa #eeee77 #dd8855 #664400 #ff7777 #333333 #777777 #aaff66 #0088ff #bbbbbb` |
| NES (subset) | `#000000 #fcfcfc #f8f8f8 #bcbcbc #7c7c7c #a4e4fc #3cbcfc #0078f8 #0000fc #b8b8f8 #6888fc #0058f8 #0000bc #d8b8f8 #9878f8 #6844fc` |
| PICO-8 | `#000000 #1d2b53 #7e2553 #008751 #ab5236 #5f574f #c2c3c7 #fff1e8 #ff004d #ffa300 #ffec27 #00e436 #29adff #83769c #ff77a8 #ffccaa` |
| CGA (palette 1, high) | `#000000 #55ffff #ff55ff #ffffff` |
| CGA (palette 0) | `#000000 #55ff55 #ff5555 #ffff55` |
| Risograph | `#0078bf #ff48b0 #ffe800 #ffffff` (blue, fluorescent pink, yellow; overprint via multiply) |
| Sepia | `#2b1d0e #6b4a2b #b08a5a #efe0c4` |
| Pastel | `#2d2a32 #f4a6c1 #a6d8f4 #f4e1a6 #c1f4a6 #fdfdfd` |
| Amber terminal | `#1a0f00 #ffb000` |
| Green phosphor | `#001a00 #33ff33` |

Quantise in linear RGB or Lab for colour palettes; plain sRGB distance is fine for monochrome ramps.

## Animate Matrix (conceptual; not a bundled CLI feature)

Dither-only animation: shift the ordered matrix offset by one cell per tick in a direction (`x0 += 1` for scroll-right). Because only the threshold pattern moves, the image stays put and shimmers. Loop length = matrix size (4 frames for Bayer 4×4), so GIF exports are tiny. Do not combine with error diffusion.

## Terminal note

A custom colour pipeline can dither before encoding `▀` foreground/background pairs. The bundled renderer does not: `--style halfblock` ANSI/HTML quantizes RGB without applying `--dither`. Use luminance modes such as Braille for implemented dithering. Ordered dithers suit cell resolution; for error diffusion, raise sample resolution (Braille) before judging detail at 80 columns.
