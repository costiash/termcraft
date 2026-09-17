#!/usr/bin/env python3
"""harness_kit.py — runtime for generated CLI harnesses (stdlib only, Python ≥ 3.10).

A harness is a finite state machine over *stages*. Each stage declares:
  probe()   → Verdict        what is true right now (idempotent, side-effect free, fast)
  run(ctx)  → None           the effect, only executed when the probe says it is needed (never in --dry-run)
  describe(ctx) → [str]      what run() would do, for --dry-run (use ctx.would([...]) for commands)
  needs     → [stage ids]    stages that must be `done` first
  ask       → [Question]     inputs collected before run, only when the probe cannot supply them
  expect_s  → float          expected duration, shown to the person
The runner: probes selected stages → shows the plan → asks → confirms once → executes in order →
journals transitions → exits with a documented code. Resume re-probes real state; answers are not
persisted. Non-TTY runs need --yes and answers from env / --answer / defaults; NO_COLOR disables colour.

Design rules baked in (see references/harness-design.md): probe before ask; ask once; secrets
hidden and never echoed or journaled; every failure names the stage and the fix; --dry-run and
--check never change anything; --yes for unattended runs; exit codes are a contract.

Copy this file next to the generated harness (or vendor it) — the harness imports it.
"""
from __future__ import annotations

import atexit
import dataclasses
import getpass
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------- exit codes (contract)
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PRECONDITION = 3      # a probe found the machine/env unfit; nothing changed
EXIT_STAGE_FAILED = 4      # a stage ran and failed; journal names it; rerun resumes
EXIT_ABORTED = 5           # person declined / Ctrl-C
EXIT_MISSING_INPUT = 6     # unattended run lacked an answer

# ---------------------------------------------------------------- terminal capability ladder
def _mode() -> str:
    if "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb" or not sys.stdout.isatty():
        return "none"
    if os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return "truecolor"
    if "256color" in os.environ.get("TERM", ""):
        return "256"
    return "16"

MODE = _mode()
TTY = sys.stdin.isatty() and sys.stdout.isatty()

# Optional richer rendering: if `rich` is importable and we are on a TTY, plan/progress/prompts use it.
# Never required — an installer must work before any environment exists. Disable with HARNESS_PLAIN=1.
try:
    if TTY and not os.environ.get("HARNESS_PLAIN") and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb" and os.environ.get("HARNESS_ASCII") != "1" and os.environ.get("TERMCRAFT_ASCII") != "1":
        from rich.text import Text as _RichText
        from rich.console import Console as _RichConsole  # type: ignore
        from rich.table import Table as _RichTable          # type: ignore
        from rich.panel import Panel as _RichPanel          # type: ignore
        from rich.progress import Progress as _RichProgress, BarColumn as _Bar, TextColumn as _Txt, TimeElapsedColumn as _Elapsed  # type: ignore
        from rich.prompt import Prompt as _RichPrompt, Confirm as _RichConfirm  # type: ignore
        RICH = _RichConsole(highlight=False)
    else:
        RICH = None
except Exception:
    RICH = None

def _background() -> str:
    """'light' | 'dark'. COLORFGBG ('fg;bg', 7/15 = light) or HARNESS_BG / TERMCRAFT_BG; default dark."""
    for k in ("HARNESS_BG", "TERMCRAFT_BG"):
        if os.environ.get(k) in ("light", "dark"): return os.environ[k]
    v = os.environ.get("COLORFGBG", "")
    if ";" in v and v.split(";")[-1].isdigit(): return "light" if int(v.split(";")[-1]) in (7, 15) else "dark"
    return "dark"

BACKGROUND = _background()
UNICODE = "utf" in (sys.stdout.encoding or "").lower() and os.environ.get("HARNESS_ASCII") != "1" and os.environ.get("TERMCRAFT_ASCII") != "1"

