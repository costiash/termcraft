# Process model — the state machine the harness implements

Write this before code. It is reviewed by the person, implemented by the harness, and tested by the driver.

## Schema

```yaml
harness: <name>                # command name
root: <how the project root is found>   # e.g. dir of this file · env PB_REPO_ROOT · walk up to pyproject.toml
invariants:                    # global "never" list, shown in the plan
  - setup never contacts RDS
  - nothing is deleted: env files, volumes, data
stages:
  - id: python                 # short, stable; used by --only/--from and the journal
    title: Python ≥ 3.10       # what the person sees
    kind: precondition | setup | data | operate | verify
    probe: |                   # side-effect free; returns done | todo | blocked | unknown with detail and fix
      command python3 --version ≥ 3.10  → done "python 3.12" · blocked "python3 is too old (3.10 or newer…)"  fix: <script's own message>
    needs: []                  # dependency edges (DAG)
    ask: []                    # questions only when a probe cannot supply the value: key, prompt, secret?, env, default, validation
    run: |                     # the effect; delegates to the project's command. NEVER called in --dry-run.
      ./setup-profiling.sh --interactive=false  (env: …)
    describe: |                # what run would do, for --dry-run: commands via ctx.would([...]), files it would write
    expect_s: 240              # stated in docs or measured; 0 for instantaneous
    never: [RDS copy, jobs, external API calls]
    exits:                     # every way this stage fails and what the person is told
      - match: "Docker Engine not found"
        status: blocked
        fix: "install Docker Engine + Compose plugin, add your user to docker, rerun"
      - match: "port 15432 in use"
        status: todo
        fix: "override recorded in infra/resources.env"
    idempotent: true           # rerun with the stage done must be a no-op (probe says done)
    resumable: true            # a failure mid-stage can be rerun safely
```

## Rules for a sound model

- **Probes are the truth.** A stage is `done` when its probe says so, never because the journal says a previous run finished — environments drift. The journal is for resume and audit, not for state.
- **Every ask has an escape hatch**: an env var or `--answer key=value`, so unattended runs work.
- **Preconditions are stages** (Python version, Docker, disk space, ports, git identity). They have no `run`, only `blocked`/`done`, and they carry the project's own error text as the fix.
- **Effects are the project's commands.** The harness never re-implements setup logic; it sequences, supplies inputs, watches, and interprets exits.
- **Exits are enumerated.** Read the guards and error messages from the digest; each becomes an `exits` entry with a fix. Report an unknown failure with secrets sanitized and the journal path; use separate sanitized diagnostics for tracebacks.
- **Invariants are visible.** The union of `never` lists is shown before confirmation; a stage that would violate one does not exist.
- **Durations are honest.** Use stated figures ("first bootstrap planned for hours", "69 minutes on the first real copy") and show them; a meter without an estimate is a spinner.
- **The DAG is small.** 6–15 stages. Sub-steps live inside a stage's `run` with their own progress lines.

## Modes every harness supports

| Flag | Behaviour |
|---|---|
| (none) | plan → questions → confirm → run pending stages |
| `--check` | probe and report; exit 0/3; changes nothing |
| `--dry-run` | plan + what each stage would run; changes nothing |
| `--yes` | unattended; answers from env/`--answer`; missing → exit 6 |
| `--only ID` / `--from ID` | one stage with its needs / skip every stage before ID (their probes are not consulted) |
| `--stages` | list the DAG |
| `--journal PATH` | record transitions elsewhere than `<root>/.harness/<name>.jsonl` |

Required exit contract: 0 ok · 2 usage · 3 precondition before changes · 4 failure after effects may have started (including a newly blocked stage; rerun safely re-probes) · 5 aborted · 6 missing or invalid input (also: not a TTY and no `--yes`). Verify the 3/4 distinction against the bundled runtime and report mismatches; a late failure must not imply that nothing changed.

## Runtime behavior and author obligations

Tests are in `scripts/test_kit.py`, relative to the cli-harness skill directory, not cwd; resolve that path to absolute before running.

- `--dry-run` never calls `run()`; it prints `describe()`; `ctx.sh` raises if reached in dry-run. Probes, validation and descriptions still execute: authors must keep them read-only, since there is no callback sandbox. The same read-only requirement makes `--check` safe.
- Every answer is validated whatever its source (`--answer`, env, default, probe fact); invalid unattended → exit 6.
- **Journal faults never escape.** An unwritable journal breaks once (no retries), prints one sanitized warning naming the path, and the run keeps its exit-code contract: before any effect → exit 3 (nothing ran); after effects started → exit 4 (nothing more runs; rerun resumes from probes); at `done`/`failed` the original outcome and error are reported unchanged. `--journal PATH` relocates it. An unreadable journal at start is a warning, not an error.
- A stage whose probe stays `unknown` after running is journaled `ran-unverified`, never `done`; execution stops with exit 4 before any dependent stage runs. Unknown read-only prerequisites stop the initial plan with exit 3 — unless the stage `needs` a pending predecessor, in which case it is `waiting` (like a blocked dependant) and is re-probed after that predecessor runs. The journal contains transitions and outcome details, not persisted answers or tracebacks.
- Known answers to `Question(secret=True)` are redacted in kit-generated messages, journal details and dry-run descriptions; passing one on the command line prints a warning. Direct prints and `ctx.sh` child stdout/stderr bypass this redaction: authors must suppress or sanitize them.
- Without a TTY and without `--yes` no stage effects execute (exit 6 after the plan).
- Each stage is re-probed immediately before it runs; work already done by a predecessor is skipped.
- A stage `blocked` only because a pending predecessor has not run yet shows as `waiting` and is re-probed after it. Test both initial preconditions (exit 3) and late blocks after effects (exit 4); do not label both as unchanged.

`ctx.sh()` defaults to `check=True`: a failed command fails its stage. Use `check=False` only with explicit return-code handling. Child output is inherited, not redacted. A failed `describe()` returns exit 2; it must not be reported as a successful dry run.
