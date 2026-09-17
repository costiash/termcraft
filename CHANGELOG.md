# Changelog

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
