#!/usr/bin/env python3
"""check_plugin.py — every validation gate for termcraft in one command (CI-grade). No dependencies beyond
Python 3.10+ and, for the official checks, the `claude` CLI on PATH.

    python3 scripts/check_plugin.py            # run all gates, print a table, exit 1 on any failure
    python3 scripts/check_plugin.py --json     # machine-readable report on stdout
    python3 scripts/check_plugin.py --skip official   # e.g. on a box without the claude CLI
    python3 scripts/check_plugin.py --only tests,previews

Gates (each is independent and reported separately):
  official   `claude plugin validate --strict` on plugin.json, marketplace.json, skills/, agents/
  manifest   name kebab-case, semver, description, agents/skills dirs exist, every skill has SKILL.md with frontmatter,
             every agent has frontmatter with name/description/model/color, entry skills reference agents that exist
  links      every `references/*.md`, `scripts/*.py`, `assets/*` path mentioned in a SKILL.md or agent exists;
             no leftover references to removed web-era files or the old plugin name in skills/agents/README
  compile    python -m compileall on every .py (3.10 syntax)
  tests      every scripts/test_*.py suite under skills/ passes (unittest)
  previews   preview_theme renders all themes dark/light/ascii at 80 cols; no line > 80 codepoints; ascii previews pure ASCII
  contrast   theme palettes meet ink ≥ 7:1, dim ≥ 3:1, accent ≥ 4.5:1 against black (dark) / white (light)
  evals      evals/*/prompt.md and graders/*.md parse: frontmatter present, grader types known, referenced paths exist
  package    scripts/package_plugin.py rebuilds the zip and its byte-verification passes; no __pycache__/.pyc/.venv in the tree
Read the table; a passing exit is necessary, not sufficient — live `claude plugin eval` and a real terminal still matter.
"""
from __future__ import annotations

import json, os, re, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT: list[dict] = []
JUNK_NAMES = ("__pycache__", ".venv", ".pytest_cache", ".DS_Store")
def find_junk(): return sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.name in JUNK_NAMES or p.suffix == ".pyc")
JUNK_AT_START = find_junk()

def gate(name):
    def deco(fn):
        def run():
            t0 = time.time(); notes: list[str] = []
            try: ok = fn(notes)
            except Exception as e: ok = False; notes.append(f"exception: {e.__class__.__name__}: {e}")
            REPORT.append({"gate": name, "ok": bool(ok), "seconds": round(time.time() - t0, 1), "notes": notes})
            return ok
        run.gate_name = name; return run
    return deco

def sh(cmd, cwd=ROOT, timeout=900):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)

