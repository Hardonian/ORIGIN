# Open-Ended Evolution and Cross-Morphology Generalization: A Reproducible Experimental Framework

**Author:** Scott Hardie (Hardonian) · **Status:** PRELIMINARY, not peer reviewed.

> This report was generated automatically from the stored experiment artifacts by
> `scripts/make_report.py`. Every figure below is read from the experiment store; no
> number is hand-entered. Experiment id: `b61d1ac9a348`.

---

## 1. Research question and hypothesis

Pilot comparison of fixed-objective evolution, novelty search, quality-diversity and RL on a deterministic egocentric foraging task, with held-out seeds and morphology/perturbation transfer. Hazards are held out of training and used only as a robustness perturbation.

**H1.** Under an equivalent environment-interaction budget, maintaining behaviourally
diverse populations (novelty search, quality-diversity) improves adaptation to unseen
evaluation environments and to changed morphology relative to fixed-objective evolution.

## 2. Method

Deterministic 10×10 egocentric foraging world; observation is 7-D (energy + resource/hazard bearings), absolute position excluded so policies cannot memorise a layout. Budget: **500,000 environment interactions per method per seed**. Training seeds [11, 22, 33, 44]; held-out test seeds [101, 202, 303, 404] (disjoint). 5 independent RNG seeds.

## 3. Held-out performance (train/test isolated)

| method | n seeds | held-out reward (mean) | standard error | train fitness | mean interactions |
|---|---|---|---|---|---|
| `random` | 5 | 2.010 | ±0.187 | 1.660 | 560 |
| `heuristic` | 5 | 4.977 | ±0.000 | 4.980 | 91 |
| `fixed_objective_ga` | 5 | 2.707 | ±0.602 | 4.406 | 505,815 |
| `novelty_search` | 5 | 3.069 | ±0.712 | 4.343 | 504,850 |
| `map_elites` | 5 | 2.637 | ±0.246 | 3.813 | 503,608 |
| `reinforce` | 5 | 1.121 | ±0.528 | 1.271 | 500,652 |

_held-out reward is measured on evaluation seeds never used for training._

### Directional test of H1

* Novelty search minus fixed-objective GA on held-out reward: **+0.362** (pooled sd ≈ 1.330, n=5–5).
* MAP-Elites minus fixed-objective GA: **-0.071**.
* With this seed count the difference is **not** a powered statistical test; it is a
  preliminary directional signal. See limitations.

## 4. Cross-morphology and perturbation transfer

Values are reached reward; morphology variants show `zero-shot → adapted`.

| variant | kind | `fixed_objective_ga` | `novelty_search` | `map_elites` | `reinforce` |
|---|---|---|---|---|---|
| `body_fast` | morphology | 2.96 → 4.98 | 2.66 → 4.15 | 2.70 → 4.34 | 1.17 → 1.77 |
| `body_small` | morphology | 3.32 → 4.98 | 3.21 → 4.15 | 2.74 → 4.34 | 1.17 → 1.77 |
| `hazard_dense` | perturbation | -4.38 | -3.79 | -4.28 | -0.63 |
| `obs_sparse` | perturbation | 0.31 | 0.31 | 0.36 | 0.06 |
| `resource_scarce` | perturbation | 0.95 | 0.95 | 0.94 | 0.48 |
| `rooms` | perturbation | 0.61 | 0.61 | 0.61 | 0.16 |
| `sensor_local` | morphology | 0.56 → 4.98 | 0.51 → 4.15 | 0.76 → 4.34 | 0.31 → 1.77 |
| `sensor_nonspatial` | morphology | -0.09 → 4.98 | -0.04 → 4.15 | -0.04 → 4.34 | -0.04 → 1.77 |
| `slow_actuator` | perturbation | 3.32 | 3.56 | 2.85 | 1.17 |

## 5. Compute

* `random`: mean 560 interactions per seed over 5 seed(s).
* `heuristic`: mean 91 interactions per seed over 5 seed(s).
* `fixed_objective_ga`: mean 505,815 interactions per seed over 5 seed(s).
* `novelty_search`: mean 504,850 interactions per seed over 5 seed(s).
* `map_elites`: mean 503,608 interactions per seed over 5 seed(s).
* `reinforce`: mean 500,652 interactions per seed over 5 seed(s).

## 6. Failures

Failed trials: **0** of 30.
No failures were observed; every recorded trial completed.

## 7. Limitations

* **PRELIMINARY.** 5 seeds per method; confidence intervals are wide and no null-hypothesis test is powered.
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
.venv/bin/python scripts/make_report.py --store runs --experiment b61d1ac9a348
```

Reference environment: Python 3.12.13, Linux-6.18.33.1-microsoft-standard-WSL2-x86_64-with-glibc2.39, 16 CPUs.

## 9. Generated artifacts

* `runs/b61d1ac9a348/plots/training_curves.png`
* `runs/b61d1ac9a348/plots/transfer.png`
* `runs/b61d1ac9a348/plots/descriptors.png`

## 10. Next milestone

Pre-register a powered replication of H1: more seeds, larger budgets, and a
descriptor-designed task where quality-diversity can express its advantage, plus an
articulated-physics embodiment benchmark (Milestone 4) to test morphology transfer beyond
sensor/actuator changes.
