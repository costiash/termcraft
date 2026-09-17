# Auditing an existing harness

The user already has an installer, wizard, or operator CLI. The job is to map what it actually does, find where it fails the contract in `harness-design.md`, fix those without breaking its users, and prove it.

## 1. Explore without changing anything

Read startup and flag-handling code before execution: an existing tool's `--help`, `--check` or `--dry-run` is not proof of safety. Resolve `scripts/drive_harness.py` (and its basename below) against the loaded cli-harness skill directory to an absolute path; do not assume cwd or an exported plugin-root variable.

```
python scripts/drive_harness.py --explore "<cmd> --help"
python scripts/drive_harness.py --explore "<cmd> --check"        # if it has one
python scripts/drive_harness.py --explore "<cmd> --dry-run"      # if it has one
```

Then read its source (digest it like any codebase). Reconstruct its state machine in the process-model schema: stages, probes (or the lack of them), questions, effects, exits. Note what it does at startup before any confirmation.

## 2. Drive it

Write scenarios (`drive_harness.py`) for: fresh machine, rerun on a completed machine, each documented failure, Ctrl-C mid-run, `| cat`, `NO_COLOR=1`, unattended with and without inputs, wrong/malformed answers. Snapshot the working tree before and after each run to see what it touched.

## 3. Gap checklist

| Gap | Symptom | Fix pattern |
|---|---|---|
| asks what it could probe | prompts for a value present in `.env`/git/env | add probe → `facts` |
| no plan | starts doing things before showing what it will do | plan screen + confirm |
| silent destruction | deletes/overwrites without a plan and confirmation | forbid `never` actions; explicitly confirm permitted destructive effects |
| no resume | a failure means starting over | re-probe partial state; journal transitions, not saved answers |
| stack traces | the person sees a Python traceback | catch → sanitized summary + outcome journal; separate sanitized diagnostics if needed |
| secrets echoed | password visible in prompt, log, error, or shell history | getpass + known-value redaction; suppress/sanitize child and direct output; no CLI-arg secrets |
| non-TTY breaks | crashes or hangs when piped or in CI | isatty ladder; `--yes`; exit 6 |
| no dry-run/check | can't preview or verify | read-only probes/validation/descriptions, guarded effects; verify no changes, callbacks are not sandboxed |
| ambiguous exits | every failure exits 1 | exit-code contract |
| mystery durations | long stages with no estimate | stated/measured `expect_s` |
| README dependency | the person must read docs to run it | fold the docs' guidance into probes and fixes |
| width/colour | broken at 80 cols, unreadable with NO_COLOR | kit UI |

## 4. Fix without breaking

- Keep the command name, flags, exit codes and file locations that existing users/scripts rely on; add, don't rename. If a behaviour must change, keep the old one behind the old flag for one release and say so in `HARNESS.md`.
- Prefer wrapping: if the existing tool is sound but unfriendly, the harness can orchestrate it (`run` calls it) rather than rewriting it.
- Every fix gets a scenario that failed before and passes after; ship the scenarios.

## 5. Report

Findings table (gap · evidence: transcript line · fix · scenario), then what was changed, then what was verified and what could not be (missing infrastructure), then how to run the scenarios again.