class Style:
    """Six colour roles (ink, dim, accent, ok, warn, stop). Accepts a palette dict, or a termcraft Theme
    (themes.py) — then the light-background variant and the 16-colour fallbacks come from the theme."""
    DEFAULT = {"ink": "#d7dde3", "dim": "#7b8590", "accent": "#9bbc0f", "ok": "#8bac0f", "warn": "#e0b04a", "stop": "#e06b6b"}
    ANSI16 = {"ink": ("37", "30"), "dim": ("90", "90"), "accent": ("36", "34"), "ok": ("32", "32"), "warn": ("33", "33"), "stop": ("31", "31")}
    def __init__(self, palette: dict[str, str] | None = None, theme=None, background: str | None = None):
        bg = background or BACKGROUND
        self.p = dict(self.DEFAULT); self.a16 = dict(self.ANSI16); self.background = bg
        if theme is not None:
            self.p.update(theme.roles(bg)); self.a16.update(getattr(theme, "ansi16", {}))
        if palette: self.p.update(palette)
    def fg(self, role: str) -> str:
        if MODE == "none": return ""
        h = self.p.get(role, self.p["ink"]).lstrip("#"); r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
        if MODE == "truecolor": return f"\x1b[38;2;{r};{g};{b}m"
        if MODE == "256":
            index = 16 + 36 * round(r / 51) + 6 * round(g / 51) + round(b / 51)
            return f"\x1b[38;5;{index}m"
        pair = self.a16.get(role, self.a16["ink"]); return f"\x1b[{pair[1] if self.background == 'light' else pair[0]}m"
    @property
    def reset(self): return "" if MODE == "none" else "\x1b[0m"
    @property
    def bold(self): return "" if MODE == "none" else "\x1b[1m"
    def paint(self, role: str, text: str) -> str: return f"{self.fg(role)}{text}{self.reset}"

BOX = {"light": "┌─┐│└┘", "rounded": "╭─╮│╰╯", "heavy": "┏━┓┃┗┛", "double": "╔═╗║╚╝", "ascii": "+-+|++"}
METER = "█▓▒░"
SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
MARKS = {"done": "✓", "todo": "•", "blocked": "✗", "unknown": "?", "waiting": "…", "skip": "·"}
ASCII_GLYPHS = {"box": "ascii", "meter": "#=-.", "spinner": "|/-\\", "rule": "-",
                "marks": {"done": "+", "todo": "*", "blocked": "x", "unknown": "?", "waiting": "~", "skip": "-"}}

def _text(text: str) -> str:
    if UNICODE: return text
    return text.translate(_ASCII_MAP).encode("ascii", "replace").decode("ascii")

# Stage text written by harness authors often carries comparison and drawing glyphs; map the common ones to
# unambiguous ASCII instead of letting them fall through to "?" (which is the `unknown` mark).
_ASCII_MAP = str.maketrans({"✓": "+", "✗": "x", "•": "*", "→": "->", "←": "<-", "—": "-", "–": "-", "…": "...", "·": ".",
                            "≥": ">=", "≤": "<=", "≠": "!=", "±": "+/-", "×": "x", "│": "|", "┃": "|", "─": "-", "━": "-",
                            "├": "|", "└": "`", "┌": "+", "┐": "+", "┘": "+", "╭": "+", "╮": "+", "╰": "+", "╯": "+",
                            "█": "#", "▓": "=", "▒": "-", "░": ".", "“": '"', "”": '"', "‘": "'", "’": "'"})

def cols() -> int: return min(120, shutil.get_terminal_size((80, 24)).columns)

# ---------------------------------------------------------------- model
@dataclass
class Verdict:
    """What a probe found. `status`: done | todo | blocked | unknown."""
    status: str
    detail: str = ""
    fix: str = ""                     # for blocked: what the person must do (actionable, one line)
    facts: dict[str, Any] = field(default_factory=dict)   # values the probe learned (answers it can supply)
    def __post_init__(self):
        if self.status not in {"done", "todo", "blocked", "unknown", "skip"}:
            raise ValueError(f"invalid probe status: {self.status}")

@dataclass
class Question:
    key: str
    prompt: str
    secret: bool = False
    default: str | None = None
    validate: Callable[[str], str | None] | None = None   # returns error text or None
    env: str | None = None                                 # env var that answers it unattended

@dataclass
class Stage:
    id: str
    title: str
    probe: Callable[["Context"], Verdict]
    run: Callable[["Context"], None] | None = None
    needs: list[str] = field(default_factory=list)
    ask: list[Question] = field(default_factory=list)
    expect_s: float = 0
    never: list[str] = field(default_factory=list)         # invariants shown in the plan ("what never happens")
    describe: Callable[["Context"], list[str]] | None = None  # dry-run: what `run` WOULD do (commands/paths). run() is never called in dry-run.

