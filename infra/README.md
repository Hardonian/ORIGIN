# Infrastructure

ORIGIN is designed to run on a single machine by default and scale to a small
local cluster without cloud dependencies. This directory documents the intended
deployment topology; it contains no host-specific secrets.

## Roles

| Machine | Role | Notes |
|---|---|---|
| Workstation (Ryzen AI 9 HX370, WSL2 Ubuntu) | development, lab UI, experiment scheduling, analysis | loopback services only |
| Research compute (AMD EPYC 7452, V100/P40/RTX 3060) | parallel CPU simulation, population evaluation, bounded GPU workloads | **optional**, see below |

The platform is **CPU-first**. GPU acceleration is a possible future
optimisation, not a requirement. ORIGIN never assumes a GPU is present.

## Workstation quickstart

```bash
uv venv --python 3.12 .venv
uv pip install -e ".[dev]" --python .venv/bin/python
.venv/bin/origin-run --config configs/pilot.json --store runs --jobs 6
.venv/bin/origin-api  --store runs --host 127.0.0.1 --port 8788
```

## Compute worker (optional)

Because a trial is a pure function of `(algorithm, seed, config)`, work can be
distributed trivially:

* **Same-account SSH, shared filesystem**: run `origin-run` with a larger
  `--jobs` on the compute host, pointing `--store` at a shared directory. The
  store uses `filelock`, so concurrent writers are safe.
* **No shared filesystem**: copy the config, run the same `origin-run` with the
  same `--config` and `--store` on the worker, then copy `runs/` back. Trial ids
  are deterministic, so results merge without duplication.

GPU nodes are used only if a future algorithm is written to target CUDA
(currently none are). Do not assume V100/P40/RTX3060 share CUDA features.

## Safety

* Bind all services to loopback.
* Do not modify host GPU drivers, kernels or existing containers.
* Bound concurrency with `--jobs` on shared machines.
* Do not commit machine credentials or SSH keys; see `SECURITY.md`.
