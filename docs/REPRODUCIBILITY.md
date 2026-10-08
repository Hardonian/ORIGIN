# Reproducibility

ORIGIN is designed so that any published number can be regenerated from a
configuration file plus the environment manifest stored with the run.

## Determinism guarantees

| Layer | Mechanism |
|---|---|
| World generation | `GridWorld._make_rng(seed, part)` — SHA-256 derived per-part seeds |
| Episode dynamics | seeded `Generator`, serializable state (`get_state`/`set_state`) |
| Algorithms | single `np.random.default_rng(seed)` per trial |
| Metric aggregation | deterministic (mean/std, no sampling) |

Two runs with identical configuration and seed produce equivalent trajectories
within floating-point tolerance. Verified by
`tests/test_environment.py::test_seed_determinism_identical_trajectories` and
`::test_replay_consistency`.

## What is recorded per experiment

`runs/<experiment_id>/manifest.json` contains:

* the full experiment config (`configs/*.json`);
* environment manifest: Python version, platform, CPU count, package versions,
  git SHA, branch, dirty flag, timestamp.

Per trial (`runs/<experiment_id>/<trial_id>.jsonl` + SQLite row):

* algorithm + version, seed, interaction count, budget;
* full hyperparameters (via `metrics_json.algorithm_extra` and the config);
* training history (down-sampled), descriptors;
* held-out test metrics;
* transfer report (zero-shot and adapted per variant);
* the winning organism's genome (`<trial_id>.organism.json`).

## Reproduce a run

```bash
# exact re-run of a config (resumes; use --no-resume to force)
.venv/bin/origin-run --config configs/pilot.json --store runs --jobs 6 --no-resume
```

Because the experiment id is a hash of the config, the same config always lands
in the same directory. If code has changed, the recorded `git_sha`/`git_dirty`
in `manifest.json` tells you the run is not bit-identical to a clean checkout.

## Train / test isolation

* `train_seeds` and `test_seeds` are disjoint; the runner **refuses** to run
  with an overlap (raises on seed leakage). See
  `tests/test_experiments.py::test_validate_config_rejects_seed_leakage`.
* Held-out seeds are never used for tuning.
* Morphology / perturbation variants are only used for *evaluation* after
  training, never in the training loop (except the explicit adaptation phase).

## Dependency reproducibility

`uv` with a pinned Python (3.12) and a lockfile. `pyproject.toml` declares the
supported versions; CI installs from it, so CI is the reference environment.

## Known limits

* Absolute bit-for-bit equality across BLAS builds is not guaranteed; numerical
  tolerances are documented in tests.
* The PILOT campaign uses modest budgets; results are marked preliminary where
  the sample size does not support inference (see the research report).
