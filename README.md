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
