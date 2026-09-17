# termcraft

[![validate](https://github.com/costiash/termcraft/actions/workflows/validate.yml/badge.svg)](https://github.com/costiash/termcraft/actions/workflows/validate.yml)

Terminal craft for Claude Code CLI: operator CLI harnesses generated or audited from a codebase, and terminal UI design from a theme bank — with workflows that require pty verification.

## What's inside

| Component | Purpose |
|---|---|
| `agents/harness-architect.md` | Digests a source tree or shell script into a connection map and a finite-state process model; generates a guided, resumable operator CLI harness on `harness_kit.py`; or audits an existing installer/wizard (explore in a pty → gap table with transcript evidence → fixes → scenarios). Delegates the look to tui-designer. |
| `agents/tui-designer.md` | Terminal UI/UX specialist. Picks a theme family from the product's mood, renders three real candidates (plus mono, ASCII and light-terminal variants) for the person to choose, generates `theme.py` and a banner, verifies at 80 columns / `NO_COLOR` / piped / light background. |
| `skills/cli-harness/` | The harness method (digest → process model → harness design → libraries tier → audit) and tools: `harness_kit.py` (stdlib runtime: stages with side-effect-free probes, plan, invariants, journal/resume, secrets, exit-code contract, dry-run with author-supplied read-only callbacks, theme-aware UI), `digest.py`, `drive_harness.py` (pty driver), `test_kit.py` (contract tests). |
| `skills/tui-design/` | The theme bank (`themes.py`: noir, blueprint, phosphor, amber, paper, cyber, slate, mono — each with dark and light palettes, 16-colour and ASCII fallbacks, glyph sets), `preview_theme.py` (render the real screens per theme), `make_theme.py` (self-contained `theme.py`), `banner.py` (block-letter font, no FIGlet), `ascii_render.py` (luminance glyph rendering with dithering, or RGB halfblocks without dithering), `tui_frame.py` (widgets: frame diff-redraw, box, meter, sparkline, table, kv, tree, tabs, columns), references. |
| `skills/harness/`, `skills/design/` | `/termcraft:harness <path>` and `/termcraft:design <request>` — entry commands that dispatch to the agents. |

## Install

**Local, persistent:** add this directory as a marketplace, then install its plugin. In Claude Code:

```text
/plugin marketplace add /absolute/path/to/termcraft
/plugin install termcraft@termcraft-marketplace
```

Choose User scope for all your projects, or Local scope for only the current project. Adding the marketplace alone does not install the plugin. Its `source: "./"` resolves relative to the marketplace root (this directory), not `.claude-plugin/`. On current Claude Code, this local-directory source loads in place; keep the directory available. Restart or run `/reload-plugins` after edits.

**Local, one session only** (no persistent install):

```sh
claude --plugin-dir /absolute/path/to/termcraft
```

**From a git repo** containing this folder at its root:

```text
/plugin marketplace add costiash/termcraft
/plugin install termcraft@termcraft-marketplace
```

Git-hosted installs use the plugin cache; local source edits do not update that copy.

For a Cowork `.plugin` package, use Cowork's plugin import flow; this source folder is not itself that package.

## Verify plugin metadata

From this directory, run `claude plugin validate .`. Because the root also contains a marketplace, validate `skills/` and `agents/` separately with `claude plugin validate ./skills` and `claude plugin validate ./agents` (directory-only validation requires Claude Code 2.1.233+). Validation checks metadata, not agent behavior.

After loading the plugin, inspect `/plugin` for load errors and `/agents` for `termcraft:harness-architect` and `termcraft:tui-designer`. Confirm `/termcraft:harness` and `/termcraft:design` are available. See the [official plugin reference](https://code.claude.com/docs/en/plugins-reference) for installation scopes, path resolution and validation.

## Use

- `/termcraft:harness ~/code/repo` — generate an operator harness for a codebase
- `/termcraft:harness audit tools/installer` — evaluate and fix an existing one
- `/termcraft:design theme for the installer — show me noir, slate and blueprint at 80 columns`
- Or describe the task; the agents trigger on CLI/TUI/installer/harness/terminal-look requests.

## Validation

One command runs every gate and fails on the first problem (exit 1); it is what CI runs:

```sh
python3 scripts/check_plugin.py            # table on stdout
python3 scripts/check_plugin.py --json     # machine-readable report
python3 scripts/check_plugin.py --skip official   # on a box without the claude CLI
```

| gate | what it proves |
|---|---|
| `official` | `claude plugin validate --strict --json` raises nothing for `plugin.json`, `marketplace.json`, `skills/`, `agents/` |
| `manifest` | kebab-case name, semver, descriptions long enough to trigger; every `SKILL.md` and agent has **parseable** YAML frontmatter with the right `name`, `<example>` blocks, `model`/`color`; entry skills dispatch to agents that exist. The official validator (2.1.x) reports only components it has findings for and does not parse SKILL.md frontmatter strictly — this gate does |
| `links` | every `references/…`, `scripts/…`, `assets/…` path mentioned in a skill or agent exists; no leftovers from the removed web skill or the old plugin name |
| `compile` | every `.py` compiles |
| `tests` | all bundled `test_*.py` suites pass (61 tests: kit contract, pty driver, digest, UI, tools, reviews) |
| `previews` | all themes render dark/light/ASCII at 80 columns; no line wider than 80; ASCII previews are pure ASCII |
| `contrast` | 48 palette-role checks: ink ≥ 7:1, dim ≥ 3:1, accent ≥ 4.5:1 |
| `evals` | the `evals/` suite parses (frontmatter, grader types, scaffold scripts) |
| `package` | `package_plugin.py` rebuilds the ZIP and byte-verifies it; no `__pycache__`/`.pyc` in the tree |

A green table is necessary, not sufficient. The live gate is `claude plugin eval` — `evals/README.md` has the three cases (theme pick, harness create, harness audit) and the exact commands; the smoke case costs a few cents, the create/audit cases run real agents against scaffolded fixtures and need `--scaffold --allow-tools Bash Write Edit` (a sandbox backend — bubblewrap + socat on Linux — must be installed or the CLI refuses the shell grant). `.github/workflows/validate.yml` runs the gates on every push and the smoke eval on manual dispatch.

Individual suites, if you want them alone:

```sh
python3 -B -m unittest discover -s skills/cli-harness/scripts -p 'test_*.py' </dev/null
python3 -B -m unittest discover -s skills/tui-design/scripts -p 'test_*.py' </dev/null
python3 skills/tui-design/scripts/preview_theme.py --name PB  # visual review
```

These test bundled runtime/tools, not Claude dispatch — that is what the evals are for. Renderer tests require Pillow + numpy; inspect skips rather than treating them as coverage. See [AUDIT.md](AUDIT.md) for the latest review, evidence, and remaining limitations. Use only synthetic secrets in PTY scenarios. The driver checks the original capture, then redacts declared `script[].secret` values from saved transcripts and diagnostics. This does not detect undeclared, encoded or transformed credentials.

## Dependencies

Runtime: Python 3.10+ with the standard library only. Optional: Pillow + numpy for `ascii_render.py` (image→glyph rendering); Rich for richer kit rendering (`HARNESS_PLAIN=1` forces plain). No plugin manifest declares these; install them in your environment if you use the renderer.

## 0.7.0 compatibility notes

- An executed stage whose final probe remains `unknown` now stops the run with exit **4** and a `ran-unverified` journal event. Dependents do not run. An unverifiable read-only prerequisite exits **3** before effects.
- `Context.sh()` now defaults to `check=True`. Use `check=False` only when the caller explicitly handles the command's return code. Child output remains inherited and must be sanitized or suppressed by the harness author.
- Saved theme previews include both `.ansi` (truecolor candidates) and `.txt` (plain geometry). View `.ansi` with `cat` in a compatible terminal; `--out` deliberately preserves colors regardless of output redirection.
- The frame demo accepts `--no-animation`; its runner restores terminal state on callback errors and stops motion under `NO_COLOR` or `TERM=dumb`.
- Rebuild the source ZIP with `python3 scripts/package_plugin.py`. It includes only manifests, agents, skills, maintenance scripts, assets, README, the current audit, LICENSE and third-party notices; no environment, bytecode or review evidence. This is a source ZIP, not a tested Cowork import package.

## License

Termcraft is [MIT licensed](LICENSE), copyright 2026 Costa Shafranski. See [third-party notices](THIRD_PARTY_NOTICES.md) for ASCII Magic attribution and a separately scoped summary of its service terms. Those service terms do not add restrictions to Termcraft’s MIT license.

## Sample artwork

The [asset library](skills/tui-design/assets/README.md) contains **four original imagegen source illustrations and 15 real terminal conversions**: Terminal Study, Lunar Relay, Nautilus and Voxel Grove. Explore ASCII, dithered blocks, dots, lines, Braille and color halfblocks. Each set includes its generation prompt, reproduction commands and verified hashes. Compact outputs are optional splash assets; 80×24 Braille outputs are detail references. The source ZIP includes all assets.
