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
| Articulated-body physics (**PyBullet**) | `origin.environments.embodied` | calibrated yaw-joint crawler; fail-closed probe required before embodied campaigns |
| Organisms (morphology/controller/lineage) | `origin.organisms` | working |
| Evolution (fixed-objective GA, novelty search, MAP-Elites) | `origin.evolution` | working |
| Learning (REINFORCE + PPO RL baselines) | `origin.learning` | implementations working; PPO v1 is exploratory pending its corrected v2 study |
| Evaluation (train/test isolation, morphology transfer) | `origin.evaluation` | working |
| Embodied evaluation + transfer | `origin.evaluation.embodied` | calibrated v3 campaign complete; historical v2 results remain retracted |
| Experiment runner + store (SQLite/Parquet/CSV) | `origin.experiments` | working |
| Telemetry | `origin.telemetry` | working |
| Visualization (plots) | `origin.visualization` | working |
| Research lab UI | `apps/lab` | see status ledger |

The same optimizers drive both simulators; `env_kind` selects `gridworld` or
`embodied`. See `docs/ARCHITECTURE.md`. The historical v2 embodied report is
retracted in `research/reports/ORIGIN_M4_Embodied_Transfer_Report.md`; its
calibrated v3 replacement is
`research/reports/ORIGIN_M4_Embodied_Transfer_Report_v3.md`.

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

On Windows, PyBullet currently builds from source. Install the Microsoft C++
Build Tools once, then run the install from its x64 developer environment:

```powershell
winget install --id Microsoft.VisualStudio.2022.BuildTools --exact --silent --accept-package-agreements --accept-source-agreements --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
uv venv --python 3.12 .venv
cmd /d /s /c 'call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" && uv pip install -e ".[dev,embodied]" --python .venv\Scripts\python.exe'
.venv\Scripts\python.exe -m pytest tests/test_embodied.py tests/test_embodied_eval.py tests/test_runner_embodied.py tests/test_embodied_probe.py -q
.venv\Scripts\python.exe scripts\probe_embodied_morphology.py --json-out runs\embodied-calibration-local.json
```

The probe is an acceptance gate, not a success command: it exits nonzero and
writes the evidence when no production gait can move forward at least 5 cm in
3 seconds while upright.

The probe is fail-closed and can also write durable evidence for a campaign
review. On a Docker-capable Linux host, the repository's pinned container path
runs the same command without requiring a local compiler:

```bash
docker compose -f infra/docker-compose.yml --profile calibration run --rm calibration
# evidence is persisted in the named origin-data volume at
# /origin/runs/embodied-calibration.json
```

GitHub Actions runs guard, Python, security, frontend, and browser checks on
GitHub-hosted Linux. The PyBullet regression suite and calibration gate run on
the dedicated Linux physics runner for every pull request; a failed or
unavailable probe cannot be mistaken for a successful embodied result.

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

The current confirmatory grid result is the strict-cap multi-niche H1.MN
replication. Run it, then generate its descriptive report and registered
paired transfer analysis (both from stored artifacts, with no hand-entered
numbers):

```bash
.venv/bin/origin-run --config configs/multi_niche_transfer_replication_v3.json --store runs --jobs 8
.venv/bin/python scripts/make_report.py --store runs --experiment <id> --out research/reports/ORIGIN_Multi_Niche_v3_Research_Report.md
.venv/bin/python scripts/analyze_multi_niche.py --store runs --experiment <id> \
  --bootstrap-seed 20261015 --protocol-doc research/protocols/multi_niche_replication_v3.md \
  --out research/reports/H1_multi_niche_v3_analysis.md
```

Older single-niche and multi-niche stores are retained for audit, not as current
strict-cap evidence. `scripts/make_report.py` requires an explicit
`--allow-legacy` override for an archival report; see
`research/reports/RESULT_PROVENANCE.md` before citing them.

Distribute a campaign to the compute node when it is online:

```bash
scripts/origin_remote_worker.sh --check
scripts/origin_remote_worker.sh --config configs/multi_niche_transfer_replication_v3.json --jobs 32
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
