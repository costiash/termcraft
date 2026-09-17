#!/usr/bin/env python3
"""preview_theme.py — render the harness screens under each theme so a person can pick a look.

    python3 preview_theme.py --name PB                       # every theme, dark background, to the terminal
    python3 preview_theme.py --name PB --theme noir amber    # a subset
    python3 preview_theme.py --name PB --bg light            # light-terminal palettes
    python3 preview_theme.py --name PB --out previews/       # write .ansi color and .txt plain previews per theme
    python3 preview_theme.py --name PB --ascii               # what a non-UTF terminal gets
    python3 preview_theme.py --name PB --cols 80             # at 80 columns

Each preview is the three screens that matter: header + plan, invariants panel + question, progress + outcome.
It is the "show me candidates" step of the tui-designer: pick one, then `make_theme.py` writes theme.py.
"""
from __future__ import annotations

import io, os, re, sys, contextlib, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / "cli-harness" / "scripts"))

def main():
    a = sys.argv[1:]
    def opt(k, d=None): return a[a.index(k) + 1] if k in a else d
    name = opt("--name", "demo"); bg = opt("--bg", "dark"); cols = int(opt("--cols", "100"))
    if "--ascii" in a: os.environ["TERMCRAFT_ASCII"] = "1"; os.environ["HARNESS_ASCII"] = "1"
    os.environ["TERMCRAFT_BG"] = bg; os.environ["HARNESS_BG"] = bg; os.environ["COLUMNS"] = str(cols)
    if "--out" not in a and sys.stdout.isatty(): os.environ.setdefault("COLORTERM", "truecolor")
    import themes, banner
    import harness_kit as k
    k.MODE = "truecolor" if "--out" in a else k._mode(); k.RICH = None; k.TTY = False; k.BACKGROUND = bg; k.UNICODE = k.UNICODE and "--ascii" not in a
    wanted = list(themes.THEMES)
    if "--theme" in a:
        wanted = []
        for x in a[a.index("--theme") + 1:]:
            if x.startswith("--"): break
            wanted.append(x)
    out_dir = Path(opt("--out")) if "--out" in a else None
    for tid in wanted:
        t = themes.THEMES[tid]
        lines = banner.fit(banner.render(name, t.banner, ascii_only=not k.UNICODE), cols, name)
        ui = k.UI(name, banner=lines, theme=t)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ui.header(f"{name} v0.1 · ~/{name.lower()} · theme {t.id} ({bg})")
            ui.plan([(ui.marks["done"], "host: not root, curl|wget", "done", "curl, git"),
                     (ui.marks["done"], "python3 ≥ 3.10", "done", "python 3.12.4"),
                     (ui.marks["blocked"], "Docker Engine + Compose", "blocked", "daemon unreachable  → install Docker Engine + Compose plugin, add your user to docker"),
                     (ui.marks["todo"], "setup-environment.sh", "todo", "environment not configured; .venv absent"),
                     (ui.marks["waiting"], "service .env: required keys", "waiting", "after setup"),
                     (ui.marks["unknown"], "data status (local only)", "unknown", "waiting for setup (.venv)")])
            ui.line("  2 stage(s) to run, ~11 min expected", "dim")
            ui.panel("what never happens", ["contacting production services", "deleting env files, volumes or data", "printing a secret"])
            ui.line("  your name for the branch install/<name> [operator]: ", "ink")
            ui.line("  service password: ", "ink")
            ui.line("  proceed? [Y/n] y", "ink")
            started = time.time() - 37
            sys.stdout.write(f"{ui.s.paint('accent', ui.spin[3])} {'setup-environment.sh'.ljust(28)} {ui.meter(0.62)} {ui.s.paint('dim', '  37s of ~60s')}\n")
            ui.line("  │ == setup environment: uv preflight ==", "dim")
            ui.line("  │ ensure_uv: uv 0.8.17 (reused)", "dim")
            ui.line(f"  {ui.marks['done']} setup-environment.sh  58s", "ok")
            ui.line(f"  {ui.marks['blocked']} service .env failed: SERVICE_PASSWORD invalid → fill the named keys, rerun", "stop")
            ui.rule("successful rerun")
            ui.line(f"  {ui.marks['done']} all stages done", "ok")
            ui.line(f"  {t.recipe}", "dim")
        text = buf.getvalue()
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{tid}-{bg}{'-ascii' if not k.UNICODE else ''}.ansi").write_text(text, encoding="utf-8")
            (out_dir / f"{tid}-{bg}{'-ascii' if not k.UNICODE else ''}.txt").write_text(re.sub(r"\x1b\[[0-9;]*m", "", text))
        else:
            print(text)
            print(("═" if k.UNICODE else "=") * min(cols, 100))
    if out_dir: print(f"wrote {len(wanted)} preview(s) to {out_dir}/")

if __name__ == "__main__": main()