@dataclass
class Context:
    root: Path
    answers: dict[str, str]
    journal: "Journal"
    ui: "UI"
    dry_run: bool = False
    secrets: set[str] = field(default_factory=set)         # answer keys whose values must never be printed
    def redact(self, text: str) -> str: return _redact(text, self.answers, self.secrets)
    def would(self, cmd: list[str]) -> str:
        """For Stage.describe: the redacted command line that run() would execute."""
        return "would run: " + self.redact(" ".join(cmd))
    def sh(self, cmd: list[str], **kw) -> subprocess.CompletedProcess:
        """Run a command under the current stage. In dry-run it refuses (run() is not called in dry-run; use Stage.describe)."""
        if self.dry_run:
            raise RuntimeError("ctx.sh called during dry-run — declare Stage.describe instead of executing")
        self.ui.line(f"  $ {self.redact(' '.join(cmd))}", "dim")
        return subprocess.run(cmd, cwd=kw.pop("cwd", self.root), text=True, check=kw.pop("check", True), **kw)

# ---------------------------------------------------------------- journal (resume + audit)
class Journal:
    """Append-only JSONL record of stage transitions. Fault-tolerant: an unreadable file is reported, not fatal; an
    unwritable file breaks the journal ONCE (`broken` holds a sanitized reason) and no further disk writes are attempted —
    events keep accumulating in memory so the run can still report. Probes, not the journal, are the truth for resume."""
    def __init__(self, path: Path):
        self.path = path; self.events: list[dict] = []; self.broken: str | None = None; self.read_error: str | None = None
        try:
            if path.exists():
                for ln in path.read_text().splitlines():
                    try: self.events.append(json.loads(ln))
                    except json.JSONDecodeError: pass
        except OSError as e:
            self.read_error = f"{e.strerror or e.__class__.__name__}: {path}"
    def write(self, **ev) -> bool:
        """Record an event. Returns False (once broken, always False) when the file cannot be written; never raises."""
        ev["t"] = time.strftime("%Y-%m-%dT%H:%M:%S"); self.events.append(ev)
        if self.broken: return False
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as f: f.write(json.dumps(ev) + "\n")
            return True
        except OSError as e:
            self.broken = f"{e.strerror or e.__class__.__name__}: {self.path}"
            return False
    def last(self, stage: str) -> dict | None:
        for ev in reversed(self.events):
            if ev.get("stage") == stage: return ev
        return None

