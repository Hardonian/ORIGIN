# ORIGIN

**Open Research Into General Intelligence** — an open, reproducible research platform for
investigating whether *generalizable* intelligent behaviour can emerge through evolution,
learning, environmental adaptation and morphological diversity.

ORIGIN is a research instrument, not a demo. It implements falsifiable hypotheses,
controlled interventions, reproducible trials, meaningful baselines and quantitative
evaluation, and it refuses to report any metric that is not traceable to a real
experiment artifact.

> Status: **alpha**. See `IMPLEMENTATION_STATUS.md` for exactly what is verified,
> what is incomplete, and why.

## Research question

> Can evolutionary diversity and open-ended learning produce capabilities that transfer
> more effectively to unfamiliar environments and physical morphologies than conventional
> fixed-objective training?

Initial hypothesis (to be *tested*, not assumed):

> Under equivalent computational and environment-interaction budgets, maintaining
> behaviourally diverse agent populations improves adaptation to unseen tasks or changes
> in morphology.

## What is implemented

| Subsystem | Package | State |
|---|---|---|
| Deterministic 2D environment | `origin.environments` | working |
| Articulated-body physics (**PyBullet**) | `origin.environments.embodied` | engine working; crawler redesign awaiting physics calibration — see status ledger |
| Organisms (morphology/controller/lineage) | `origin.organisms` | working |
| Evolution (fixed-objective GA, novelty search, MAP-Elites) | `origin.evolution` | working |
| Learning (REINFORCE policy-gradient RL baseline) | `origin.learning` | working |
| Evaluation (train/test isolation, morphology transfer) | `origin.evaluation` | working |
| Embodied evaluation + transfer | `origin.evaluation.embodied` | instrumentation verified; **M4 results retracted** (2026-10-08) |
| Experiment runner + store (SQLite/Parquet/CSV) | `origin.experiments` | working |
| Telemetry | `origin.telemetry` | working |
| Visualization (plots) | `origin.visualization` | working |
| Research lab UI | `apps/lab` | see status ledger |

The same optimizers drive both simulators; `env_kind` selects `gridworld` or
`embodied`. See `docs/ARCHITECTURE.md`. For the embodied results and their
retraction (2026-10-08), see
`research/reports/ORIGIN_M4_Embodied_Transfer_Report.md` and
`IMPLEMENTATION_STATUS.md`.

## Quickstart

```bash
uv venv --python 3.12 .venv
uv pip install -e ".[dev]" --python .venv/bin/python
.venv/bin/python -m pytest -q
```

The articulated-body simulator is optional so core development works where
PyBullet is unavailable. Install its extra before running the embodied suite or
calibration probe:

```bash
uv pip install -e ".[dev,embodied]" --python .venv/bin/python
```

The probe is fail-closed and can also write durable evidence for a campaign
review. On a Docker-capable Linux host, the repository's pinned container path
runs the same command without requiring a local compiler:

```bash
docker compose -f infra/docker-compose.yml --profile calibration run --rm calibration
# evidence is persisted in the named origin-data volume at
# /origin/runs/embodied-calibration.json
```

GitHub Actions is configured to run this PyBullet regression suite and
calibration gate on Linux for every pull request; a failed or unavailable probe
cannot be mistaken for a successful embodied result.

Run system diagnostics:

```bash
origin-doctor
```

Run a bounded experiment or local worker cluster:

```bash
# Single-runner mode
origin-run --config configs/pilot.json --store runs --jobs 4

# Distributed worker model (atomic claims, heartbeats, automatic stale recovery)
origin-worker --config configs/pilot.json --store runs --stale-after 120

# Or manage a cluster of concurrent worker processes:
python scripts/cluster_manager.py --config configs/pilot.json --workers 4
```

Launch the API server and Research Lab UI:

```bash
# API server (loopback default, token authenticated on external interfaces)
origin-api --store runs --host 127.0.0.1 --port 8788

# Research Lab UI (Next.js 16 with 3D creature simulator & cluster dashboard)
cd apps/lab && npm run start   # runs on http://127.0.0.1:4317
```

Containerized deployment (Docker Compose):

```bash
docker compose -f infra/docker-compose.yml up --build
```

Run the UI↔API contract smoke tests:

```bash
node apps/lab/scripts/smoke-api.mjs
```

Run the pre-registered powered replication of H1, then generate its report and the
registered statistical analysis (both generated from the store, no hand-entered numbers):

```bash
.venv/bin/origin-run --config configs/pilot_powered.json --store runs --jobs 8
.venv/bin/python scripts/make_report.py --store runs --experiment <id> --out research/reports/ORIGIN_Initial_Research_Report.md
.venv/bin/python scripts/analyze.py      --store runs --experiment <id> --out research/reports/H1_powered_analysis.md
```

Study v2 repeats this with a **paired** primary design and fresh seeds
(`configs/pilot_paired_v2.json`, `research/protocols/paired_v2.md`):

```bash
.venv/bin/origin-run --config configs/pilot_paired_v2.json --store runs --jobs 8
.venv/bin/python scripts/analyze.py --store runs --experiment <id> --design paired --out research/reports/H1_paired_v2_analysis.md
```

Study v3 (`configs/pilot_paired_v3.json`, `research/protocols/paired_v3_power.md`) is
power-sized from a prior power analysis and scoped to the resolvable comparison:

```bash
.venv/bin/origin-run --config configs/pilot_paired_v3.json --store runs --jobs 8
.venv/bin/python scripts/analyze.py --store runs --experiment <id> --design paired \
  --bootstrap-seed 20261010 --protocol-doc research/protocols/paired_v3_power.md \
  --out research/reports/H1_v3_decisive_analysis.md
```

Every study uses a **distinct** bootstrap seed and its analysis is fixed before the
run; no study is re-analysed and the conclusion is never switched to a more
favourable statistic.

Distribute a campaign to the compute node when it is online:

```bash
scripts/origin_remote_worker.sh --check
scripts/origin_remote_worker.sh --config configs/pilot.json --jobs 32
```

## Repository layout

```text
apps/lab/            Next.js research-lab interface
packages/origin/     Python research platform
  environments/      deterministic 2D world
  organisms/         morphology, genome, lineage, policies
  evolution/         GA, novelty search, MAP-Elites QD
  learning/          RL baselines (REINFORCE)
  evaluation/        evaluation + transfer harnesses
  experiments/       runner, store, API
  telemetry/         metrics logging
  visualization/     plotting
research/            hypotheses, protocols, baselines, reports
configs/             versioned experiment configs
tests/               pytest suite
benchmarks/          deterministic fixtures + perf smoke
docs/                architecture, reproducibility, protocol, verification
infra/               server + worker notes
.github/workflows/   CI
```

## Science, honesty and reproducibility

* Two runs with identical configuration and seed produce equivalent trajectories within
  documented tolerance (`tests/test_environment.py`).
* Train and held-out evaluation environments are separated by seed and by generation
  parameters; held-out benchmarks are never used for tuning.
* Every algorithm records algorithm name/version, hyperparameters, seed, environment
  config, interaction budget, compute cost, evaluation protocol and checkpoints.
* Failed trials are recorded and reported, never silently dropped.

## License

MIT. See `LICENSE`.