def frontmatter(path: Path) -> dict | None:
    """Parse YAML frontmatter. Uses PyYAML when importable (strict: a YAML error → None); otherwise a small
    parser that understands `key: value` and `key: |` / `key: >` block scalars — enough for skills, agents,
    prompts and graders. `claude plugin validate` (2.1.x) does not inspect SKILL.md frontmatter at all, so this
    is the only place a malformed skill description is caught."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"): return None
    end = text.find("\n---", 3)
    if end < 0: return None
    raw = text[4:end]
    try:
        import yaml  # type: ignore
        try: d = yaml.safe_load(raw)
        except yaml.YAMLError: return None
        return d if isinstance(d, dict) else None
    except ImportError: pass
    fm: dict = {}; lines = raw.splitlines(); i = 0
    while i < len(lines):
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", lines[i])
        if not m: i += 1; continue
        key, val = m.group(1), m.group(2).strip()
        if val in ("|", ">", "|-", ">-", "|+", ">+"):
            block = []; i += 1
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()): block.append(lines[i]); i += 1
            ind = min((len(l) - len(l.lstrip()) for l in block if l.strip()), default=0)
            body = [l[ind:] for l in block]
            fm[key] = "\n".join(body).strip() if val[0] == "|" else " ".join(x.strip() for x in body).strip()
            continue
        fm[key] = val.strip("\"'"); i += 1
    return fm

# ---------------------------------------------------------------- gates
@gate("official")
def g_official(notes):
    if not shutil.which("claude"): notes.append("claude CLI not on PATH — skipped (use --skip official to silence)"); return False
    ok = True
    v = sh(["claude", "--version"]).stdout.strip()
    # plugin.json validation also walks agents/ and commands/; skills/ and agents/ are validated again as
    # component dirs. The CLI (2.1.x) lists only components it has findings for, and it does not parse SKILL.md
    # frontmatter or agent YAML strictly — the `manifest` gate does; this gate only proves the CLI raised nothing.
    for target in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json", "skills", "agents"):
        r = sh(["claude", "plugin", "validate", "--strict", "--json", target])
        try: d = json.loads(r.stdout)
        except json.JSONDecodeError: notes.append(f"{target}: non-JSON output (exit {r.returncode}): {r.stderr[:200]}"); ok = False; continue
        man = d.get("manifest") or {}; contents = d.get("contents") or []
        errs = list(man.get("errors", [])) + [e for c in contents for e in c.get("errors", [])]
        warns = list(man.get("warnings", [])) + [w for c in contents for w in c.get("warnings", [])]
        if not d.get("success") or errs or warns or r.returncode:
            ok = False; notes.append(f"{target}: success={d.get('success')} exit={r.returncode} errors={[e.get('message') for e in errs]} warnings={[w.get('message') for w in warns]}")
        else:
            notes.append(f"{target}: strict OK, no findings" + (f" ({man.get('type')} manifest)" if man else ""))
    notes.append(f"claude {v}"); return ok

@gate("manifest")
def g_manifest(notes):
    ok = True
    m = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", m.get("name", "")): ok = False; notes.append("name not kebab-case")
    if not re.fullmatch(r"\d+\.\d+\.\d+", m.get("version", "")): ok = False; notes.append("version not semver")
    if len(m.get("description", "")) < 40: ok = False; notes.append("description too short")
    mk = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    if not any(p.get("name") == m["name"] for p in mk.get("plugins", [])): ok = False; notes.append("marketplace does not list the plugin by name")
    skills = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())
    for s in skills:
        fm = frontmatter(s / "SKILL.md") if (s / "SKILL.md").exists() else None
        if not fm: ok = False; notes.append(f"skills/{s.name}: SKILL.md missing or no frontmatter"); continue
        if fm.get("name") != s.name: ok = False; notes.append(f"skills/{s.name}: frontmatter name '{fm.get('name')}' ≠ dir")
        if len(fm.get("description", "")) < 60: ok = False; notes.append(f"skills/{s.name}: description too short to trigger reliably")
    agents = sorted((ROOT / "agents").glob("*.md"))
    names = set()
    for a in agents:
        fm = frontmatter(a) or {}
        for k in ("name", "model", "color"):
            if k not in fm: ok = False; notes.append(f"agents/{a.name}: missing {k}")
        if fm.get("name") != a.stem: ok = False; notes.append(f"agents/{a.name}: name ≠ filename")
        names.add(fm.get("name"))
        if "<example>" not in a.read_text(): ok = False; notes.append(f"agents/{a.name}: no <example> blocks in description")
    for s in skills:  # entry skills must dispatch to agents that exist
        t = (s / "SKILL.md").read_text()
        for ref in re.findall(r"`([a-z-]+)` agent", t):
            if ref not in names: ok = False; notes.append(f"skills/{s.name}: references agent `{ref}` which does not exist")
    notes.append(f"{len(skills)} skills, {len(agents)} agents: {', '.join(sorted(names))}")
    return ok

@gate("links")
def g_links(notes):
    ok = True
    stale = re.compile(r"ascii-design|layout-designer|ascii-designer|html-mode|layout_audit|verify_page|build_page|template\.html|layout-tokens|components\.css|web-app-integration|Mode B")
    for md in list((ROOT / "skills").rglob("*.md")) + list((ROOT / "agents").glob("*.md")) + [ROOT / "README.md"]:
        text = md.read_text(encoding="utf-8")
        if md.name == "THIRD_PARTY_NOTICES.md": continue
        for m in stale.finditer(text):
            # the recipe format string legitimately says "ascii-design recipe line" nowhere else; flag everything
            ok = False; notes.append(f"{md.relative_to(ROOT)}: stale reference '{m.group(0)}'"); break
        base = md.parent if md.parent.name != "references" else md.parent.parent
        if md.name == "SKILL.md" or md.parent.name == "agents":
            for ref in set(re.findall(r"`((?:references|scripts|assets)/[\w./-]+)`", text)):
                if ref.endswith("...") or ref.endswith("/"): continue  # generic mentions like `references/...`
                cand = [base / ref, ROOT / "skills" / "tui-design" / ref, ROOT / "skills" / "cli-harness" / ref]
                if not any(c.exists() for c in cand): ok = False; notes.append(f"{md.relative_to(ROOT)}: `{ref}` does not exist")
    if ok: notes.append("all referenced paths exist; no web-era or old-name references")
    return ok

@gate("compile")
def g_compile(notes):
    r = sh([sys.executable, "-m", "compileall", "-q", "skills", "scripts"])
    if r.returncode: notes.append(r.stdout[-800:] + r.stderr[-800:]); return False
    # compileall leaves __pycache__ behind; remove so the package gate stays clean
    for d in ROOT.rglob("__pycache__"): shutil.rmtree(d, ignore_errors=True)
    notes.append(f"python {sys.version.split()[0]}: all sources compile"); return True

@gate("tests")
def g_tests(notes):
    ok = True; total = 0
    for t in sorted(ROOT.glob("skills/*/scripts/test_*.py")):
        r = sh([sys.executable, str(t)], timeout=1200)
        m = re.search(r"Ran (\d+) tests?", r.stderr); n = int(m.group(1)) if m else 0; total += n
        passed = r.returncode == 0 and "OK" in r.stderr
        ok &= passed
        notes.append(f"{t.relative_to(ROOT)}: {'OK' if passed else 'FAIL'} ({n} tests)" + ("" if passed else " — " + r.stderr[-600:]))
    notes.append(f"{total} tests total"); return ok

@gate("previews")
def g_previews(notes):
    import tempfile
    tool = ROOT / "skills/tui-design/scripts/preview_theme.py"; ok = True
    with tempfile.TemporaryDirectory() as d:
        for extra in ([], ["--bg", "light"], ["--ascii"]):
            r = sh([sys.executable, str(tool), "--name", "PB", "--cols", "80", "--out", d, *extra])
            if r.returncode: ok = False; notes.append(f"preview {extra}: exit {r.returncode}: {r.stderr[-300:]}")
        files = sorted(Path(d).glob("*.txt")); wide = []; nonascii = []
        for f in files:
            lines = f.read_text(encoding="utf-8").splitlines()
            if any(len(l) > 80 for l in lines): wide.append(f.name)
            if f.name.endswith("-ascii.txt") and any(ord(c) > 127 for l in lines for c in l): nonascii.append(f.name)
        if wide: ok = False; notes.append(f"lines > 80 codepoints: {wide}")
        if nonascii: ok = False; notes.append(f"non-ASCII in ascii previews: {nonascii}")
        notes.append(f"{len(files)} previews rendered")
    return ok

@gate("contrast")
def g_contrast(notes):
    sys.path.insert(0, str(ROOT / "skills/tui-design/scripts")); import themes
    def lum(h):
        r, g, b = (int(h.lstrip("#")[i:i+2], 16) / 255 for i in (0, 2, 4))
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
    def ratio(a, b): la, lb = lum(a), lum(b); return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)
    targets = {"ink": 7.0, "dim": 3.0, "accent": 4.5}; ok = True; n = 0
    for t in themes.THEMES.values():
        for bg_name, bg, pal in (("dark", "#000000", t.palette), ("light", "#ffffff", t.light)):
            for role, need in targets.items():
                n += 1; r = ratio(pal[role], bg)
                if r < need: ok = False; notes.append(f"{t.id}/{bg_name}/{role}: {r:.2f} < {need}")
    notes.append(f"{n} palette-role checks"); return ok

@gate("evals")
def g_evals(notes):
    ev = ROOT / "evals"
    if not ev.exists(): notes.append("no evals/ directory"); return False
    ok = True; known = {"regex", "tool_used", "tool_order", "file_exists", "llm", "baseline"}
    cases = [c for c in sorted(ev.iterdir()) if c.is_dir() and c.name not in ("results", "mocks", "evidence")]
    for c in cases:
        p = c / "prompt.md"
        if not p.exists(): ok = False; notes.append(f"{c.name}: prompt.md missing"); continue
        fm = frontmatter(p)
        if fm is None: ok = False; notes.append(f"{c.name}: prompt.md has no frontmatter")
        graders = sorted((c / "graders").glob("*.md")) if (c / "graders").exists() else []
        if not graders: ok = False; notes.append(f"{c.name}: no graders")
        for g in graders:
            gfm = frontmatter(g) or {}
            if gfm.get("type") not in known: ok = False; notes.append(f"{c.name}/{g.name}: unknown grader type {gfm.get('type')}")
        cy = c / "case.yaml"
        if cy.exists():
            for m in re.finditer(r"scaffold_script:\s*[\"']?([\w./-]+)", cy.read_text()):
                if not (c / m.group(1)).exists(): ok = False; notes.append(f"{c.name}: scaffold {m.group(1)} missing")
    notes.append(f"{len(cases)} case(s): {', '.join(c.name for c in cases)}"); return ok

@gate("package")
def g_package(notes):
    ok = True
    if JUNK_AT_START: ok = False; notes.append(f"junk in tree before the run: {JUNK_AT_START[:5]}")
    for d in ROOT.rglob("__pycache__"): shutil.rmtree(d, ignore_errors=True)  # anything the gates themselves left
    r = sh([sys.executable, "scripts/package_plugin.py"])
    if r.returncode: ok = False; notes.append(r.stderr[-400:])
    else: notes.append(r.stdout.strip())
    return ok

GATES = [g_official, g_manifest, g_links, g_compile, g_tests, g_previews, g_contrast, g_evals, g_package]

def main():
    a = sys.argv[1:]
    skip = set((a[a.index("--skip") + 1] if "--skip" in a else "").split(",")) - {""}
    only = set((a[a.index("--only") + 1] if "--only" in a else "").split(",")) - {""}
    ok_all = True
    for g in GATES:
        if g.gate_name in skip or (only and g.gate_name not in only): continue
        ok_all &= g()
    if "--json" in a:
        print(json.dumps({"ok": ok_all, "gates": REPORT, "root": str(ROOT)}, indent=2)); return 0 if ok_all else 1
    w = shutil.get_terminal_size((100, 24)).columns
    for r in REPORT:
        print(f"{'PASS' if r['ok'] else 'FAIL'} {r['gate']:<10} {r['seconds']:>6.1f}s")
        for n in r["notes"]: print("     " + n[: w - 6])
    print(f"\n{'all gates passed' if ok_all else 'FAILED — see notes'}: {sum(r['ok'] for r in REPORT)}/{len(REPORT)}")
    return 0 if ok_all else 1

if __name__ == "__main__": sys.exit(main())
