#!/usr/bin/env python3
"""digest.py — static digest of a source tree or shell script into a connection map (stdlib only).

    python digest.py <dir-or-script> [--out connection-map.json] [--mermaid map.mmd]

Extracts, without executing anything:
  entrypoints   pyproject [project.scripts], __main__.py, argparse/click/typer command names, shell scripts
  exec_chain    what each shell script hands off to: exec/source/./x.sh, python3 -m pkg, uv run …, docker compose
  env           every environment variable read (os.environ[...], .get, ${VAR}, $VAR, getenv) with the file that reads it,
                plus .env.example keys
  subprocesses  external commands invoked from Python (subprocess/os.system) and from shell
  writes        files/dirs the code writes (open(..,'w'), Path.write_text, mkdir, > redirects)
  imports       intra-repo import graph (package → package)
  ports         numeric ports mentioned near 'port'
  guards        early-exit conditions in shell (command -v, version checks, id -u) and Python (sys.exit on missing)
  tests         test files, markers, opt-in env vars
The output is the raw material for the process model (references/process-model.md). It is deliberately
over-inclusive; the agent prunes it while reading the actual code — the digest tells you WHERE to read.
"""
from __future__ import annotations

import hashlib
import os
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

SKIP = {".git", "node_modules", ".venv", "__pycache__", "dist", "build", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
PY_ENV = re.compile(r"""(?:os\.environ(?:\.get)?\s*[\[(]\s*|getenv\s*\(\s*)["']([A-Z][A-Z0-9_]+)["']""")
PY_ENV_PREFIX = re.compile(r"""f?["']([A-Z][A-Z0-9_]*_)\{?\w*\}?["']\s*\+?\s*(?:name|key|suffix)""")
SH_ENV = re.compile(r"\$\{?([A-Z][A-Z0-9_]{2,})\b")
SH_EXEC = re.compile(r"^\s*(?:exec\s+|source\s+|\.\s+)?((?:python3?|uv|docker|bash|sh|\./[\w./-]+|~[\w./-]+|[\w./-]+\.sh)\b[^\n#|&;]*)", re.M)
PY_SUB = re.compile(r"(?:subprocess\.(?:run|call|check_call|check_output|Popen)|os\.system)\s*\(\s*(\[[^\]]*\]|f?[\"'][^\"']*[\"'])", re.S)
PY_WRITE = re.compile(r"(?:open\([^)]*[\"'](?:w|a)[\"']|\.write_text\(|\.write_bytes\(|\.mkdir\(|shutil\.copy|os\.makedirs)")
SH_WRITE = re.compile(r"(?:>>?\s*([\w./~$-]+)|\bmkdir\b[^\n]*|\bcp\b[^\n]*|\btee\b\s+([\w./~$-]+))")
PORT = re.compile(r"port[^\n]{0,40}?\b(\d{4,5})\b", re.I)
SH_GUARD = re.compile(r"^(?:.*\b(command -v [\w-]+|id -u|version_info|--version|\[ .+? \] \|\| \{.*?\})).*$", re.M)
PY_EXIT = re.compile(r"(?:sys\.exit\(|raise SystemExit|raise \w*(?:Error|Exception)\()[^\n]{0,120}")
CLI_ARGPARSE = re.compile(r"add_parser\(\s*[\"']([\w-]+)[\"']|add_argument\(\s*[\"'](--[\w-]+)[\"']")
CLI_CLICK = re.compile(r"@(?:\w+\.)?(?:command|group)\(\s*(?:name\s*=\s*)?[\"']?([\w-]*)[\"']?")
TYPER = re.compile(r"@(\w+)\.command\(\s*(?:[\"']([\w-]+)[\"'])?")

def read(p: Path) -> str:
    try: return p.read_text(encoding="utf-8", errors="replace")
    except Exception: return ""

def digest(root: Path) -> dict:
    root = root.resolve()
    if not root.exists(): raise FileNotFoundError(root)
    files = [root] if root.is_file() else []
    if root.is_dir():
        for directory, dirs, names in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in SKIP)
            files.extend(Path(directory) / n for n in sorted(names) if not (Path(directory) / n).is_symlink())
    files.sort(key=lambda p: (p.name != "pyproject.toml", str(p)))
    local_modules = {p.stem for p in files if p.suffix == ".py"}
    local_modules.update(p.parent.name for p in files if p.name == "__init__.py")
    base = root if root.is_dir() else root.parent
    rel = lambda p: str(p.relative_to(base)) if p != root or root.is_dir() else p.name
    out = {"root": str(root), "entrypoints": [], "exec_chain": {}, "env": defaultdict(list), "env_examples": {}, "subprocesses": defaultdict(list),
           "writes": defaultdict(list), "imports": defaultdict(set), "ports": defaultdict(set), "guards": defaultdict(list), "tests": [], "docs": [], "packages": []}
    pkgs = {}
    for p in files:
        r = rel(p); name = p.name
        if p.suffix not in {".py", ".sh", ".toml", ".md", ".example", ""}: continue
        t = read(p)
        if name == "pyproject.toml":
            m = re.search(r"^name\s*=\s*[\"']([\w.-]+)[\"']", t, re.M); pkg = m.group(1) if m else r
            out["packages"].append({"name": pkg, "path": str(p.parent.relative_to(base)) if p.parent != base else "."})
            sections = re.findall(r"^\[project\.scripts\]\s*\n(.*?)(?=^\[|\Z)", t, re.M | re.S)
            for sm in re.finditer(r"^\s*([\w-]+)\s*=\s*[\"']([\w.]+):(\w+)[\"']", "\n".join(sections), re.M):
                out["entrypoints"].append({"kind": "console_script", "name": sm.group(1), "target": f"{sm.group(2)}:{sm.group(3)}", "file": r})
            pkgs[p.parent] = pkg
        if name in ("CLAUDE.md", "README.md", "AGENTS.md") or p.suffix == ".md": out["docs"].append(r)
        if name.endswith(".env.example") or name == ".env.example":
            out["env_examples"][r] = [ln.split("=", 1)[0].strip() for ln in t.splitlines() if ln.strip() and not ln.startswith("#") and "=" in ln]
        if p.suffix == ".sh" or t.startswith("#!") and "bash" in t[:40] or t.startswith("#!/bin/sh"):
            out["entrypoints"].append({"kind": "shell", "name": name, "file": r})
            chain = []
            for m in SH_EXEC.finditer(t):
                cmd = m.group(1).strip()
                if re.match(r"(python3?\s+-m|uv\s+run|exec\b|source\b|\./|~|docker\b|bash\b)", cmd) or cmd.endswith(".sh"): chain.append(cmd)
            out["exec_chain"][r] = sorted(set(chain))
            for m in SH_ENV.finditer(t):
                if m.group(1) not in ("BASH_SOURCE", "HOME", "PATH", "PWD"): out["env"][m.group(1)].append(r)
            for m in SH_GUARD.finditer(t): out["guards"][r].append(m.group(0).strip()[:160])
            for m in SH_WRITE.finditer(t):
                w = m.group(1) or m.group(2) or m.group(0).split()[0]
                if w and w not in ("/dev/null", "&2", "2"): out["writes"][r].append(w.strip()[:80])
            for m in PORT.finditer(t): out["ports"][m.group(1)].add(r)
        if p.suffix == ".py":
            if name == "__main__.py": out["entrypoints"].append({"kind": "python_module", "name": str(p.parent.relative_to(base)).replace("/", "."), "file": r})
            if "test" in p.parts or name.startswith("test_"):
                marks = sorted(set(re.findall(r"pytest\.mark\.(\w+)", t))); envs = sorted(set(PY_ENV.findall(t)))
                out["tests"].append({"file": r, "markers": marks, "env": envs}); continue
            for m in PY_ENV.finditer(t): out["env"][m.group(1)].append(r)
            for m in re.finditer(r"prefix\s*[+]\s*[\"'](\w+)[\"']|f[\"']\{prefix\}(\w+)[\"']", t):
                out["env"][f"<PREFIX>{m.group(1) or m.group(2)}"].append(r)
            for m in PY_SUB.finditer(t): out["subprocesses"][r].append(re.sub(r"\s+", " ", m.group(1))[:120])
            if PY_WRITE.search(t): out["writes"][r].append("(python file writes)")
            for m in PY_EXIT.finditer(t): out["guards"][r].append(m.group(0)[:140])
            for m in CLI_ARGPARSE.finditer(t):
                out["entrypoints"].append({"kind": "cli_command", "name": m.group(1) or m.group(2), "file": r})
            for m in CLI_CLICK.finditer(t): out["entrypoints"].append({"kind": "click", "name": m.group(1) or "(fn)", "file": r})
            for m in TYPER.finditer(t): out["entrypoints"].append({"kind": "typer", "name": m.group(2) or "(fn)", "file": r})
            for m in PORT.finditer(t): out["ports"][m.group(1)].add(r)
            src_pkg = next((pkgs[parent] for parent in p.parents if parent in pkgs), None)
            for m in re.finditer(r"^(?:from|import)\s+([\w.]+)", t, re.M):
                mod = m.group(1).split(".")[0]
                if mod in local_modules:
                    out["imports"][src_pkg or r].add(mod)
    out["env"] = {k: sorted(set(v)) for k, v in sorted(out["env"].items())}
    out["subprocesses"] = dict(out["subprocesses"]); out["writes"] = {k: sorted(set(v)) for k, v in out["writes"].items()}
    out["imports"] = {k: sorted(v) for k, v in out["imports"].items()}; out["ports"] = {k: sorted(v) for k, v in out["ports"].items()}
    out["guards"] = dict(out["guards"])
    seen = set(); out["entrypoints"] = [e for e in out["entrypoints"] if not (json.dumps(e, sort_keys=True) in seen or seen.add(json.dumps(e, sort_keys=True)))]
    return out

