#!/usr/bin/env bash
# An existing "wizard" with planted defects: secret echoed, no --dry-run/--check, no journal/resume,
# exit 0 after a failed step, colour-only status, no non-TTY handling.
set -euo pipefail
mkdir -p relay/tools
cat > relay/tools/setup_wizard.py <<'PY'
#!/usr/bin/env python3
"""relay setup wizard (legacy)."""
import os, subprocess, sys, pathlib

def step(name, fn):
    print(f"\033[36m{name}\033[0m")
    try:
        fn()
        print("\033[32mok\033[0m")
    except Exception as e:
        print(f"\033[31m{e}\033[0m")

def venv():
    if not pathlib.Path(".venv").exists():
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)

def token():
    t = input("RELAY_TOKEN: ")
    print(f"using token {t}")
    pathlib.Path("config").mkdir(exist_ok=True)
    pathlib.Path("config/relay.env").write_text(f"RELAY_TOKEN={t}\nRELAY_DATA_DIR=./data\n")

def migrate():
    subprocess.run([sys.executable, "-c", "import pathlib; pathlib.Path('data').mkdir(exist_ok=True); pathlib.Path('data/schema.version').write_text('3')"])

step("virtualenv", venv)
step("token", token)
step("migrate", migrate)
print("done")
PY
chmod +x relay/tools/setup_wizard.py
cat > relay/README.md <<'MD'
# relay
Run `python3 tools/setup_wizard.py` from the repo root to set up.
MD