# ---------------------------------------------------------------- UI
class UI:
    """Renders every screen. Pass a termcraft Theme (themes.py) to take palette, box weight and glyph sets from it;
    or a Style + banner + box by hand. Non-UTF terminals (or HARNESS_ASCII=1) get the ASCII glyph set automatically."""
    def __init__(self, name: str, style: Style | None = None, banner: list[str] | None = None, box: str = "rounded", theme=None):
        self.name = name; self.spin_i = 0
        g = getattr(theme, "glyphs", None)
        self.s = style or Style(theme=theme)
        self.banner = banner or []
        if not UNICODE:
            self.box = BOX["ascii"]; self.meter_ramp = ASCII_GLYPHS["meter"]; self.spin = ASCII_GLYPHS["spinner"]; self.marks = ASCII_GLYPHS["marks"]; self.rule_ch = "-"
            self.banner = [ln for ln in self.banner if all(ord(c) < 128 for c in ln)] or [name.upper()]
        else:
            self.box = BOX[getattr(theme, "box", None) or box]
            self.meter_ramp = g.meter if g else METER; self.spin = g.spinner if g else SPIN
            self.marks = dict(g.marks) if g else dict(MARKS); self.rule_ch = g.rule if g else "─"
        if TTY:
            sys.stdout.write("\x1b[?25l"); atexit.register(self.close); sys.stdout.flush()
    def close(self):
        if getattr(self, "_rp", None):
            self._rp.stop(); self._rp = None
        if TTY:
            sys.stdout.write("\x1b[?25h" + self.s.reset); sys.stdout.flush()
        atexit.unregister(self.close)
    def line(self, text: str = "", role: str = "ink"):
        """Print one message, wrapped to the terminal width with a hanging indent equal to its leading spaces."""
        import textwrap
        text = _text(text)
        indent = len(text) - len(text.lstrip(" ")); width = max(24, cols())
        parts = textwrap.wrap(text, width, subsequent_indent=" " * (indent + 4), drop_whitespace=False) or [text]
        for part in parts: print(self.s.paint(role, part) if role != "ink" else part)
    def rule(self, title: str = ""):
        w = cols(); t = f" {title} " if title else ""
        print(self.s.paint("dim", self.rule_ch * 2 + t + self.rule_ch * max(0, w - 2 - len(t))))
    def header(self, subtitle: str = ""):
        banner = self.banner
        if any(len(line) > cols() for line in banner):
            banner = [self.name.upper()[:cols()]]
        for ln in banner: self.line(ln, "accent")
        if subtitle: self.line(subtitle, "dim")
        print()
    def panel(self, title: str, rows: list[str], role: str = "dim"):
        title, rows = _text(title), [_text(row) for row in rows]
        if RICH:
            RICH.print(_RichPanel(_RichText("\n".join(rows)), title=_RichText(title), border_style=self.s.p.get(role, "#7b8590"), expand=False)); return
        import textwrap
        tl, hz, tr, vt, bl, br = self.box
        w = max(6, min(cols(), max([len(title) + 6, *(len(r) + 4 for r in rows)])))
        label = f" {title[:w - 6]} "
        print(self.s.paint(role, tl + hz + label + hz * (w - 3 - len(label)) + tr))
        for row in rows:
            for logical_line in row.splitlines() or [""]:
                for part in textwrap.wrap(logical_line, width=w - 4) or [""]:
                    print(self.s.paint(role, vt) + " " + part.ljust(w - 4) + " " + self.s.paint(role, vt))
        print(self.s.paint(role, bl + hz * (w - 2) + br))
    def plan(self, rows: list[tuple[str, str, str, str]]):
        """rows: (mark, title, status, detail)"""
        if RICH:
            t = _RichTable(title="plan", show_header=True, header_style="dim", box=None, pad_edge=False)
            for c in ("", "stage", "status", "detail"): t.add_column(c)
            for mark, title, status, detail in rows:
                col = {"done": self.s.p["ok"], "todo": self.s.p["accent"], "blocked": self.s.p["stop"], "unknown": self.s.p["warn"], "waiting": self.s.p["dim"], "skip": self.s.p["dim"]}.get(status, self.s.p["ink"])
                t.add_row(_RichText(mark, style=col), _RichText(title), _RichText(status, style=col), _RichText(detail, style=self.s.p["dim"]))
            RICH.print(t); return
        self.rule("plan")
        for mark, title, status, detail in rows:
            mark, title, status, detail = map(_text, (mark, title, status, detail))
            role = {"done": "ok", "todo": "accent", "blocked": "stop", "unknown": "warn", "waiting": "dim", "skip": "dim"}.get(status, "ink")
            import textwrap
            lead = 1 + len(mark) + 1 + 28 + 1 + 8 + 1; width = max(20, cols() - lead)
            parts = textwrap.wrap(detail, width) or [""]
            print(f" {self.s.paint(role, mark)} {title[:28].ljust(28)} {self.s.paint(role, status.ljust(8))} {self.s.paint('dim', parts[0])}")
            for extra in parts[1:]: print(" " * lead + self.s.paint("dim", extra))
        self.rule()
    def meter(self, frac: float, width: int = 30) -> str:
        full = int(frac * width); return self.meter_ramp[0] * full + self.meter_ramp[-1] * (width - full)
    def progress(self, title: str, started: float, expect: float, done: bool = False, failed: bool = False):
        if not TTY: return
        title = _text(title)
        if RICH:
            if done:
                if getattr(self, "_rp", None): self._rp.update(self._rt, completed=0 if failed else 100); self._rp.stop(); self._rp = None
                RICH.print(f"{'failed' if failed else 'done'}: {title}  {time.time()-started:.0f}s", markup=False)
                return
            if not getattr(self, "_rp", None):
                self._rp = _RichProgress(_Txt("[progress.description]{task.description}"), _Bar(bar_width=30, complete_style=self.s.p["accent"]), _Txt("{task.percentage:>3.0f}%"), _Elapsed(), console=RICH, transient=True)
                self._rp.start(); self._rt = self._rp.add_task(title, total=100)
            el = time.time() - started; self._rp.update(self._rt, completed=min(97, el / expect * 100) if expect else 0)
            return
        el = time.time() - started; frac = 0.0 if failed else 1.0 if done else min(0.97, el / expect) if expect else 0
        self.spin_i += 1; sp = " " if done else self.spin[self.spin_i % len(self.spin)]
        tail = f"{el:4.0f}s" + (f" of ~{expect:.0f}s" if expect and not done else "")
        sys.stdout.write("\r" + self.s.paint("accent", sp) + " " + title.ljust(28) + " " + self.meter(frac) + " " + self.s.paint("dim", tail) + ("\n" if done else "")); sys.stdout.flush()
    def ask(self, q: Question, unattended: bool) -> str | None:
        """Answer from env or default (validated) or the person. Returns None when nothing valid is available unattended."""
        for cand in (os.environ.get(q.env) if q.env else None, None if TTY and not unattended else q.default):
            if cand is None: continue
            err = q.validate(cand) if q.validate else None
            if err:
                message = _redact(str(err), {q.key: cand}, {q.key} if q.secret else set())
                self.line(f"  {q.key}: {message} (value from {'env ' + q.env if cand == os.environ.get(q.env or '') else 'default'})", "warn")
                continue
            return cand
        if unattended or not TTY: return None
        sys.stdout.write("\x1b[?25h"); sys.stdout.flush()          # cursor visible while the person types
        try: return self._ask_loop(q)
        finally: sys.stdout.write("\x1b[?25l"); sys.stdout.flush()
    def _ask_loop(self, q: Question) -> str | None:
        while True:
            if RICH:
                v = _RichPrompt.ask(_RichText(f"  {q.prompt}"), password=q.secret, default=q.default if (q.default is not None and not q.secret) else None, show_default=not q.secret)
                v = (v or q.default or "").strip()
                err = q.validate(v) if q.validate else None
                if err:
                    self.line("    " + _redact(str(err), {q.key: v}, {q.key} if q.secret else set()), "warn")
                    continue
                return v
            suffix = f" [{q.default}]" if q.default is not None and not q.secret else ""
            try:
                v = getpass.getpass(f"  {_text(q.prompt)}: ") if q.secret else input(f"  {_text(q.prompt)}{_text(suffix)}: ")
            except EOFError: return None
            v = v.strip() or (q.default or "")
            err = q.validate(v) if q.validate else None
            if err:
                self.line("    " + _redact(str(err), {q.key: v}, {q.key} if q.secret else set()), "warn")
                continue
            return v
    def confirm(self, prompt: str, unattended: bool) -> bool:
        if unattended or not TTY: return True
        sys.stdout.write("\x1b[?25h"); sys.stdout.flush()
        if RICH:
            try: return _RichConfirm.ask(_RichText(f"  {prompt}"), default=True)
            finally: sys.stdout.write("\x1b[?25l"); sys.stdout.flush()
        try: return input(f"  {prompt} [Y/n] ").strip().lower() in ("", "y", "yes")
        except EOFError: return False
        finally: sys.stdout.write("\x1b[?25l"); sys.stdout.flush()

