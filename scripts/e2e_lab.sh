#!/usr/bin/env bash
#
# ORIGIN lab E2E — start the API and the production UI, run a real headless
# browser test against them, then tear everything down. Always cleans up.
#
# Usage:  scripts/e2e_lab.sh
#
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY=".venv/bin/python"
API_PORT="${ORIGIN_API_PORT:-8788}"
UI_PORT="${ORIGIN_UI_PORT:-4317}"
API_PID=""
UI_PID=""

cleanup() {
  [[ -n "$API_PID" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "$UI_PID" ]] && kill "$UI_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT

wait_for() {  # url, label
  for _ in $(seq 1 60); do
    if curl -sf -o /dev/null --max-time 3 "$1"; then return 0; fi
    sleep 1
  done
  echo "ERROR: $2 did not become ready at $1" >&2
  return 1
}

echo "[e2e] starting ORIGIN API on ${API_PORT}"
"$PY" -m origin.experiments.api --store runs --host 127.0.0.1 --port "$API_PORT" >/tmp/origin_e2e_api.log 2>&1 &
API_PID=$!
wait_for "http://127.0.0.1:${API_PORT}/api/health" "API"

echo "[e2e] building + starting the lab UI on ${UI_PORT}"
(cd apps/lab && npm run build >/tmp/origin_e2e_build.log 2>&1)
(cd apps/lab && npm run start -- -p "$UI_PORT" >/tmp/origin_e2e_ui.log 2>&1) &
UI_PID=$!
wait_for "http://127.0.0.1:${UI_PORT}/" "UI"

echo "[e2e] running browser tests"
ORIGIN_E2E=1 \
ORIGIN_UI_URL="http://127.0.0.1:${UI_PORT}" \
ORIGIN_API_URL="http://127.0.0.1:${API_PORT}" \
  "$PY" -m pytest tests/e2e -q -p no:cacheprovider

echo "[e2e] OK"
