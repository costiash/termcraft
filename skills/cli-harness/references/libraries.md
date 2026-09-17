# Libraries — what to use when dependencies are allowed

The kit is stdlib-only on purpose: an installer runs *before* the environment exists (`install.sh` → `python3 -m tools.installer` with nothing installed yet), and a harness must work in CI pipes and on locked-down hosts. But an operator console that runs *inside* an established environment can and should use better tooling. Decide per harness, record the decision in `HARNESS.md`, and keep the stdlib path working (the kit degrades automatically).

## Tiers

| Tier | When | Rendering | Prompts | CLI surface |
|---|---|---|---|---|
| **0 — bootstrap** | installers, anything that runs before `pip`/`uv` | kit (ANSI, box drawing, meters) | kit (`input`/`getpass`) | argparse (kit) |
| **1 — established env** | operator consoles inside a repo with a lockfile | **Rich** (auto-detected by the kit: tables, panels, progress, prompts) | Rich `Prompt`/`Confirm` (kit) or **questionary** for lists/checkboxes/autocomplete | **Typer** for multi-command surfaces (`data bootstrap`, `data refresh`, …) with shell completion |
| **2 — full-screen** | long-running dashboards, live logs, multi-pane monitoring | **Textual** (widgets, layouts, keybindings, mouse) | Textual inputs | Textual app + a thin Typer launcher |

Tier 2 is the exception, not the goal: a wizard is a sequence of screens, not an app. Reach for Textual only when the person must watch several things at once (a data ladder with per-table progress, a log tail and a status panel).

## Recommended per concern

| Concern | Library | Why it helps the simple user | Kit fallback |
|---|---|---|---|
| tables, panels, progress, markup | **rich** | readable plan tables, live progress bars with ETA, wrapped panels, colour that respects `NO_COLOR` | kit ANSI renderer |
| structured prompts (select, checkbox, path autocomplete, password) | **questionary** (on prompt_toolkit) | arrow-key selection instead of typing option names; validation inline; hidden passwords | `input`/`getpass` |
| multi-command CLI, `--help`, completion | **typer** | consistent help, type-checked args, shell completion for stage names | argparse |
| full-screen TUI | **textual** | multi-pane live views, keybindings, mouse; CSS-like layout | tui_frame.py |
| logs | **loguru** | one-line setup, rotation, `logger.exception()` with context, secret filtering via `patcher`; write the journal *and* a human log | kit Journal + print |
| retries around flaky probes/effects | **tenacity** | declarative `@retry(stop=stop_after_attempt(3), wait=wait_exponential())` for network probes (RDS reachability, port checks) | manual loop |
| env contracts | **pydantic-settings** (+ python-dotenv) | typed, validated settings from `.env` with clear per-field errors — mirrors `MissingConfigurationError` | `probe_env_file` |
| humane units | **humanize** | "1 hour 9 minutes", "5.6 GB", "3 minutes ago" in plan and progress | f-strings |
| journal/config location | **platformdirs** | correct per-OS state dir instead of a dotfile in the repo | `.harness/` in root |
| "did you mean" for stage names, scopes, answers | **rapidfuzz** (`process.extractOne`, WRatio) | a typo in `--only setpu` or a scope answer gets a suggestion instead of "unknown stage"; treat score < 80 as "ask", never auto-accept | `difflib.get_close_matches` (stdlib — good enough for ≤ 20 candidates; the kit should use it) |
| memoised probes | **cachetools** (`TTLCache` + `@cached`) | expensive probes (docker version, remote reachability) run once per plan/execute pass instead of twice; TTL keeps `--check` honest | dict in `Context` for one run |
| per-loop progress inside a stage | **tqdm** | wraps any iterable (tables to copy, files to write) with an ETA in one line; `tqdm.write()` keeps log lines above the bar | kit meter / Rich progress (prefer Rich when already present — one renderer) |
| where the time goes | **pyinstrument** (dev only) | call-tree profile of a slow probe pass; never shipped in the harness | `time.perf_counter()` around probes |
| fast JSON journal/reports | **orjson** | faster dumps/loads and native datetime for large journals or `--report` output | stdlib json (journals are small) |
| batching, windows, first-match | **more-itertools** (`chunked`, `first`, `unique_justseen`) | batch table copies, de-duplicate repeated log lines in the streamed output | small helpers |
| tables → files | **tabulate** | markdown/plain tables for `--report` output that pastes into issues | manual |
| paths, temp, atomic writes | stdlib `pathlib`, `tempfile`, `os.replace` | already enough | — |

## Rules

1. **Detect, don't require.** `try: import rich except ImportError: rich = None`. The kit already does this for Rich; do the same for questionary. A harness must never crash because a nicety is absent.
2. **Never put a secret in a CLI argument** whatever the library — shell history and `ps` see it. Prompts hidden, env vars, or a file with mode 0600.
3. **`NO_COLOR`, non-TTY and 80 columns still hold** with every library. Rich honours `NO_COLOR` and `TERM=dumb`; questionary needs a TTY — fall back to `input` in pipes (the kit's `--yes` path).
4. **One rendering library per harness.** Rich *or* Textual; not both fighting over the terminal.
5. **Bootstrap installers stay Tier 0** even when the repo has these deps, because the installer's job is to create the environment that would contain them.

## Source note

Requested source: the Medium article "21 Python libraries that quietly do the work you're still doing by hand" (python.plainenglish.io). Items 1–7 were reviewed (Loguru, Pyinstrument, orjson, RapidFuzz, more-itertools, cachetools, tqdm); the fetch is paywalled past the first item, so items 8–21 were not seen. For a harness the ones that change the person's experience are **Loguru** (a human log beside the journal, rotation, secret-filtering `patcher`), **RapidFuzz** ("did you mean" on stage names and answers), **cachetools** (probe memoisation with TTL) and **tqdm** (per-loop progress inside a stage, only when Rich is not already the renderer). Pyinstrument is a development aid; orjson and more-itertools are conveniences, not UX. Everything above stays optional: detect, don't require.
