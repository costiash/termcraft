# Motion in the terminal

Motion is for splash screens and progress, not text being read. **No animation while a prompt is open**, in pipes, or under `NO_COLOR`: these are caller-enforced design rules, not automatic runner guarantees.

## What is allowed

| Where | What | Implementation |
|---|---|---|
| splash / banner | one **Reveal** in reading order, stable endpoint, ≤ 1.5 s | `tui_frame.reveal(lines, progress)` with `tui_frame.run(loop, fps=30, duration=1.5)`; caller supplies endpoint handling |
| progress | elapsed/estimated progress | `harness_kit.UI.progress`: plain TTY spinner/meter, optional Rich bar; caller drives updates, not measured work completion |
| idle dashboards (no prompt) | sparkline updates, spinner | `tui_frame.sparkline`, `Spinner` |
| transitions | at most one L→R cascade over a panel | caller schedules `reveal` per line; no separate Cascade API |

No Wave/Pulse over readable text, glitch effects, or redraw during `input()`/`getpass()`.

## Bundled runner and caller obligations

Resolve `scripts/tui_frame.py` against the tui-design skill directory to an absolute path, not cwd; `harness_kit.py` is in the sibling cli-harness skill's `scripts/` directory.

- `run` validates 0 < fps ≤ 30, paces with `perf_counter`, and reconstructs the frame at terminal resize. The callback must relayout for its current dimensions. Cells remain codepoints, not graphemes: use single-cell glyphs.
- Animated TTY runs enter the alternate screen. A `finally` block restores the cursor/screen and previous SIGINT/SIGTERM handlers on normal completion, interruption and callback errors. SIGKILL cannot be cleaned up.
- Non-TTY, `NO_COLOR` (even empty), `TERM=dumb`, or `animate=False` calls the callback once at `duration or 0`, prints the static frame, and uses no alternate screen. Supply a duration that represents the final state for splashes. The demo exposes `--no-animation`.
- Timed animation calls the callback at its exact endpoint before leaving the alternate screen. Callers decide whether to print a persistent final result afterwards. Prompt awareness is still caller-controlled: never invoke animation while input is open.

## Reveal

The caller maps elapsed time to progress 0→1 and supplies easing if desired. The helper reveals `int(progress * total)` characters; the last `len(crest)` revealed positions use the crest (`░▒▓` by default), not the last 5%. At `progress ≥ 1` it returns the original lines without a crest. Crest brightness is up to the renderer.
