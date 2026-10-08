#!/usr/bin/env bash
# ORIGIN cleanup: removes generated run data and caches. DRY-RUN by default.
set -Eeuo pipefail

STORE="${ORIGIN_STORE:-runs}"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

targets=("$STORE" .pytest_cache .ruff_cache .mypy_cache)
echo "ORIGIN cleanup (apply=$APPLY)"
for t in "${targets[@]}"; do
  if [[ -e "$t" ]]; then
    echo "  would remove: $t ($(du -sh "$t" 2>/dev/null | cut -f1))"
    if [[ $APPLY -eq 1 ]]; then
      rm -rf "$t" && echo "    removed"
    fi
  fi
done
[[ $APPLY -eq 0 ]] && echo "dry-run only; re-run with --apply to delete."
