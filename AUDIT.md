# Termcraft independent review — 2026-09-17

## Verdict

**The terminal-only direction is coherent, and the plugin is materially stronger after this review. It is suitable for a controlled local trial, but I would not call it fully release-certified.** Remaining release concerns include live Claude-agent/real-terminal acceptance and a reproduced journal-I/O error-handling defect; metadata parsing passes. The missing-license-document gate is now closed; remaining technical gates are listed below.

The two specialties complement each other: the architect models and orchestrates existing operations; the designer supplies an optional presentation layer. Dropping the web-page skill reduces scope without weakening that purpose. The image renderer's small HTML export is still present as an output format, not a website-building workflow. No webpage skill was reintroduced.

This review inspected the supplied source tree, not a Git diff: `.git` is not a usable repository. It covered both manifests, both agents, all four skills and their references, all original Python tools/tests, and the supplied ZIP. The previous audit was treated as a list of claims to verify, not proof. Its text and the original ZIP are preserved under `review-evidence/`; baseline SHA-256 hashes are recorded there too.

## Confirmed findings and changes

| Priority | Finding and trigger | Resolution |
|---|---|---|
| P1 | `drive_harness.py` persisted a raw leaked secret and repeated its value in assertion diagnostics. The verifier itself leaked the value it rejected. | Assertions now inspect the original in-memory capture, then declared step secrets are redacted from stored transcripts and diagnostics. A regression verifies both the failure and sanitized output. |
| P1 | A process closing its PTY before exiting bypassed the timeout and reached a blocking wait. Timeouts killed only the direct child; descendants could continue effects. | Monotonic deadline remains active after EOF; process-group cleanup and descriptor closing run in `finally`. Real subprocess tests cover closed descriptors and a descendant's delayed write. Processes deliberately escaping the group are outside this guarantee. |
| P1 | An `unknown` final probe produced a `ran-unverified` journal event but execution continued to dependents and could conclude “all stages done.” | Stops with exit 4 after an unverified execution; dependents do not run. An unknown read-only prerequisite blocks the initial plan with exit 3. Existing contract test updated intentionally for this behavior change. |
| P1 | A project name was interpolated into the generated Python module's triple-quoted docstring. Quotes/newlines could break syntax or insert Python executed when importing the theme. | Generated documentation is now a Python string literal via `repr`; a hostile-name regression imports the result safely. This was a generator input-to-code boundary, not a remotely reachable service. |
| P2 | `Context.sh()` ignored nonzero command exits by default. A stage could continue after a failed external command unless its author remembered `check=True`. | Defaults to `check=True`; explicit `check=False` remains available for callers that handle return codes. This is a documented compatibility change. |
| P2 | The PTY driver could reuse an old prompt match, override scenario `TERM`, report success for an empty directory, or accept an unexpected command failure when no exit assertion was given. Capture size was unbounded. | Consumes prompt output, respects `TERM`, rejects empty suites, defaults expected exit to zero, limits capture to 8 MiB (scenario override), and parses exploration commands with `shlex`. Scenario names must be simple filenames. |
| P2 | Runtime cleanup depended on process exit, SIGINT handlers were left installed, plain prompt EOF returned an unvalidated default, and malformed verdicts could silently disappear from the plan. | Explicit final cleanup/restored SIGINT; EOF yields missing input; verdict validation; invalid flag combinations/answer syntax rejected. Failed dry-run descriptions no longer return success. |
| P2 | Minimum-version probes accepted unparseable output, ignored the command's exit status and missed stderr versions. | Fail closed as `unknown`, inspect stdout plus stderr, and compare normalized version tuples. Read-only unknown prerequisites stop execution. |
| P2 | Saved theme candidates discarded color, so their principal design difference could not be reviewed from the deliverables. Installed Rich could also interfere with capture. | Save `.ansi` truecolor candidates alongside `.txt` geometry previews; use deterministic plain rendering for capture. `--out` deliberately preserves color in its ANSI files. |
| P2 | Mono used chromatic ANSI16 roles; banner fallback could exceed its promised width; ASCII conversion missed plan/panel data. Rich interpreted plan/panel text as markup. | Grayscale mono fallbacks, bounded banners, consistent ASCII plan/panel conversion, literal Rich text. Examples separate failure output from a successful rerun. |
| P2 | Frame-runner exceptions could leave terminal state active, empty widgets crashed, meters overflowed, and empty `NO_COLOR` was ignored. | Immediate `finally` cleanup with handler restoration, bounded FPS, terminal-resize reconstruction, static `NO_COLOR`/dumb/no-animation modes, empty-widget handling and clamped meters. The image renderer also honors empty `NO_COLOR`/dumb terminals and validates dimensions. |
| P2 | Digest imported project-specific assumptions, scanned console commands outside `[project.scripts]`, depended on discovery order, and produced colliding/unescaped Mermaid identifiers/labels. A missing input looked like an empty successful scan. | Deterministic traversal with directory pruning, package discovery before source analysis, tree-derived import candidates, section-scoped script extraction, hashed diagram IDs/escaped labels, and missing-input rejection. |
| P2 | The supplied source ZIP contained 14 bytecode/cache entries and would become stale after fixes. | Added an explicit-allowlist, atomic package builder; regenerated the ZIP and verified every archived byte against the source. No `.venv`, bytecode or review-evidence directory is included. |

