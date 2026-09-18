#!/usr/bin/env bash
# Builds the fixture project in the eval workspace (cwd): a small service with a hand-written install.sh.
set -euo pipefail
mkdir -p relay/scripts relay/config
cat > relay/README.md <<'MD'
# relay
Small event-relay service. Install with `./install.sh`, then `python3 -m relay serve`.
Requires Python ≥ 3.10, a RELAY_TOKEN, and a writable data dir (default ./data).
MD
cat > relay/requirements.txt <<'REQ'
requests>=2.31
REQ
cat > relay/config/relay.env.example <<'ENV'
RELAY_TOKEN=
RELAY_DATA_DIR=./data
RELAY_PORT=8080
ENV
cat > relay/install.sh <<'SH'
#!/usr/bin/env bash
# relay installer — run from the repo root
set -e
echo "== relay install =="
command -v python3 >/dev/null || { echo "python3 missing"; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' || { echo "need python >= 3.10"; exit 1; }
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
[ -f config/relay.env ] || cp config/relay.env.example config/relay.env
grep -q '^RELAY_TOKEN=.\+' config/relay.env || { echo "set RELAY_TOKEN in config/relay.env"; exit 2; }
mkdir -p "${RELAY_DATA_DIR:-./data}"
python3 scripts/migrate.py
echo "install complete — run: python3 -m relay serve"
SH
chmod +x relay/install.sh
mkdir -p relay/relay
cat > relay/relay/__init__.py <<'PY'
"""relay — tiny event-relay service (fixture)."""
__version__ = "0.1.0"
PY
cat > relay/relay/__main__.py <<'PY'
import os, sys
if len(sys.argv) > 1 and sys.argv[1] == "serve":
    print(f"relay serving on :{os.environ.get('RELAY_PORT', '8080')} (fixture: exits immediately)"); sys.exit(0)
print("usage: python3 -m relay serve"); sys.exit(2)
PY
cat > relay/scripts/migrate.py <<'PY'
import os, pathlib, sys
d = pathlib.Path(os.environ.get("RELAY_DATA_DIR", "./data")); d.mkdir(parents=True, exist_ok=True)
(d / "schema.version").write_text("3\n"); print("migrated to schema 3")
PY
