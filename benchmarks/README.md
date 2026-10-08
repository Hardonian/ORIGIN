# Benchmarks

Small, **deterministic** fixtures suitable for CI, plus notes on where real
benchmarks live.

## In-repo fixtures

* `configs/smoke.json` — a tiny experiment that runs in seconds; executed by CI
  to prove the full pipeline (env → algorithms → store → export) works.
* Unit tests under `tests/` are the primary correctness benchmark.

## What is NOT in routine CI

Full scientific benchmarks (large budgets, many seeds, transfer adaptation) are
intentionally **excluded** from pull-request CI: they are expensive and non-
deterministic across machines. They are run manually and their artifacts are
committed to `research/reports/` (tables) — never fabricated.

## Running a benchmark locally

```bash
.venv/bin/origin-run --config configs/pilot.json --store runs --jobs "$(nproc)"
.venv/bin/python -c "from origin.visualization import generate_all; import sys; \
  print('\n'.join(generate_all('runs', sys.argv[1])))" <experiment_id>
```

## Performance notes

Measured on the reference workstation (Ryzen AI 9 HX370, WSL2, single process):
approximately **2.4 × 10⁴ environment interactions per second** for the 10×10
foraging task. GPU acceleration is not currently used.