The runtime-contract fixes shipped in **0.7.0**; the current artifact is **0.7.7**: asset-library expansion, license/third-party notices, (0.7.4) the journal-fault correction below plus the unknown-waiting rule, and (0.7.5) the repeatable validation gates and eval suite described at the end. No plugin was globally installed, no repository was initialized, and no commit or publication was performed.

## Validation evidence

Baseline: **22 runtime/UI tests + 6 tool tests passed**. That baseline missed the reproduced defects. Before-fix results are retained in `review-evidence/*-before.txt`: five PTY failures, five runtime failures, seven tool failures/errors, and three digest failures.

Final:

- **40 runtime/driver/digest/integration/UI tests passed on Python 3.12**, and all 40 passed again on **Python 3.10**.
- **13 tool/renderer tests passed on Python 3.10**, with Pillow and numpy available; no skips. No new dependencies were installed during this review.
- The integration test runs **13 synthetic PTY scenarios plus a piped invocation**: check, dry-run, blocked prerequisite, missing input, failed subprocess, Ctrl-C, interactive hidden input/confirmation, plain execution, idempotent rerun, ASCII, empty `NO_COLOR`, light background and the optional Rich path. State-file and journal checks accompany the scenarios. It exercises generated themes and the absent-theme fallback. Rich was available in the Python 3.12 run; the Python 3.10 run exercises the dependency-free fallback.
- Claude Code **2.1.274** strict validation passed separately for the marketplace, plugin manifest, skills and agents.
- All Python source files compile. Digest CLI generated a JSON map and Mermaid text for the skills tree.
- Twelve preview variants (four themes × dark/light/ASCII) were generated; all plain rows fit 80 codepoints, and ASCII previews contain only ASCII. This is geometry/encoding evidence, not a screenshot or universal terminal-width/contrast guarantee.
- The source ZIP is CRC-checked and byte-compared with its allowlisted source files. The package builder is repeatable.

Exact commands, exit statuses, timings and logs are in `review-evidence/validation.json`. `review-evidence/prior-audit.md` and `prior-plugin.zip` preserve the supplied state; `baseline-sha256.json` identifies it.

## Claude Code alignment