# ---------------------------------------------------------------- runner
class Harness:
    def __init__(self, name: str, stages: list[Stage], root: Path, ui: UI, journal_path: Path | None = None, version: str = "0.1"):
        self.name, self.stages, self.root, self.ui, self.version = name, stages, root, ui, version
        self.by_id = {s.id: s for s in stages}
        if len(self.by_id) != len(stages):
            raise ValueError("duplicate stage IDs; each stage must have a unique ID")
        for stage in stages:
            for need in stage.needs:
                if need not in self.by_id:
                    raise ValueError(f"stage {stage.id}: missing dependency {need}")
        self.journal = Journal(journal_path or root / ".harness" / f"{name}.jsonl")
        order = []; seen = set(); visiting = set()
        def visit(s: Stage):
            if s.id in seen: return
            if s.id in visiting: raise ValueError(f"dependency cycle at stage {s.id}")
            visiting.add(s.id)
            for n in s.needs: visit(self.by_id[n])
            visiting.remove(s.id)
            seen.add(s.id); order.append(s)
        for s in stages: visit(s)
        self.order = order

    # -- CLI surface every harness shares
    def main(self, argv: list[str] | None = None) -> int:
        previous_sigint = signal.getsignal(signal.SIGINT)
        try:
            return self._main(argv)
        except KeyboardInterrupt:
            self.ui.line("  aborted", "warn")
            return EXIT_ABORTED
        finally:
            signal.signal(signal.SIGINT, previous_sigint)
            self.ui.close()

    def _main(self, argv: list[str] | None = None) -> int:
        import argparse
        p = argparse.ArgumentParser(prog=self.name, description=f"{self.name} — guided operator harness (v{self.version})",
            epilog="exit codes: 0 ok · 2 usage · 3 precondition (nothing changed) · 4 stage failed (rerun resumes) · 5 aborted · 6 missing input (unattended)")
        p.add_argument("--check", action="store_true", help="probe every stage and report; change nothing")
        p.add_argument("--dry-run", action="store_true", help="show the plan and what each stage would run; change nothing")
        p.add_argument("--yes", "-y", action="store_true", help="unattended: no prompts; answers from env/--answer; missing → exit 6")
        p.add_argument("--answer", action="append", default=[], metavar="KEY=VALUE", help="pre-supply an answer")
        p.add_argument("--only", metavar="STAGE", help="run one stage (and its needs)")
        p.add_argument("--from", dest="from_stage", metavar="STAGE", help="skip every stage before STAGE (their probes are not consulted)")
        p.add_argument("--stages", action="store_true", help="list stages and exit")
        p.add_argument("--journal", metavar="PATH", help=f"where to record stage transitions (default: <root>/.harness/{self.name}.jsonl)")
        a = p.parse_args(argv)
        if a.journal: self.journal = Journal(Path(a.journal).expanduser())
        if self.journal.read_error: self.ui.line(f"  journal unreadable ({self.journal.read_error}); earlier events are not loaded", "warn")
        if a.stages:
            for s in self.order: print(f"{s.id:<24} {s.title}  needs={','.join(s.needs) or '-'}")
            return EXIT_OK
        if a.from_stage and a.from_stage not in self.by_id: self._closure(a.from_stage)   # same did-you-mean path
        if a.only and a.from_stage: p.error("--only and --from cannot be combined")
        if any("=" not in kv or not kv.split("=", 1)[0] for kv in a.answer):
            p.error("--answer requires KEY=VALUE")
        answers = dict(kv.split("=", 1) for kv in a.answer if "=" in kv)
        secrets = {q.key for st in self.stages for q in st.ask if q.secret}
        ctx = Context(self.root, answers, self.journal, self.ui, dry_run=a.dry_run, secrets=secrets)
        if any(k in secrets for k in answers): self.ui.line("  note: secrets passed on the command line are visible in shell history and `ps`; prefer the env variable or the prompt", "warn")
        signal.signal(signal.SIGINT, signal.default_int_handler)
        self.ui.header(f"{self.name} v{self.version} · {self.root}")

        # 1. probe everything → plan
        def probe(st: Stage) -> Verdict:
            try:
                v = st.probe(ctx)
                if not isinstance(v, Verdict) or v.status == "skip":
                    raise ValueError("probe must return done, todo, blocked or unknown Verdict")
            except Exception as e: v = Verdict("unknown", f"probe failed: {ctx.redact(str(e))}")
            for k, val in v.facts.items(): answers.setdefault(k, str(val))
            return v
        if a.from_stage:
            idx = [st.id for st in self.order].index(a.from_stage)
            selected = self.order[idx:]                      # skipped predecessors are not probed
        else:
            selected = self.order if not a.only else self._closure(a.only)
        selected_ids = {st.id for st in selected}
        verdicts: dict[str, Verdict] = {
            st.id: probe(st) if st.id in selected_ids else Verdict("skip")
            for st in self.order
        }
        # a stage blocked (or unknown) only because a pending predecessor has not run yet is "waiting", not a precondition failure
        waiting_ids = set()
        for st in selected:
            if verdicts[st.id].status in ("blocked", "unknown") and any(
                n in selected_ids and (verdicts[n].status in ("todo", "unknown") or n in waiting_ids)
                for n in st.needs
            ):
                waiting_ids.add(st.id)
        def waiting(st: Stage) -> bool:
            return st.id in waiting_ids
        rows = []
        for st in self.order:
            v = verdicts[st.id]; status = v.status if st in selected else "skip"
            if st in selected and waiting(st): status = "waiting"
            mark = self.ui.marks.get(status, "?")
            rows.append((mark, st.title, status, ctx.redact(v.detail + (f"  → {v.fix}" if v.fix and status == "blocked" else ""))))
        self.ui.plan(rows)
        # exit 3: a real precondition failure, or a read-only stage whose probe cannot decide and that has nothing pending to wait for
        blocked = [st for st in selected if not waiting(st) and (verdicts[st.id].status == "blocked" or (verdicts[st.id].status == "unknown" and st.run is None))]
        if blocked:
            self.ui.line("  blocked — fix the items marked ✗ and rerun; nothing was changed", "stop"); return EXIT_PRECONDITION
        todo = [st for st in selected if verdicts[st.id].status in ("todo", "unknown") or waiting(st)]
        if a.check or not todo:
            self.ui.line("  nothing to do" if not todo else f"  {len(todo)} stage(s) pending", "dim"); return EXIT_OK
        total = sum(st.expect_s for st in todo)
        self.ui.line(f"  {len(todo)} stage(s) to run, ~{total/60:.0f} min expected" if total >= 90 else f"  {len(todo)} stage(s) to run", "dim")
        nevers = sorted({n for st in todo for n in st.never})
        if nevers: self.ui.panel("what never happens", nevers)

        # 2. questions (only those the probes could not answer); every answer is validated whatever its source
        for st in todo:
            for q in st.ask:
                if q.key in answers:
                    err = q.validate(answers[q.key]) if q.validate else None
                    if not err: continue
                    self.ui.line(ctx.redact(f"  {q.key}: {err} (value from {'--answer' if q.key in dict(kv.split('=',1) for kv in a.answer if '=' in kv) else 'a probe'})"), "warn")
                    if a.yes or not TTY:
                        self.ui.line(f"  invalid input: {q.key}", "stop"); return EXIT_MISSING_INPUT
                    del answers[q.key]
                v = self.ui.ask(q, a.yes)
                if v is None:
                    self.ui.line(f"  missing input: {q.key}" + (f" (set {q.env})" if q.env else ""), "stop"); return EXIT_MISSING_INPUT
                answers[q.key] = v
        if not a.dry_run:
            if not TTY and not a.yes:
                self.ui.line("  not a terminal and --yes not given: nothing was run (pass --yes to execute unattended)", "stop"); return EXIT_MISSING_INPUT
            if not self.ui.confirm("proceed?", a.yes): return EXIT_ABORTED

        # 3. execute (dry-run never calls run(); it prints Stage.describe)
        effects_started = False
        journal_warned = False
        def record(**ev) -> bool:
            """Journal an event; on the first failure say so once (sanitized). Never raises; never retries a broken path."""
            nonlocal journal_warned
            ok = self.journal.write(**ev)
            if not ok and not journal_warned:
                journal_warned = True
                self.ui.line(f"  journal unwritable ({self.journal.broken}); this run is not being recorded — pass --journal PATH or fix the location", "warn")
            return ok
        for st in todo:
            if a.dry_run:
                self.ui.line(f"• {st.title}", "accent")
                try: lines = st.describe(ctx) if st.describe else ([f"would run stage `{st.id}` (no describe() declared)"] if st.run else [])
                except Exception as e:
                    self.ui.line(f"describe failed: {ctx.redact(str(e))}", "stop")
                    return EXIT_USAGE
                for ln in lines: self.ui.line("  " + ctx.redact(ln), "dim")
                continue
            now = probe(st)                                   # re-probe: an earlier stage may have done this one's work
            if now.status == "done":
                self.ui.line(f"  ✓ {st.title}  already done", "dim"); continue
            if now.status == "blocked":
                record(stage=st.id, event="blocked", detail=ctx.redact(now.detail))
                self.ui.line(ctx.redact(f"  ✗ {st.title} blocked: {now.detail}" + (f"  → {now.fix}" if now.fix else "")), "stop")
                return EXIT_STAGE_FAILED if effects_started else EXIT_PRECONDITION
            started = time.time()
            if not record(stage=st.id, event="start"):
                # refuse to start an effect that cannot be recorded; say exactly what state the machine is in
                if effects_started:
                    self.ui.line(f"  ✗ {st.title} not started: earlier stages ran, the journal cannot record this one; rerun resumes from probes", "stop")
                    return EXIT_STAGE_FAILED
                self.ui.line(f"  ✗ {st.title} not started; nothing was changed", "stop")
                return EXIT_PRECONDITION
            self.ui.progress(st.title, started, st.expect_s)
            try:
                if st.run:
                    effects_started = True
                    st.run(ctx)
                after = probe(st)
                if after.status in ("blocked", "todo"):
                    raise RuntimeError(after.detail or "stage ran but its probe still reports work pending")
            except Exception as e:
                self.ui.progress(st.title, started, st.expect_s, done=True, failed=True)
                record(stage=st.id, event="failed", error=ctx.redact(str(e)))       # the original error is reported whatever the journal does
                self.ui.line(f"  ✗ {st.title} failed: {ctx.redact(str(e))}", "stop")
                self.ui.line(f"    rerun `{self.name}` to resume from this stage; journal: {self.journal.path}", "dim")
                return EXIT_STAGE_FAILED
            self.ui.progress(st.title, started, st.expect_s, done=True, failed=after.status == "unknown")
            if after.status == "unknown":
                record(stage=st.id, event="ran-unverified", detail=ctx.redact(after.detail), seconds=round(time.time() - started, 1))
                self.ui.line(f"  ? {st.title} ran, but its probe cannot confirm the result: {ctx.redact(after.detail)}; fix the probe and rerun", "warn")
                return EXIT_STAGE_FAILED
            else:
                record(stage=st.id, event="done", seconds=round(time.time() - started, 1))
        self.ui.line("  dry run complete — nothing was changed" if a.dry_run else "  ✓ all stages done", "ok")
        return EXIT_OK

    def _closure(self, stage_id: str) -> list[Stage]:
        if stage_id not in self.by_id:
            import difflib
            near = difflib.get_close_matches(stage_id, list(self.by_id), n=1, cutoff=0.6)
            self.ui.line(f"unknown stage {stage_id}" + (f" — did you mean {near[0]}?" if near else f"; stages: {', '.join(self.by_id)}"), "stop"); sys.exit(EXIT_USAGE)
        out: list[Stage] = []
        def visit(s: Stage):
            for n in s.needs: visit(self.by_id[n])
            if s not in out: out.append(s)
        visit(self.by_id[stage_id]); return out