def mermaid(d: dict) -> str:
    lines = ["flowchart LR"]
    for f, chain in d["exec_chain"].items():
        for c in chain: lines.append(f'  {_id(f)}["{_label(f)}"] --> {_id(c)}["{_label(c[:40])}"]')
    for src, mods in d["imports"].items():
        for m in mods:
            if m != src: lines.append(f'  {_id(src)}["{_label(src)}"] -.-> {_id(m)}["{_label(m)}"]')
    for e in d["entrypoints"]:
        if e["kind"] in ("console_script", "python_module", "shell"): lines.append(f'  {_id(e["name"])}(("{_label(e["name"])}"))')
    return "\n".join(dict.fromkeys(lines))

def _id(s: str) -> str: return "n" + hashlib.sha256(s.encode()).hexdigest()[:20]

def _label(s: str) -> str:
    return "".join(ch if ch.isalnum() or ch in " ._/-" else f"#{ord(ch)};" for ch in s)

def main():
    if len(sys.argv) < 2: sys.exit(__doc__)
    root = Path(sys.argv[1]).resolve(); d = digest(root)
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else None
    mmd = Path(sys.argv[sys.argv.index("--mermaid") + 1]) if "--mermaid" in sys.argv else None
    text = json.dumps(d, indent=2, default=sorted)
    if out: out.write_text(text); print(f"wrote {out}")
    else: print(text)
    if mmd: mmd.write_text(mermaid(d)); print(f"wrote {mmd}")
    print(f"\n{len(d['entrypoints'])} entrypoints · {len(d['env'])} env vars · {len(d['exec_chain'])} shell chains · {len(d['tests'])} test files · packages: {[p['name'] for p in d['packages']]}", file=sys.stderr)

if __name__ == "__main__": main()