Namespaced agent dispatch, plugin-root paths, result waiting, parent-mediated theme selection and fallback when nested spawning is unavailable are appropriate. Current [official subagent documentation](https://code.claude.com/docs/en/sub-agents) supports nesting, with a configurable limit and a default of three layers. It would be incorrect to remove nested delegation based on older “subagents cannot spawn subagents” guidance.

Plugin layout and validation were checked against the [official plugin reference](https://code.claude.com/docs/en/plugins-reference) and the installed validator. Instructions now explicitly preserve a user's prior theme choice or authorization to choose through handoffs, and require artifact paths to be saved before returning control. The product claim is scoped to Claude Code CLI; a source ZIP is not evidence of Cowork compatibility.

## Remaining limits and release gates

Revisited against the **0.7.2** source. This section separates tests that can be closed from documented scope limits. The checks below do not turn every limitation into a release blocker, and they do not imply full certification.

| Original item | Current status | Evidence and remaining work |
|---|---|---|
| **1. Actual agent behavior** | **Smoke CLOSED in 0.7.6 (CI, sandboxed Bash); create/audit still the owner's live run** | An `evals/` suite for `claude plugin eval` now encodes the three workflows (theme pick; harness create on a scaffolded `install.sh` fixture; harness audit of a wizard with planted defects) with trace/tool/file/LLM graders. The smoke case was executed live during the 0.7.5 review (result recorded below). The create and audit cases run real agents for many turns with `--scaffold --allow-tools Bash Write Edit`; they were parsed and loaded by the CLI but not executed here — run them and keep `evals/results/` transcripts. |
| **2. Secret protection / trusted callbacks** | **Documented boundary; not a claim of universal protection** | Known-value redaction tests already cover kit messages, validation, journal details and saved driver output. Child stdout/stderr, direct prints, transformed/undeclared secrets and arbitrary callbacks remain outside that guarantee. Keep this in author guidance; require synthetic-secret leakage checks for each generated harness. No generic “all output is safe” gate is closed. |
| **3. International layout** | **OPEN — compatibility limitation** | Codepoint widths, lossy ASCII conversion and single-cell frame assumptions remain. Wide CJK, combining sequences, embedded ANSI and very narrow terminals are not supported by a complete display-cell layout implementation. Release notes must scope that compatibility; full international layout would require implementation work, not another test count. |
| **4. Visual acceptance** | **PARTIALLY CLOSED** | **48/48 palette-role contrast checks pass** for all eight themes, dark/light palettes, and the documented ink ≥7:1, dim ≥3:1, accent ≥4.5:1 targets against explicit black/white backgrounds. This closes that numeric check only. Real terminal backgrounds, ANSI16/256 mappings, fonts, screenshots, color-count budgets and motion during actual prompts still need visual/integration acceptance. Recipe bloom/scanlines remain inspiration, not executable effects. |
| **5. Digest / Mermaid** | **Documented heuristic scope; renderer check OPEN** | Source extraction remains a navigation aid rather than a complete language parser. Dynamic/relative imports, namespace layouts, multiline/quoted TOML and indirect shell execution require source reading. Diagram identifiers/escaping have regression tests. No local Mermaid package/CLI was found in the checked executable, project-resolution and npm-cache locations; independent Mermaid rendering was not run or claimed. |
| **6. Image renderer** | **Execution/format coverage CLOSED for the tested matrix** | **91/91 cases pass**: seven styles × six dither options × text/HTML = 84 CLI cases, plus seven real-PTY truecolor cases. Checks cover successful execution, exact output geometry, HTML `<pre>` extraction and ANSI foreground output. The four saved art sources and 15 conversions also have dimension/hash evidence. This does not certify every input, palette or visual result, or prove that an accepted flag affects a mode. Halfblock RGB still ignores luminance dither/brightness/contrast/invert/edges as documented; those are scope limits, not newly implemented features. |
| **7. Runtime / cleanup / journal failures** | **CLOSED in 0.7.4 (journal); non-goals unchanged** | Real Rich PTY checks now pass for normal completion (0), stage exception (4) and Ctrl-C during an effect (5), with cursor restoration after the last hide and no traceback. **Journal write failure is now a reproduced defect**, described below. Concurrency, rollback and callback sandboxing remain non-goals; Linux testing does not establish macOS/Windows portability or cleanup of intentionally detached children. |
| **8. License** | **CLOSED — license-document completeness** | At the owner’s request, added standard MIT text in `LICENSE`, copyright 2026 Costa Shafranski (matching the manifest), and `THIRD_PARTY_NOTICES.md` for ASCII Magic attribution and service-specific terms. Both are included in the source ZIP. This closes the missing-document gate, not a comprehensive third-party ownership review. |

### Newly confirmed runtime finding: journal I/O failures escape

**P2 — `skills/cli-harness/scripts/harness_kit.py`, `Journal.write()` and the execution loop in `Harness._main()`.** Injecting an `OSError` into the `start`, `done` and `failed` journal events escapes `Harness.main()` instead of returning its documented error contract. Before `start`, no effect ran; at `done`, the effect completed; at `failed`, the journal error replaces the original stage failure. A conventional uncaught CLI invocation would show a traceback and exit outside the advertised 3/4 contract. A missing/unwritable journal destination or filesystem write failure can trigger this path.

**Correction shipped in 0.7.4 (`harness_kit.py`, `Journal` + `Harness._main()`):** `Journal.write()` never raises; the first `OSError` marks the journal `broken` with a sanitized reason (strerror + path) and no further disk writes are attempted, while events keep accumulating in memory. The execution loop records through one helper that warns once. Policy: an unwritable `start` before any effect → exit 3, nothing ran; after effects started → exit 4, nothing more runs, rerun resumes from probes; an unwritable `done`/`failed`/`ran-unverified` keeps the original outcome and error and the original exit code. A construction-time read error is reported as a warning and earlier events are simply not loaded. `--journal PATH` relocates the file. Six regressions in `test_kit.py::JournalFaults` cover before-start, after-effects, at-done, at-failed, unreadable-at-construction and the flag.

**Also corrected in 0.7.4:** the 0.7.0 rule "an unknown read-only prerequisite blocks the plan" was too broad — a read-only stage whose probe is `unknown` only because a pending predecessor has not run yet (e.g. `data status` before setup created `.venv`) blocked every fresh install with exit 3. Such stages are now `waiting`, exactly as blocked dependants already were, and are re-probed after the predecessor; a genuinely undecidable prerequisite with nothing pending still exits 3. Two regressions added. The `pb` reference harness (22 pty scenarios) passes again on this kit; it needed one `check=False` for a `git checkout` whose return code it interprets itself, consistent with the documented `ctx.sh` compatibility change.

### Evidence and reproduction

Current-source hashes and focused receipts live in `review-evidence/gate-recheck/`:

- `renderer.json` — 91-case matrix, renderer source hash; raw ANSI captures alongside it.
- `contrast.json` — all 48 measured nominal ratios and their targets.
- `runtime.json` — three Rich cleanup passes and three journal fault observations; raw Rich PTY captures alongside it.
- `source-sha256.json` — reviewed source/agent/manifest/asset hashes, excluding bytecode.

Run from the plugin root:

```sh
.venv/bin/python -B review-evidence/gate-recheck/check_renderer.py
python3 -B review-evidence/gate-recheck/check_contrast.py
python3 -B review-evidence/gate-recheck/check_runtime.py
```

The runtime check requires Rich in the selected interpreter and **records the journal defect as an observation**, not as a passing behavior. The renderer check uses the existing Pillow/numpy environment. No dependency installation, live model workflow, global plugin installation or publication was performed. Review evidence is retained in the workspace and excluded from the source ZIP.

**What can actually be crossed off:** the bounded renderer execution/format matrix, the nominal palette contrast calculation, and the three tested Rich progress cleanup paths. **What still gates a stronger release claim:** live agent workflows, real-terminal visual acceptance and journal error handling. License-document completion is now closed. The other items remain explicit compatibility/design limits rather than promises to implement every possible feature.

## Asset follow-up — 0.7.1

Added `skills/tui-design/assets/terminal-study/`: one built-in-imagegen source PNG and three bundled-renderer conversions. PNG inspected; image dimensions and hashes recorded in the asset manifest. All variants verified as 40 columns × 12 rows; ASCII is ASCII-only and the halfblock file contains truecolor foreground/background escapes captured through a PTY. Contrast tuning improves dark-background glyph output; monochrome detail loss remains disclosed. The exact image prompt and reproduction commands ship alongside the assets. The package allowlist now includes PNG/text/ANSI files specifically under the assets directory. This follow-up does not change runtime behavior or close the live-agent/visual-acceptance gaps above.

## Asset-library expansion — 0.7.2

Added Lunar Relay, Nautilus and Voxel Grove, inspired by the ASCII Magic gallery and user-supplied Context.md. Three original built-in-imagegen PNGs, three saved prompts, and 12 deterministic renderer variants (9 text, 3 ANSI). Each source is 1619×971 RGB; compact variants are 40×12 cells and Braille references 80×24. PNG integrity, dimensions, ASCII purity and ANSI foreground/background control sequences were checked. Text variants reproduced byte-for-byte; manifests record source/output hashes and renderer arguments. Source images were visually inspected and compact text conversions read; detail-loss tradeoffs are documented. The catalogue now contains four sets, four source images and 15 conversions. Package contents were compared to disk. This changes assets/documentation only, not runtime capability; no live-agent or real-terminal screenshot certification is implied.

## License follow-up — 0.7.3

Added MIT license text at the owner’s explicit request, using the author name already in the manifest. Reviewed ASCII Magic’s terms (page dated May 25, 2026) and recorded their service-specific content-rights, acceptable-use, warranty/liability and change provisions in a separately scoped third-party notice. These do not alter the standard MIT grant or claim permission to copy ASCII Magic code/gallery material. LICENSE and the notice are packaged and byte-verified; runtime code is unchanged.

## Validation gates and eval suite — 0.7.5

`scripts/check_plugin.py` runs nine independent gates in one command (`--json`, `--skip`, `--only`): the official `claude plugin validate --strict --json` on the plugin manifest, marketplace, `skills/` and `agents/`; a manifest gate of our own; link integrity; compile; every bundled test suite; preview geometry; palette contrast; eval-suite parsing; and the byte-verified package. `.github/workflows/validate.yml` runs it on push and the smoke eval on manual dispatch.

Two facts learned while building it, both now encoded: (1) `claude plugin validate` 2.1.274 lists only components it has findings for and accepted a `SKILL.md` with unparseable YAML and an agent whose `name` did not match its file — so the `manifest` gate parses every frontmatter with PyYAML (fallback: a block-scalar-aware parser) and enforces names, `<example>` blocks, `model`/`color`, and that entry skills dispatch to agents that exist; a negative test (broken skill YAML + renamed agent) passed the official gate and failed ours. (2) Regex graders written with YAML double quotes silently change meaning (`"\b"` is a backspace, `"\."` is an error) — all patterns use single quotes and the `evals` gate parses every grader.

`evals/` holds three cases for `claude plugin eval`: `design-theme-pick` (smoke), `harness-create` (scaffolded `relay/install.sh` fixture → process model, kit harness, scenarios, pty drive; graders check the files, that `drive_harness.py` and `--dry-run`/`--check` actually ran, and an LLM rubric on the hand-back) and `harness-audit` (a wizard with five planted defects: token echoed, no dry-run, exit 0 after failure, no journal, colour-only status; graders require evidence from real runs). The CLI parsed and loaded all three.

**Live evidence (smoke):** `claude plugin eval . --trust-plugin --tag smoke --runs 1 --ablation none` on Claude Code 2.1.274 — score **1.0 (4/4 graders)**, 2 turns, 218 s, $0.44: the request was routed to `tui-designer`, the answer shortlisted noir/slate/blueprint with per-candidate reasons, stated what `NO_COLOR`/piped/ASCII users get, and left the choice to the user. Recorded in `evals/evidence/2026-09-17-smoke.json`. Caveats: the run used the read-only tool set because the review container cannot start the CLI's bubblewrap sandbox (`--allow-tools Bash` was refused, then failed inside the run with a seccomp error); the agent disclosed that it hand-traced `preview_theme.py` instead of executing it. On a machine with a working sandbox the same case should be run with `--allow-tools Bash` so the previews are rendered, and the create/audit cases with `--scaffold --allow-tools Bash Write Edit`; those two remain the owner's live run. Gate 1 above is updated accordingly.

## Live smoke in CI — 0.7.6

`workflow_dispatch` of `validate.yml` on GitHub Actions (ubuntu-latest, bubblewrap sandbox, `--allow-tools Bash`), Claude Code 2.1.274: **score 1.0, 4/4 graders, 11 turns, 214 s, $1.21**. Unlike the 0.7.5 read-only run, the agent executed `preview_theme.py` for noir/slate/blueprint at 80 columns plus `NO_COLOR`, piped and `HARNESS_ASCII=1` variants, measured zero escape sequences in the colourless transcripts, and recommended noir with a reasoned case against blueprint. Recorded in `evals/evidence/2026-09-17-ci-smoke.json`.

The run also did what a live gate is for — it found two defects the synthetic tests had not: in ASCII mode the kit rendered `≥` and the log gutter `│` as `?`, which is the `unknown` mark; and blueprint's Unicode `todo` mark `+` was the ASCII `done` mark, so one glyph meant "not run" on a truecolor terminal and "finished" in a CI log. Both are fixed (`harness_kit._ASCII_MAP`; blueprint `todo` → `•`) with regressions in `test_ui.py` and `test_tools.py` (the latter forbids any Unicode mark equal to a different status's ASCII mark, for every theme). Two earlier CI failures were environmental and are documented in the workflow: the runner image's preinstalled Claude Code 2.1.197 lacks `--json` (the official gate now falls back to text mode), and an org-level API key without workspace scope is rejected by the API (use a workspace-scoped key).
