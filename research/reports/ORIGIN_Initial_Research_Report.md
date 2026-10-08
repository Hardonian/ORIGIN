# Open-Ended Evolution and Cross-Morphology Generalization: A Reproducible Experimental Framework

**Author:** Scott Hardie (Hardonian) · **Status:** 10 seeds; interval-based registered
analysis in `research/reports/H1_powered_analysis.md`. Not peer reviewed.

> This report was generated automatically from the stored experiment artifacts by
> `scripts/make_report.py`. Every figure below is read from the experiment store; no
> number is hand-entered. Experiment id: `d0ef7208a010`.

---

## 1. Research question and hypothesis

Pre-registered replication of H1 (research/protocols/powered_replication.md). Identical task and budget to the pilot; 10 independent seeds instead of 5 for a lower-variance estimate and an interval-based analysis. No tuning against held-out seeds.

**H1.** Under an equivalent environment-interaction budget, maintaining behaviourally
diverse populations (novelty search, quality-diversity) improves adaptation to unseen
evaluation environments and to changed morphology relative to fixed-objective evolution.

## 2. Method

Deterministic 10×10 egocentric foraging world; observation is 7-D (energy + resource/hazard bearings), absolute position excluded so policies cannot memorise a layout. Budget: **500,000 environment interactions per method per seed**. Training seeds [11, 22, 33, 44]; held-out test seeds [101, 202, 303, 404] (disjoint). 10 independent RNG seeds.

## 3. Held-out performance (train/test isolated)

| method | n seeds | held-out reward (mean) | standard error | train fitness | mean interactions |
|---|---|---|---|---|---|
| `random` | 10 | 2.085 | ±0.102 | 1.710 | 560 |
| `heuristic` | 10 | 4.977 | ±0.000 | 4.980 | 91 |
| `fixed_objective_ga` | 10 | 2.554 | ±0.422 | 4.247 | 506,482 |
| `novelty_search` | 10 | 2.326 | ±0.492 | 3.727 | 504,886 |
| `map_elites` | 10 | 2.516 | ±0.304 | 3.463 | 503,630 |
| `reinforce` | 10 | 0.769 | ±0.345 | 1.266 | 500,642 |

_held-out reward is measured on evaluation seeds never used for training._

### Registered analysis of H1

* Novelty search − fixed-objective GA: **-0.228** (95% bootstrap CI [-1.427, +0.998], n=10–10) → **inconclusive**.
* MAP-Elites − fixed-objective GA: **-0.038** (95% bootstrap CI [-0.972, +0.965], n=10–10) → **inconclusive**.

* The registered interval analysis overrides any informal reading of the point
  estimates. Where the 95% CI spans zero the result is reported as **inconclusive**,
  not as a near-miss. Full analysis: `research/reports/H1_powered_analysis.md`.

## 4. Cross-morphology and perturbation transfer

Values are reached reward; morphology variants show `zero-shot → adapted`.

| variant | kind | `fixed_objective_ga` | `novelty_search` | `map_elites` | `reinforce` |
|---|---|---|---|---|---|
| `body_fast` | morphology | 2.68 → 4.98 | 2.07 → 3.17 | 2.21 → 3.99 | 0.79 → 1.98 |
| `body_small` | morphology | 3.01 → 4.98 | 2.22 → 3.17 | 2.59 → 3.99 | 0.79 → 1.98 |
| `hazard_dense` | perturbation | -5.11 | -3.29 | -5.11 | -1.58 |
| `obs_sparse` | perturbation | 0.24 | 0.21 | 0.31 | 0.06 |
| `resource_scarce` | perturbation | 0.90 | 0.64 | 0.89 | 0.35 |
| `rooms` | perturbation | 0.61 | 0.46 | 0.56 | 0.21 |
| `sensor_local` | morphology | 0.44 → 4.98 | 0.44 → 3.17 | 0.51 → 3.99 | 0.19 → 1.98 |
| `sensor_nonspatial` | morphology | -0.12 → 4.98 | 0.01 → 3.17 | -0.07 → 3.99 | -0.07 → 1.98 |
| `slow_actuator` | perturbation | 2.91 | 2.42 | 2.65 | 0.79 |

## Prior exploratory run and replication check

Exploratory experiment `b61d1ac9a348` vs the primary run `d0ef7208a010`. The task and budget are identical; only the seed count differs, so this is a
replication, not a re-tune.

| method | exploratory n | exploratory mean | primary n | primary mean | change |
|---|---|---|---|---|---|
| `random` | 5 | 2.010 | 10 | 2.085 | 0.075 |
| `heuristic` | 5 | 4.977 | 10 | 4.977 | 0.000 |
| `fixed_objective_ga` | 5 | 2.707 | 10 | 2.554 | -0.153 |
| `novelty_search` | 5 | 3.069 | 10 | 2.326 | -0.743 |
| `map_elites` | 5 | 2.637 | 10 | 2.516 | -0.121 |
| `reinforce` | 5 | 1.121 | 10 | 0.769 | -0.353 |

**Determinism cross-check:** 30 overlapping (method, seed) pairs reproduced across the two independent experiments with **0 mismatches**.

> The registered analysis of the primary run is in `research/reports/H1_powered_analysis.md`. Where an exploratory
> direction does not replicate at higher n, the replication governs.

## 5. Compute

* `random`: mean 560 interactions per seed over 10 seed(s).
* `heuristic`: mean 91 interactions per seed over 10 seed(s).
* `fixed_objective_ga`: mean 506,482 interactions per seed over 10 seed(s).
* `novelty_search`: mean 504,886 interactions per seed over 10 seed(s).
* `map_elites`: mean 503,630 interactions per seed over 10 seed(s).
* `reinforce`: mean 500,642 interactions per seed over 10 seed(s).

## 6. Failures

Failed trials: **0** of 60.
No failures were observed; every recorded trial completed.

## 7. Limitations

* **PRELIMINARY.** 10 seeds per method; confidence intervals are wide and no null-hypothesis test is powered.
* A reactive controller is a low-ceiling policy class on tasks requiring planning; this
  bounds achievable effect sizes and compresses between-method differences.
* Single task family. No claim about generality beyond this world.
* The scripted BFS heuristic is a privileged reference, not a like-for-like competitor.
* `reinforce` (a pure-NumPy policy gradient) is sample-inefficient at this budget and, in
  this run, collapsed toward a degenerate policy. This is reported, not hidden; it bounds
  any conclusion about RL rather than supporting one.

## 8. Reproduction

```bash
uv venv --python 3.12 .venv && uv pip install -e '.[dev]' --python .venv/bin/python
.venv/bin/origin-run --config configs/pilot.json --store runs --jobs $(nproc)
.venv/bin/python scripts/make_report.py --store runs --experiment d0ef7208a010
```

Reference environment: Python 3.12.13, Linux-6.18.33.1-microsoft-standard-WSL2-x86_64-with-glibc2.39, 16 CPUs.

## 9. Generated artifacts

* `runs/d0ef7208a010/plots/training_curves.png`
* `runs/d0ef7208a010/plots/transfer.png`
* `runs/d0ef7208a010/plots/descriptors.png`

## 10. Next milestone

Pre-register a powered replication of H1: more seeds, larger budgets, and a
descriptor-designed task where quality-diversity can express its advantage, plus an
articulated-physics embodiment benchmark (Milestone 4) to test morphology transfer beyond
sensor/actuator changes.
