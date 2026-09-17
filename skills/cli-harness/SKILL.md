---
name: cli-harness
description: >-
  Build, audit and improve operator CLI harnesses — guided, resumable, TUI-quality command-line programs that wrap a process defined by a codebase or shell script (install → setup → data → operate). Use when a user requests a CLI/TUI/installer/wizard/operator console, a friendlier setup script, or testing/auditing an existing harness. Ships a stdlib runtime (harness_kit.py: finite-state stages with probes, plan, transition journal, secrets, exit codes), a static digest tool, and a pty driver for verification.
---

# cli-harness

An operator harness is a finite-state machine wearing a friendly face. Each *stage* knows how to **probe** whether it is already done, blocked, or pending; what it must **ask** (only when a probe cannot find the answer); what it **runs**; how long it usually takes; and what it **never** does. The runner probes everything first, shows one plan, asks once, confirms once, executes in order, journals every transition so a rerun resumes, and exits with a code that means something. The person never reads a README to operate it.

Two jobs:

- **Create** — from a source tree or a shell script: digest → connection map → process model → harness on `harness_kit.py` → TUI layer → pty-verified.
- **Audit** — an existing harness/installer/wizard: explore it in a pty, reconstruct its state machine, find the gaps (`references/audit-existing.md`), fix them, re-verify.

## Bundled resources

Reference paths are skill-relative to `${CLAUDE_PLUGIN_ROOT}/skills/cli-harness/`; resolve them to absolute paths before reading. Script basenames below identify the absolute entries in this table. Ordinary reference files do not export `CLAUDE_PLUGIN_ROOT`: replace their `<skill-root>` placeholders with this resolved absolute directory before running examples, without changing or assuming cwd. Put outputs in the target project.

| Path | Read / run when |
|---|---|
| `references/digest.md` | starting a digest: what to extract from code and scripts, how to read `connection-map.json`, what to read by hand afterwards |
| `references/process-model.md` | turning the map into stages: the model schema, guards/probes, effects, exits, invariants, idempotence, resume |
| `references/harness-design.md` | the UX contract every harness obeys (probe before ask, secrets, dry-run/check/yes, exit codes, non-TTY) and how the TUI layer uses the tui-design theme bank |
| `references/libraries.md` | deciding the dependency tier (stdlib bootstrap vs Rich/questionary/Typer vs Textual) and which library serves which UX concern; the kit auto-upgrades to Rich when importable |
| `references/audit-existing.md` | the user already has a harness: exploration protocol, gap checklist, how to fix without breaking its users |
| `${CLAUDE_PLUGIN_ROOT}/skills/cli-harness/scripts/digest.py` | run first: `python3 "${CLAUDE_PLUGIN_ROOT}/skills/cli-harness/scripts/digest.py" <dir-or-script> --out connection-map.json --mermaid map.mmd` |
| `${CLAUDE_PLUGIN_ROOT}/skills/cli-harness/scripts/harness_kit.py` | copy beside the generated harness: `Stage`, `Verdict`, `Question`, `Harness`, `UI`, common probes |
| `${CLAUDE_PLUGIN_ROOT}/skills/cli-harness/scripts/test_kit.py` | contract tests: dry-run callbacks, validation, redaction boundaries, non-TTY, re-probe, waiting |
| `${CLAUDE_PLUGIN_ROOT}/skills/cli-harness/scripts/drive_harness.py` | pty scenarios and `--explore "<cmd>"` |
| `${CLAUDE_PLUGIN_ROOT}/skills/tui-design/SKILL.md` | theme references and absolute tool paths; delegate to `termcraft:tui-designer` |

## Workflow

1. **Digest, then read.** `digest.py` finds entry points, exec chains, env contracts, subprocesses, writes, guards, ports and tests. It tells you where to read; then read those files fully. Missing pieces (a script that `exec`s a module that is not in the tree) are recorded as *external dependencies with a probe*, never assumed.
2. **Write the process model** (`references/process-model.md`) before code: stages with probe / ask / run / needs / expect / never / exits, plus the global invariants ("setup never touches RDS"). The model is a JSON/Markdown document the user can review; it is the contract the harness implements and the verifier tests.
3. **Pick the dependency tier** (`references/libraries.md`): bootstrap installers stay stdlib; consoles inside an established environment may use Rich/questionary/Typer; the stdlib path must keep working. Then **generate the harness** on `harness_kit.py`. One file per harness (`<name>.py`) plus the kit beside it. Every stage's probe is real (checks the filesystem, commands, ports, env, journal) and side-effect free. Every `run` delegates to the project's own scripts/commands where they exist — the harness orchestrates, it does not reimplement.
4. **TUI layer**: dispatch `termcraft:tui-designer` with the harness name, stages, mood and terminal facts; wait for candidate results, relay them through the user-facing parent for choice, then resume with the choice and wait for `theme.py`. If spawning is unavailable or rejected, follow the tui-design skill inline with permitted tools or return a handoff; do not bypass restrictions. Use the optional theme import in `references/harness-design.md`, then `UI(name, banner=BANNER, theme=THEME)`.
5. **Verify in a pty** with `drive_harness.py` scenarios: happy path; `--check` and `--dry-run` change nothing (diff the tree before/after); rerun is idempotent ("nothing to do"); preconditions before changes exit 3; failures or newly blocked stages after effects exit 4 with an actionable fix and safe rerun. Verify this 3/4 contract against the runtime and report mismatches. `--yes` without inputs exits 6; secrets never appear in transcript or journal, including child output; `NO_COLOR=1` and `| cat` produce sane text; Ctrl-C leaves the terminal clean. Where infrastructure is unavailable, test explicit env-selected fakes (`HARNESS_FAKE=…`) and disclose the limits.
6. **Deliver**: the harness, `harness_kit.py`, `theme.py`, the process model, the scenarios directory, and a one-screen `HARNESS.md` (how to run, flags, exit codes, resume, unattended use). Summary lists what was verified and what could not be.

## Rules

- The harness orchestrates existing scripts/commands; it never re-implements their logic. If the source has no command for a step, the stage runs the smallest explicit action and says so.
- Probe before ask; ask once; a fact a probe can find is never a question.
- `never` lists forbid actions; explicitly plan and confirm permitted destructive effects. Keep probes, validation and descriptions read-only: dry-run skips `run` and guards `ctx.sh`, but callbacks are not sandboxed.
- Every failure names the stage, cause and fix; rerun re-probes real state. The journal records transitions/outcomes, not persisted answers or tracebacks.
- Hide secret input and register secret questions for known-value redaction in kit-controlled messages/journal details. Authors must suppress or sanitize child stdout/stderr and direct prints, which bypass that redaction.
- Works at 80 columns, without colour, without a TTY.
