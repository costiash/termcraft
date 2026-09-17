# Terminal study — optional sample asset

A generated vintage-terminal illustration, supplied as a source image and three real renderer outputs. Use it for renderer experiments, documentation, or an optional splash. It is not a logo, a default harness dependency, or evidence of a working UI. Keep it out of interactive plans if its 12 rows would push required information offscreen.

![Source illustration](source.png)

| File | Use |
|---|---|
| `source.png` | Original AI-generated RGB illustration, 1619×971 pixels. |
| `characters-40.txt` | 40×12 ASCII cells; portable silhouette, limited screen detail. |
| `braille-40.txt` | 40×12 Unicode cells; preserves the waveform better; requires a suitable font. |
| `halfblock-40.ansi` | 40×12 truecolor cells, with foreground/background ANSI escapes. |
| `prompt.txt` | Exact source-generation prompt; built-in imagegen mode. |
| `manifest.json` | Verified dimensions and SHA-256 hashes. |

## Reproduce the text variants

Run from the plugin root with a Python environment containing Pillow and numpy:

```sh
python3 skills/tui-design/scripts/ascii_render.py skills/tui-design/assets/terminal-study/source.png --style characters --cols 40 --invert --contrast 1.6 --brightness -0.06 --out text
python3 skills/tui-design/scripts/ascii_render.py skills/tui-design/assets/terminal-study/source.png --style braille --cols 40 --invert --contrast 1.6 --brightness -0.06 --dither fs --out text
```

These variants are tuned for bright glyphs on a dark terminal. For dark glyphs on a light terminal, start by omitting `--invert`, then inspect the result. The grayscale shapes and detailed waveform will not survive every size equally well.

For a live truecolor terminal:

```sh
python3 skills/tui-design/scripts/ascii_render.py skills/tui-design/assets/terminal-study/source.png --style halfblock --cols 40 --color --out ansi
```

The renderer intentionally degrades to text when stdout is redirected or `NO_COLOR` is set; `> example.ansi` does not force color. The bundled `.ansi` file was captured from a real PTY. Display it with `cat` only when color is wanted and supported. For pipes or `NO_COLOR`, use one of the `.txt` files instead. Pre-rendered files need no Pillow/numpy dependency.

Source generated using the built-in `image_gen` tool. The original output was copied unchanged into the plugin. All character conversions were produced by the bundled renderer, not by the image model. Source generation is stochastic; the saved prompt records intent, while the PNG and checksums identify the actual selected artifact.
