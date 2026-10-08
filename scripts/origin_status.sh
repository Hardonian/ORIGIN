#!/usr/bin/env bash
# ORIGIN status: non-destructive health report for the local platform.
set -Eeuo pipefail

ROOT="${1:-.}"
STORE="${ORIGIN_STORE:-runs}"
PY="${ORIGIN_PY:-.venv/bin/python}"

echo "=== ORIGIN status ==="
echo "root:  $(cd "$ROOT" && pwd)"
echo "store: $STORE"
echo

echo "--- python / package ---"
if [[ -x "$PY" ]]; then
  "$PY" -c "import origin, sys; print('origin', origin.__version__, '| python', sys.version.split()[0])"
else
  echo "WARNING: $PY not found (create the venv: uv venv --python 3.12 .venv)"
fi
echo

echo "--- git ---"
git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || true
git -C "$ROOT" log -1 --pretty='%h %s' 2>/dev/null || true
git -C "$ROOT" status --porcelain 2>/dev/null | head -20 || true
echo

echo "--- experiment store ---"
if [[ -f "$STORE/origin.db" ]]; then
  "$PY" - <<'PY'
from origin.experiments.store import Store
import os
store = Store(os.environ.get("ORIGIN_STORE", "runs"))
for e in store.list_experiments():
    print(f"  {e['id']}  {e['name']:<24} {e['status']:<10} {store.summary(e['id'])}")
PY
else
  echo "  no store at $STORE (run an experiment first)"
fi
echo

echo "--- disk ---"
du -sh "$STORE" 2>/dev/null || true
echo "done."
