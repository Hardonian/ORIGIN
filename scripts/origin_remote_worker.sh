#!/usr/bin/env bash
#
# ORIGIN remote worker — run a bounded experiment on the EPYC research node.
#
# ORIGIN is CPU-first: a trial is a pure function of (algorithm, seed, config),
# so work distributes trivially. This script checks reachability, mirrors the
# repo, runs the campaign remotely under a bounded job count, and pulls the
# results back into the local store.
#
# Usage:
#   scripts/origin_remote_worker.sh --check
#   scripts/origin_remote_worker.sh --config configs/pilot.json --jobs 32
#
# Env overrides:
#   ORIGIN_REMOTE_HOST   (default: epyc)      SSH host / tailscale name
#   ORIGIN_REMOTE_DIR    (default: ~/origin)  remote checkout directory
#   ORIGIN_STORE         (default: runs)      local store directory
#
set -Eeuo pipefail

REMOTE_HOST="${ORIGIN_REMOTE_HOST:-epyc}"
REMOTE_DIR="${ORIGIN_REMOTE_DIR:-~/origin}"
LOCAL_STORE="${ORIGIN_STORE:-runs}"
CONFIG="configs/pilot.json"
JOBS=32
CHECK_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check)  CHECK_ONLY=1; shift ;;
    --config) CONFIG="$2"; shift 2 ;;
    --jobs)   JOBS="$2"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

log() { printf '[origin-remote] %s\n' "$*"; }

# ---------------------------------------------------------------- reachability
log "checking tailnet status for '${REMOTE_HOST}'"
if command -v tailscale >/dev/null 2>&1; then
  tailscale status 2>/dev/null | grep -E "[[:space:]]${REMOTE_HOST}[[:space:]]" || true
fi

if ! ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=8 \
        "${REMOTE_HOST}" 'true' 2>/dev/null; then
  log "ERROR: ${REMOTE_HOST} is not reachable over SSH."
  log "Diagnose with:  tailscale status | grep ${REMOTE_HOST}"
  log "If it shows 'offline', the node is powered down or off the tailnet."
  exit 2
fi
log "reachable."

log "remote hardware:"
ssh -o BatchMode=yes "${REMOTE_HOST}" '
  echo "  host:    $(hostname)"
  echo "  kernel:  $(uname -r)"
  echo "  cpus:    $(nproc)"
  echo "  memory:  $(free -g | awk "/^Mem:/{print \$2\" GiB\"}")"
  echo "  git:     $(command -v git >/dev/null && git --version || echo none)"
  echo "  python:  $(command -v python3 >/dev/null && python3 --version || echo none)"
  echo "  uv:      $(command -v uv >/dev/null && uv --version || echo none)"
  if command -v nvidia-smi >/dev/null 2>&1; then
    echo "  gpus:"; nvidia-smi -L | sed "s/^/    /"
  else
    echo "  gpus:    none / no driver"
  fi
'

if [[ "${CHECK_ONLY}" -eq 1 ]]; then
  log "--check complete (no work executed)."
  exit 0
fi

# -------------------------------------------------------------------- mirror
log "syncing repo -> ${REMOTE_HOST}:${REMOTE_DIR}"
ssh -o BatchMode=yes "${REMOTE_HOST}" "mkdir -p ${REMOTE_DIR}"
rsync -az --delete \
  --exclude '.venv' --exclude 'runs' --exclude 'node_modules' \
  --exclude '.next' --exclude '.git' --exclude '__pycache__' \
  ./ "${REMOTE_HOST}:${REMOTE_DIR}/"

# --------------------------------------------------------------------- run
log "running ${CONFIG} on ${REMOTE_HOST} with --jobs ${JOBS}"
ssh -o BatchMode=yes "${REMOTE_HOST}" bash -lc "'
  set -euo pipefail
  cd ${REMOTE_DIR}
  command -v uv >/dev/null || { echo \"uv is required on the remote node\"; exit 3; }
  uv venv --python 3.12 --clear .venv >/dev/null
  uv pip install -e \".[dev]\" --python .venv/bin/python >/dev/null
  .venv/bin/python -m pytest tests -q
  .venv/bin/origin-run --config ${CONFIG} --store runs --jobs ${JOBS}
'"

# ------------------------------------------------------------------- retrieve
log "syncing results back -> ${LOCAL_STORE} (staged merge; local rows are never clobbered)"
STAGE="$(mktemp -d)"
trap 'rm -rf "${STAGE}"' EXIT
rsync -az "${REMOTE_HOST}:${REMOTE_DIR}/runs/" "${STAGE}/"
mkdir -p "${LOCAL_STORE}"
# Trial ids are deterministic (sha256 of experiment|algorithm|seed), so the
# merge is idempotent and cannot duplicate work. Local `done` rows are kept
# (keep-first); conflicts are reported instead of silently resolved.
.venv/bin/origin-merge-stores --from "${STAGE}" --into "${LOCAL_STORE}"

log "done. Inspect with:"
log "  .venv/bin/origin-worker --store ${LOCAL_STORE} --status"
log "  .venv/bin/python -c \"from origin.experiments.store import Store; s=Store('${LOCAL_STORE}'); [print(e['id'], e['name'], s.summary(e['id'])) for e in s.list_experiments()]\""