def _redact(text: str, answers: dict[str, str], secrets: set[str] = frozenset()) -> str:
    """Remove every secret answer from text. A key is secret if its Question said so (preferred) or by name heuristic."""
    values = {v for k, v in answers.items() if v and
              (k in secrets or any(t in k.lower() for t in ("pass", "secret", "key", "salt", "token", "cred")))}
    if values:
        pattern = "|".join(re.escape(v) for v in sorted(values, key=len, reverse=True))
        text = re.sub(pattern, lambda match: "[redacted]", text)
    return re.sub(r"(password|pwd)=([^\s&]+)", r"\1=[redacted]", text, flags=re.I)

# ---------------------------------------------------------------- common probes
def which(cmd: str) -> str | None: return shutil.which(cmd)

def probe_command(cmd: str, fix: str, version_args: list[str] | None = None, min_version: tuple[int, ...] | None = None) -> Verdict:
    path = which(cmd)
    if not path: return Verdict("blocked", f"{cmd} not found", fix)
    if version_args and min_version:
        try:
            result = subprocess.run([cmd, *version_args], capture_output=True, text=True, timeout=10)
            if result.returncode: return Verdict("unknown", f"{cmd} version check exited {result.returncode}", fix)
            out = result.stdout + result.stderr
            m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", out); ver = tuple(int(x) for x in m.groups() if x) if m else ()
            if not ver: return Verdict("unknown", f"{cmd} version could not be parsed", fix)
            if ver + (0,) * max(0, len(min_version) - len(ver)) < min_version: return Verdict("blocked", f"{cmd} {'.'.join(map(str, ver))} < {'.'.join(map(str, min_version))}", fix)
            return Verdict("done", f"{cmd} {'.'.join(map(str, ver)) if ver else 'present'}")
        except Exception as e: return Verdict("unknown", f"{cmd} present, version check failed: {e}")
    return Verdict("done", f"{cmd} at {path}")

def probe_env_file(path: Path, required: list[str], example: Path | None = None) -> Verdict:
    if not path.exists():
        return Verdict("todo", f"{path.name} absent" + (f" (example: {example.name})" if example and example.exists() else ""))
    vals = {}
    for ln in path.read_text().splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1); vals[k.strip()] = v.strip().strip('"').strip("'")
    missing = [k for k in required if not vals.get(k)]
    if missing: return Verdict("todo", f"{path.name}: missing {', '.join(missing)}", facts={"_env_missing": missing})
    return Verdict("done", f"{path.name} complete", facts={k: v for k, v in vals.items() if not any(t in k.lower() for t in ("pass", "secret", "key", "salt", "token", "cred"))})

def probe_port_free(port: int, what: str) -> Verdict:
    import socket
    with socket.socket() as s:
        s.settimeout(0.3)
        busy = s.connect_ex(("127.0.0.1", port)) == 0
    return Verdict("blocked", f"port {port} in use ({what})", f"stop the other service or set an override port") if busy else Verdict("done", f"port {port} free")
