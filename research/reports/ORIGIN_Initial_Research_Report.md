# Open-Ended Evolution and Cross-Morphology Generalization: A Reproducible Experimental Framework

**Author:** Scott Hardie (Hardonian) · **Status:** 10 seeds; interval-based registered analysis in `research/reports/H1_paired_v2_analysis.md`. Not peer reviewed.

> This report was generated automatically from the stored experiment artifacts by
> `scripts/make_report.py`. Every figure below is read from the experiment store; no
> number is hand-entered. Experiment id: `c7363fb00344`.

---

## 1. Research question and hypothesis

Study v2 (research/protocols/paired_v2.md): identical task and budget, FRESH seeds 11-20 (disjoint from study 1), with a pre-registered PAIRED primary analysis (paired bootstrap CI + Wilcoxon signed-rank). Correlated by method seed because all methods share identical training environments. No re-tuning; no re-analysis of study 1.

**H1.** Under an equivalent environment-interaction budget, maintaining behaviourally
diverse populations (novelty search, quality-diversity) improves adaptation to unseen
evaluation environments and to changed morphology relative to fixed-objective evolution.

## 2. Method

Deterministic 10×10 egocentric foraging world; observation is 7-D (energy + resource/hazard bearings), absolute position excluded so policies cannot memorise a layout. Budget: **500,000 environment interactions per method per seed**. Training seeds [11, 22, 33, 44]; held-out test seeds [101, 202, 303, 404] (disjoint). 10 independent RNG seeds.

## 3. Held-out performance (train/test isolated)

| method | n seeds | held-out reward (mean) | standard error | train fitness | mean interactions |
|---|---|---|---|---|---|
| `random` | 10 | 1.585 | ±0.177 | 1.585 | 560 |
| `heuristic` | 10 | 4.977 | ±0.000 | 4.980 | 91 |
| `fixed_objective_ga` | 10 | 2.395 | ±0.455 | 3.119 | 507,165 |
| `novelty_search` | 10 | 2.726 | ±0.446 | 3.623 | 508,355 |
| `map_elites` | 10 | 3.185 | ±0.278 | 4.065 | 504,660 |
| `reinforce` | 10 | 1.453 | ±0.446 | 2.140 | 500,467 |

_held-out reward is measured on evaluation seeds never used for training._

### Registered analysis of H1 (paired design)

* Novelty search − fixed-objective GA: **+0.331** (95% bootstrap CI [-0.932, +1.549], n=10) → **inconclusive**.
* MAP-Elites − fixed-objective GA: **+0.790** (95% bootstrap CI [-0.161, +1.645], n=10) → **inconclusive**.

* The registered interval analysis overrides any informal reading of the point
  estimates. Where the 95% CI spans zero the result is reported as **inconclusive**,
  not as a near-miss. Full analyses:
  `research/reports/H1_powered_analysis.md` (study 1) and
  `research/reports/H1_paired_v2_analysis.md` (study v2).

## 4. Cross-morphology and perturbation transfer

Values are reached reward; morphology variants show `zero-shot → adapted`.

| variant | kind | `fixed_objective_ga` | `novelty_search` | `map_elites` | `reinforce` |
|---|---|---|---|---|---|
| `body_fast` | morphology | 2.09 → 3.57 | 2.01 → 4.60 | 2.42 → 3.99 | 1.45 → 2.71 |
| `body_small` | morphology | 2.47 → 3.57 | 3.03 → 4.60 | 3.26 → 3.99 | 1.45 → 2.71 |
| `hazard_dense` | perturbation | -4.61 | -2.79 | -3.06 | -4.97 |
| `obs_sparse` | perturbation | 0.36 | 0.36 | 0.41 | 0.11 |
| `resource_scarce` | perturbation | 0.89 | 0.92 | 0.89 | 0.50 |
| `rooms` | perturbation | 0.54 | 0.56 | 0.56 | 0.39 |
| `sensor_local` | morphology | 0.56 → 3.57 | 0.76 → 4.60 | 0.94 → 3.99 | 0.41 → 2.71 |
| `sensor_nonspatial` | morphology | -0.07 → 3.57 | -0.04 → 4.60 | -0.02 → 3.99 | -0.07 → 2.71 |
| `slow_actuator` | perturbation | 2.60 | 3.03 | 3.29 | 1.53 |

## Prior exploratory run and replication check

Exploratory experiment `d0ef7208a010` vs the primary run `c7363fb00344`. The task and budget are identical; only the seed count differs, so this is a
replication, not a re-tune.

| method | exploratory n | exploratory mean | primary n | primary mean | change |
|---|---|---|---|---|---|
| `random` | 10 | 2.085 | 10 | 1.585 | -0.500 |
| `heuristic` | 10 | 4.977 | 10 | 4.977 | 0.000 |
| `fixed_objective_ga` | 10 | 2.554 | 10 | 2.395 | -0.159 |
| `novelty_search` | 10 | 2.326 | 10 | 2.726 | 0.400 |
| `map_elites` | 10 | 2.516 | 10 | 3.185 | 0.669 |
| `reinforce` | 10 | 0.769 | 10 | 1.453 | 0.684 |

**Determinism cross-check:** the two experiments share **no** seeds by design (disjoint seed sets), so no cross-experiment comparison applies here. Cross-experiment determinism was verified separately on the pilot and study 1 (30 overlapping pairs, **0 mismatches**, exact to 6 dp).

> The registered analysis of the primary run is in `research/reports/H1_paired_v2_analysis.md`.
> Where a direction is not established by its registered interval analysis, it is
> reported as inconclusive rather than as a near-miss or a trend.

## 5. Compute

* `random`: mean 560 interactions per seed over 10 seed(s).
* `heuristic`: mean 91 interactions per seed over 10 seed(s).
* `fixed_objective_ga`: mean 507,165 interactions per seed over 10 seed(s).
* `novelty_search`: mean 508,355 interactions per seed over 10 seed(s).
* `map_elites`: mean 504,660 interactions per seed over 10 seed(s).
* `reinforce`: mean 500,467 interactions per seed over 10 seed(s).

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
.venv/bin/python scripts/make_report.py --store runs --experiment c7363fb00344
```

Reference environment: Python 3.12.13, Linux-6.18.33.1-microsoft-standard-WSL2-x86_64-with-glibc2.39, 16 CPUs.

## 9. Generated artifacts

* `runs/c7363fb00344/plots/training_curves.png`
* `runs/c7363fb00344/plots/transfer.png`
* `runs/c7363fb00344/plots/descriptors.png`

## 10. Next milestone

Pre-register a powered replication of H1: more seeds, larger budgets, and a
descriptor-designed task where quality-diversity can express its advantage, plus an
articulated-physics embodiment benchmark (Milestone 4) to test morphology transfer beyond
sensor/actuator changes.
