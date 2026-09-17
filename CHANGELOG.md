# Changelog

## 0.7.9 — 2026-09-18
- First live `harness-create` run in CI (0.7.8): 6/7 graders, 89 turns, $6.08. The architect produced the full deliverable — process model, `relayctl.py` on the kit, noir theme via the designer, 12 pty scenarios (12/12), a real run in the tree, `HARNESS.md` — and timed out at 1800 s re-running scenarios before the hand-back. Evidence: `evals/evidence/2026-09-17-ci-create-0.7.8.json`.
- Kit: plan/progress title column now fits the longest title (was cut at 28 chars); ellipsis when it still overflows.
- Kit + `make_theme.py`: `theme.py` exports `THEME.banner_ascii`; the kit uses it on non-UTF terminals / `HARNESS_ASCII=1` instead of dropping the banner.
- Evals: create/audit `timeout_seconds` 3600, `max_turns` 150; workflow unseals `--keep-temp` dirs so the sandbox archive contains what the agent wrote.

## 0.7.8 — 2026-09-18
- `banner.py` block style: the ╗╝ shadow was malformed (`████████╗ ╝`, a stray row of `╝`), flagged by two live eval runs. Rewritten as proper ANSI-shadow geometry (╗ ║ ╝ ╚ ═ ╔ from ink adjacency); letters now read cleanly.
- Third CI smoke run on 0.7.7: 1.0 (`evals/evidence/2026-09-18-ci-smoke-0.7.7.json`).

## 0.7.7 — 2026-09-18
- Second live smoke run on 0.7.6 in CI: score 1.0, 9 turns, 19 renderings, ASCII fix confirmed live (`evals/evidence/2026-09-18-ci-smoke-0.7.6.json`).
- noir light palette: `dim` was the dark value (4.6:1 on white); now `#5f584c` (7.0:1).

## 0.7.6 — 2026-09-18
- Live smoke eval passed in GitHub Actions with the Bash sandbox (score 1.0, 11 turns, previews actually rendered; `evals/evidence/2026-09-17-ci-smoke.json`). The run surfaced two real defects, both fixed with regressions:
  - `harness_kit.py` ASCII mode turned `≥`, `≤`, `│`, `─` into `?` — the *unknown* mark. Now `>=`, `<=`, `|`, `-` (plus box/meter glyphs).
  - blueprint's Unicode `todo` mark was `+`, which is the ASCII `done` mark: same glyph, opposite meaning across terminals. Now `•`; a theme test forbids any such cross-terminal collision.

## 0.7.5 — 2026-09-17
- Official gate falls back to text mode on CLIs without `--json` (GitHub's ubuntu image ships 2.1.197); workflow installs the current CLI and puts it first on PATH.
- `scripts/check_plugin.py`: nine CI-grade gates in one command (official `claude plugin validate --strict`, manifest, links, compile, tests, previews, contrast, evals, package); `--json`, `--skip`, `--only`.
- `evals/`: three `claude plugin eval` cases (theme pick smoke, harness create on a scaffolded fixture, harness audit of a wizard with planted defects). Smoke case executed live: 4/4 graders (`evals/evidence/`).
- `.github/workflows/validate.yml`: gates on every push; smoke eval on manual dispatch (needs `ANTHROPIC_API_KEY`).
- Manifests carry repository/homepage; packager includes evals and CI files.

## 0.7.4
- `harness_kit.py`: journal I/O failures no longer escape `main()` — unwritable `start` exits 3 before effects / 4 after; `--journal PATH`.
- Waiting rule extended to `unknown` stages with pending predecessors (fixes fresh installs blocking on not-yet-created state).

## 0.7.3
- MIT `LICENSE`, `THIRD_PARTY_NOTICES.md`.

## 0.7.1 – 0.7.2
- Asset library: terminal-study, lunar-relay, nautilus, voxel-grove sources and renderer variants.

## 0.7.0
- Runtime contract fixes from the Copilot/Codex review: `ran-unverified` exit 4, `Context.sh(check=True)` default, Rich cleanup paths.

## 0.6.0
- Renamed to termcraft; web UI/UX skill and layout-designer agent removed; theme bank (8 themes × dark/light/ansi16/ASCII), banner font, previews, `make_theme.py`.

## 0.5.x
- cli-harness skill and harness-architect agent: digest → connection map → process model → resumable harness on `harness_kit.py`; pty driver; audit mode. 0.5.1 fixed the 21 Codex findings.
