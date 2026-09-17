# Digest — from source to connection map

The goal is a **connection map**: what the entry points are, what each hands off to, what every step needs from the environment, what it touches, and how it fails. `scripts/digest.py` produces the over-inclusive first pass; reading produces the truth.

## 1. Run the digest

```
python scripts/digest.py <dir-or-script> --out connection-map.json --mermaid map.mmd
```

Sections and what to do with each:

| Section | Meaning | Then |
|---|---|---|
| `entrypoints` | console scripts (`pyproject [project.scripts]`), `__main__` modules, argparse/click/typer commands, shell scripts | read each entry point top to bottom; these are the harness's `run` targets |
| `exec_chain` | for every shell script: `exec`, `source`, `python3 -m`, `uv run`, `docker …` hand-offs | follow every hop; a hop to a module not in the tree is an **external dependency** (probe it, don't assume it) |
| `env` | every env var read, with the reading file; `<PREFIX>NAME` means a prefix-parameterised family (e.g. `PROFILING_SOURCE_PG_*`) | these are the harness's questions/probes; group by family and find the `.env.example` that documents them |
| `env_examples` | keys per `.env.example` | required-key lists for `probe_env_file` |
| `subprocesses` | external commands the code shells out to | preconditions (`probe_command`) and the harness's own `never` lists |
| `writes` | files/dirs written | what `--dry-run` must not touch; what `--check` should inspect |
| `guards` | early exits: `command -v`, version checks, `id -u`, `sys.exit(...)`, raised errors | each guard is a **blocked** verdict with the script's own message as the `fix` |
| `ports` | numeric ports near the word "port" | `probe_port_free` candidates and override env vars |
| `imports` | intra-repo package graph | dependency order of packages; which package owns a step |
| `tests` | test files, markers, opt-in env vars | how to verify without live infrastructure (fakes, `local_*` markers) |
| `docs` | README/CLAUDE/AGENTS | read them; they state invariants ("never contacts RDS") the code only implies |

## 2. Read what the digest pointed at

For each entry point, write down in one line each: **inputs** (args, env, files), **preconditions** (guards), **effect** (what changes), **outputs** (files, tables, containers, exit codes), **duration** (stated or measured), **failure modes** (each raised error / abort line and its message). Shell guard messages and Python exception texts are gold: reuse them verbatim as `fix` strings so the harness speaks the project's own language.

## 3. Draw the map

Nodes: entry points, packages, external dependencies (Docker, uv, a remote DB), files/env, stores. Edges: exec/hand-off, reads env, writes file, needs command, talks to store. Mermaid from the digest is the skeleton; correct it by hand. The map goes into the deliverable — the person can see what the harness is orchestrating.

## 4. Missing pieces

A hand-off target not present in the tree (e.g. `install.sh` → `python3 -m tools.installer`, tree lacks `tools/`) becomes a stage whose probe checks for it and whose `blocked` fix says exactly what is missing and where it is expected. The harness must be honest about the edge of its knowledge; it must not fabricate the missing component's behaviour.

The scanner is heuristic, not a Python/shell/TOML parser. Console-script extraction is scoped to `[project.scripts]`; quoted keys, multiline TOML, dynamic imports, namespace layouts and indirect shell execution still require source reading. Local import candidates come from this tree, not a hardcoded project vocabulary. Generated Mermaid labels escape punctuation and use hash IDs; diagram rendering is a separate check.
