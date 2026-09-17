#!/usr/bin/env python3
"""drive_harness.py — drive an interactive CLI in a real pty with scripted answers; capture a transcript;
assert on it. Used to VERIFY a generated harness and to EXPLORE an existing one. Stdlib only (Linux/macOS).

    python drive_harness.py scenario.json [--out transcripts/]

scenario.json:
{
  "name": "happy-path",
  "cmd": ["python3", "harness.py"],           "cwd": ".",   "env": {"NO_COLOR": "1"},
  "cols": 100, "rows": 40, "timeout": 60,
  "script": [                                   # in order; each waits for `expect` (regex) then sends `send`
    {"expect": "proceed\\?", "send": "y\\n"},
    {"expect": "Postgres password", "send": "s3cret\\n", "secret": "s3cret"}
  ],
  "assert": {
    "exit_code": 0,
    "stdout_matches": ["all stages done"],
    "stdout_not_matches": ["Traceback", "s3cret"],       # secrets must never echo
    "files_exist": [".harness/pb.jsonl"]
  }
}
Multiple scenarios: pass a directory; every *.json in it runs; summary table + exit 1 if any fails.
Assertions inspect the original capture; saved transcripts and diagnostics redact declared step secrets.
Commands are argv lists, not shell pipelines. To test pipes, explicitly use ["bash", "-o", "pipefail", "-c", "..."] after reading the command for safety.
Also useful raw: --explore "<cmd>" prints the transcript of running the command with no input (help/--check/--dry-run)
so an existing harness can be mapped before scripting it.
"""
from __future__ import annotations

import json
import os
import pty
import re
import select
import signal
import shlex
import errno
import sys
import time
from pathlib import Path


def _unescape(text: str) -> str:
    """Interpret \\n, \\t, \\x1b… escapes in a scenario's `send` while leaving non-Latin-1 text (Hebrew, CJK, emoji) intact."""
    return text.encode("latin-1", "backslashreplace").decode("unicode_escape")


def run_scenario(sc: dict, out_dir: Path) -> dict:
    name = sc["name"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
        raise ValueError("scenario name must be a simple filename")
    steps = list(sc.get("script", []))
    patterns = [re.compile(st["expect"].encode(), re.S) for st in steps]
    sends = [_unescape(st["send"]).encode("utf-8") for st in steps]
    env = {**os.environ, "TERM": "xterm-256color", **sc.get("env", {}),
           "COLUMNS": str(sc.get("cols", 100)), "LINES": str(sc.get("rows", 40))}
    pid, fd = pty.fork()
    if pid == 0:
        try:
            os.chdir(sc.get("cwd", "."))
            os.execvpe(sc["cmd"][0], sc["cmd"], env)
        except BaseException:
            os.write(2, b"driver: unable to start command\n")
            os._exit(127)
    transcript = bytearray(); cursor = 0; step_log = []; status = None
    deadline = time.monotonic() + sc.get("timeout", 60); timed_out = False; eof = False; overflow = False
    def kill_group():
        try: os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            try: os.kill(pid, signal.SIGKILL)
            except ProcessLookupError: pass
    try:
        import fcntl, struct, termios
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", sc.get("rows", 40), sc.get("cols", 100), 0, 0))
        while True:
            if status is None:
                ended, value = os.waitpid(pid, os.WNOHANG)
                if ended: status = value
            if eof and status is not None: break
            if time.monotonic() >= deadline:
                timed_out = True
                step_log.append(("timeout", steps[0]["expect"] if steps else None))
                break
            if steps and not eof:
                match = patterns[0].search(transcript, cursor)
                if match:
                    # Consume all output already seen; a later step needs fresh output.
                    cursor = len(transcript)
                    st = steps.pop(0); patterns.pop(0)
                    os.write(fd, sends.pop(0)); step_log.append(("sent", st["expect"]))
            if eof:
                time.sleep(0.02)
                continue
            ready, _, _ = select.select([fd], [], [], min(0.05, max(0, deadline - time.monotonic())))
            if ready:
                try: chunk = os.read(fd, 65536)
                except OSError as exc:
                    if exc.errno != errno.EIO: raise
                    chunk = b""
                if not chunk: eof = True
                else:
                    limit = sc.get("max_output_bytes", 8 * 1024 * 1024)
                    transcript.extend(chunk[:max(0, limit - len(transcript))])
                    if len(transcript) >= limit:
                        overflow = True
                        break
    finally:
        # Includes descendants that inherited the PTY, also on exceptions/interrupts.
        kill_group()
        os.close(fd)
        if status is None: _, status = os.waitpid(pid, 0)
    code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -os.WTERMSIG(status)
    text = re.sub(rb"\x1b\[[0-9;?]*[a-zA-Z]", b"", transcript).decode("utf-8", "replace")
    a = sc.get("assert", {}); fails = []
    expected_code = a.get("exit_code", 0)
    if code != expected_code: fails.append(f"exit {code} != {expected_code}")
    for pat in a.get("stdout_matches", []):
        if not re.search(pat, text, re.S): fails.append(f"missing /{pat}/")
    for pat in a.get("stdout_not_matches", []):
        if re.search(pat, text, re.S): fails.append(f"present /{pat}/")
    for st in sc.get("script", []):
        if st.get("secret") and st["secret"] in text: fails.append("declared secret echoed")
    for f in a.get("files_exist", []):
        if not (Path(sc.get("cwd", ".")) / f).exists(): fails.append(f"file missing {f}")
    if steps: fails.append(f"unmet expect: {steps[0]['expect']}")
    if overflow: fails.append("output limit exceeded (process group killed)")
    if timed_out: fails.append(f"timeout after {sc.get('timeout', 60)}s (process killed)")
    secrets = sorted({st["secret"] for st in sc.get("script", []) if st.get("secret")}, key=len, reverse=True)
    def redact(value):
        return re.sub("|".join(re.escape(v) for v in secrets), lambda _: "[redacted]", value) if secrets else value
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{name}.txt").write_text(redact(text), encoding="utf-8")
    fails = [redact(f) for f in fails]
    step_log = [(kind, redact(prompt) if prompt else prompt) for kind, prompt in step_log]
    return {"name": sc["name"], "exit": code, "fails": fails, "transcript": str(out_dir / f"{sc['name']}.txt"), "steps": step_log}


def main():
    args = sys.argv[1:]
    if not args: sys.exit(__doc__)
    out = Path(args[args.index("--out") + 1]) if "--out" in args else Path("transcripts")
    if args[0] == "--explore":
        sc = {"name": "explore", "cmd": shlex.split(args[1]), "timeout": 20, "env": {"NO_COLOR": "1"}}
        r = run_scenario(sc, out); print(Path(r["transcript"]).read_text()); print(f"\n[exit {r['exit']}]"); sys.exit(1 if r["fails"] or r["exit"] else 0)
    target = Path(args[0]); scenarios = sorted(target.glob("*.json")) if target.is_dir() else [target]
    if not scenarios: sys.exit("no scenario JSON files found")
    results = [run_scenario(json.loads(p.read_text()), out) for p in scenarios]
    bad = 0
    for r in results:
        ok = not r["fails"]; bad += not ok
        print(f"{'PASS' if ok else 'FAIL'} {r['name']:<28} exit={r['exit']:<3} {'; '.join(r['fails'])}")
    print(f"\n{len(results) - bad}/{len(results)} scenarios passed; transcripts in {out}/")
    sys.exit(1 if bad else 0)


if __name__ == "__main__": main()
