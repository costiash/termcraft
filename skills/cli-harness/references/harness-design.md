# Harness design — the UX contract and the TUI layer

A harness is judged by what the person does *not* have to know. Every screen answers: where am I, what will happen, what will never happen, what do you need from me, how long, and — when it fails — what do I do now.

## Screens

1. **Header**: banner (from the theme), harness name/version, project root.
2. **Plan**: one line per stage — mark (✓ • ✗ ?), title, status, detail, fix. Done stages are shown, not hidden: the person sees the whole machine.
3. **Invariants panel**: "what never happens" for the stages about to run.
4. **Questions**: only what probes could not answer; secrets via hidden input; validation inline with the project's own bounds text.
5. **Confirmation**: one `proceed? [Y/n]`.
6. **Progress**: per-stage elapsed/estimated progress (plain TTY spinner/meter or optional Rich bar); callers drive updates. Estimates are not measured work completion. Stream only sanitized project output; suppress sensitive child output.
7. **Outcome**: `✓ all stages done` or `✗ <stage> failed: <cause>` + `rerun to resume` + journal path.

## Rules

- **Probe before ask.** Read known values from the project's configuration or environment in probes. The kit does not persist answers in the journal; resume re-probes real state and resolves inputs again.
- **Ask once.** All questions before execution, never mid-run.
- **Say the never.** Name destructive or external actions in the plan and require confirmation; `never` lists state forbidden actions, not permissions to perform them.
- **Fail forward.** One line: stage · cause · fix. Rerun re-probes. The journal records stage transitions and outcome details, not persisted answers or tracebacks; arrange separate sanitized diagnostics if needed.
- **Secrets**: hidden input; declare `Question(secret=True)` so the kit can redact known values in its own messages, journal details and dry-run descriptions. Child stdout/stderr from `ctx.sh` and direct `print` calls are not automatically redacted: suppress or sanitize them before output. Never pass secrets on the command line.
- **Dry-run skips effects, not arbitrary Python**: `run()` is never invoked and `ctx.sh` is guarded, but probes, validation and `describe()` still execute and must be read-only. Callbacks are not sandboxed.
- **Unattended is first-class**: `--yes`, env-backed answers, exit 6 when something is missing or invalid. Without a TTY, `--yes` is required to execute — a piped run without it prints the plan and exits 6 rather than acting on nobody's confirmation.
- **80 columns, `NO_COLOR`, `| cat`** must all produce sane text. Verify cursor/colour restoration on normal exit, failures and Ctrl-C; do not promise cleanup for uncatchable termination.
- **Durations are shown**, from the process model.
- **The harness is one file plus the kit plus a theme**; no framework dependency for the operator surface.

## The TUI layer (tui-design)

`termcraft:tui-designer` owns the look. It receives the harness name, stages, mood and terminal facts. It returns candidates to the user-facing parent for selection, then generates `theme.py` on resumption with the choice. Wait for results; if nested spawning is unavailable or rejected, follow the tui-design skill inline with permitted tools or return a handoff. Never bypass host restrictions.

Paths in this reference are skill-relative: resolve `scripts/...` against the loaded cli-harness skill directory; resolve `tui-design/...` against its sibling tui-design directory, always to absolute paths. A reference file does not export `CLAUDE_PLUGIN_ROOT`. Candidate and generation tools are `tui-design/scripts/preview_theme.py` and `tui-design/scripts/make_theme.py`.

Import the generated theme optionally (do not hide errors inside an existing theme):

```python
try:
    from theme import THEME, BANNER
except ModuleNotFoundError as exc:
    if exc.name != "theme":
        raise
    THEME, BANNER = None, None
ui = UI("pb", banner=BANNER, theme=THEME)
```

The kit then handles the ladder on its own: truecolor → 16-colour fallback per role → `NO_COLOR`; light background via `COLORFGBG`/`HARNESS_BG=light`; ASCII glyph set when stdout is not UTF-8 or `HARNESS_ASCII=1`; banner dropped to plain text when it does not fit. Rules that still apply: ≤ 4 colours on the interactive surface, one box weight, no animation while a prompt is open, and the harness must run unchanged with `theme.py` deleted.

`ctx.sh()` defaults to `check=True`: a failed command fails its stage. Use `check=False` only with explicit return-code handling. Child output is inherited, not redacted. A failed `describe()` returns exit 2; it must not be reported as a successful dry run.
