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
| Organisms (morphology/controller/lineage) | `origin.organisms` | working |
| Evolution (fixed-objective GA, novelty search, MAP-Elites) | `origin.evolution` | working |
| Learning (REINFORCE policy-gradient RL baseline) | `origin.learning` | working |
| Evaluation (train/test isolation, morphology transfer) | `origin.evaluation` | working |
| Experiment runner + store (SQLite/Parquet/CSV) | `origin.experiments` | working |
| Telemetry | `origin.telemetry` | working |
| Visualization (plots) | `origin.visualization` | working |
| Research lab UI | `apps/lab` | see status ledger |

## Quickstart

```bash
uv venv --python 3.12 .venv
uv pip install -e ".[dev]" --python .venv/bin/python
.venv/bin/python -m pytest -q
```

Run a bounded experiment:

```bash
.venv/bin/origin-run --config configs/pilot.json --out runs
```

Inspect results / launch the read API:

```bash
.venv/bin/origin-api --store runs --host 127.0.0.1 --port 8788
```

Run the browser end-to-end tests (starts the API and the UI, then tears them down):

```bash
scripts/e2e_lab.sh
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
