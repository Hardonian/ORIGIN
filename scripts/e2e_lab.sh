#!/usr/bin/env bash
#
# ORIGIN lab E2E — start the API and the production UI, run a real headless
# browser test against them, then tear everything down. Always cleans up.
#
# Port hygiene: if a requested port is already in use (a stale run, or a second
# concurrent run), pick a free port instead of silently borrowing the other
# process's server. Borrowing previously let a killed-backend collision masquerade
# as a test failure, so a busy port may never produce a result from this script.
#
# Usage:  scripts/e2e_lab.sh
#
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY=".venv/bin/python"
API_PORT_WANT="${ORIGIN_API_PORT:-8788}"
UI_PORT_WANT="${ORIGIN_UI_PORT:-4317}"
API_PID=""
UI_PID=""

# free_port <preferred>: prints <preferred> if bindable, else a free ephemeral port.
free_port() {
  "$PY" - "$1" <<'PYEOF'
import socket
import sys

preferred = int(sys.argv[1])


def is_free(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def ephemeral() -> int:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = int(probe.getsockname()[1])
    probe.close()
    return port


print(preferred if is_free(preferred) else ephemeral())
PYEOF
}

API_PORT="$(free_port "$API_PORT_WANT")"
UI_PORT="$(free_port "$UI_PORT_WANT")"
[[ "$API_PORT" != "$API_PORT_WANT" ]] && echo "[e2e] port ${API_PORT_WANT} busy -> API on ${API_PORT}"
[[ "$UI_PORT" != "$UI_PORT_WANT" ]] && echo "[e2e] port ${UI_PORT_WANT} busy -> UI on ${UI_PORT}"

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

echo "[e2e] route preflight (server-side, independent of the browser)"
for r in / /world /evolution /designer /benchmark /workers /artifacts /failures; do
  printf '  %-12s HTTP %s\n' "$r" "$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "http://127.0.0.1:${UI_PORT}${r}")"
done

echo "[e2e] running browser tests"
ORIGIN_E2E=1 \
ORIGIN_UI_URL="http://127.0.0.1:${UI_PORT}" \
ORIGIN_API_URL="http://127.0.0.1:${API_PORT}" \
  "$PY" -m pytest tests/e2e -q -p no:cacheprovider

echo "[e2e] OK"
