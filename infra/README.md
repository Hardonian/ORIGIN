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
distributed trivially. The node is reached over a **Tailscale tailnet**.

Observed tailnet members (`tailscale status`):

| Node | Address | Role |
|---|---|---|
| `epyc` | `100.127.74.34` (`epyc.taile5788a.ts.net`) | research compute (CPU/GPU) |
| `hx370-1` | `100.106.185.67` | this WSL workstation |
| `hx370` | `100.90.157.103` | Windows host |
| `poco-f7` | `100.110.204.34` | android |

**Current availability:** `epyc` reports `offline, last seen 4d ago`; SSH times
out. This is a power/network state, not a configuration gap — no action is needed
on the workstation side. Check with:

```bash
tailscale status | grep epyc
ssh -o BatchMode=yes -o ConnectTimeout=8 epyc true && echo reachable
```

### One-command distribution

```bash
scripts/origin_remote_worker.sh --check                    # reachability + hardware report
scripts/origin_remote_worker.sh --config configs/pilot.json --jobs 32
```

The script mirrors the repo (excluding `.venv`, `runs`, `node_modules`, `.next`),
creates a venv and installs on the remote, runs `pytest` then the experiment, and
rsyncs `runs/` back. **Trial ids are deterministic** (`sha256(experiment|algo|seed)`),
so merging remote results into the local store is idempotent and cannot duplicate
work — the same is true of any number of workers writing to a shared store, which
is protected by a `filelock`.

GPU nodes are used only if an algorithm is written to target CUDA (currently none
are). Do not assume V100/P40/RTX3060 share CUDA features.

## Safety

* Bind all services to loopback.
* Do not modify host GPU drivers, kernels or existing containers.
* Bound concurrency with `--jobs` on shared machines.
* Do not commit machine credentials or SSH keys; see `SECURITY.md`.
