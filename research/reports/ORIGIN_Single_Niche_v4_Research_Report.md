# Open-Ended Evolution and Cross-Morphology Generalization: A Reproducible Experimental Framework

**Author:** Scott Hardie (Hardonian) · **Status:** 40 seeds; interval-based registered analysis in `research/reports/H1_v4_strict_cap_analysis.md`. Not peer reviewed.

> This report was generated automatically from the stored experiment artifacts by
> `scripts/make_report.py`. Every figure below is read from the experiment store; no
> number is hand-entered. Experiment id: `59427f9116fa`.

---

## 1. Research question and hypothesis

Fresh strict-cap replication of the single-niche H1-ME comparison (research/protocols/paired_v4_strict_cap.md). It remeasures the legacy task with unchanged optimizer settings, fresh method seeds, strict batch reservation, and disjoint adaptation/evaluation seeds. The confirmatory endpoint is held-out base-task reward; transfer results are descriptive.

**H1.** Under an equivalent environment-interaction budget, maintaining behaviourally
diverse populations (novelty search, quality-diversity) improves adaptation to unseen
evaluation environments and to changed morphology relative to fixed-objective evolution.

## 2. Method

Deterministic 10×10 egocentric foraging world; observation is 7-D (energy + resource/hazard bearings), absolute position excluded so policies cannot memorise a layout. Budget: **500,000 environment interactions per method per seed**. Training seeds [11, 22, 33, 44]; held-out test seeds [101, 202, 303, 404] (disjoint). 40 independent RNG seeds.

## 3. Held-out performance (train/test isolated)

| method | n seeds | held-out reward (mean) | standard error | train fitness | mean interactions |
| --- | --- | --- | --- | --- | --- |
| `random` | 40 | 2.610 | ±0.000 | 2.610 | 0 |
| `heuristic` | 40 | 4.977 | ±0.000 | 4.980 | 0 |
| `fixed_objective_ga` | 40 | 2.194 | ±0.230 | 3.436 | 487,961 |
| `map_elites` | 40 | 2.873 | ±0.189 | 3.755 | 495,269 |

_held-out reward is measured on evaluation seeds never used for training._

### Registered analysis of H1 (paired design)

* MAP-Elites − fixed-objective GA: **+0.679** (95% bootstrap CI [+0.112, +1.241], n=40) → **supported (direction)**.

* The registered interval analysis overrides any informal reading of the point
  estimates. Where the 95% CI spans zero the result is reported as **inconclusive**,
  not as a near-miss. Full analysis of this run:
  `research/reports/H1_v4_strict_cap_analysis.md`; earlier studies are in the same directory.

## 4. Cross-morphology and perturbation transfer

Values are reached reward; morphology variants show `zero-shot → adapted`.

| variant | kind | `fixed_objective_ga` | `map_elites` |
| --- | --- | --- | --- |
| `body_fast` | morphology | 1.87 → 2.13 | 2.35 → 2.93 |
| `body_small` | morphology | 2.39 → 2.44 | 2.98 → 3.29 |
| `hazard_dense` | perturbation | -3.79 | -4.49 |
| `obs_sparse` | perturbation | 0.27 | 0.36 |
| `resource_scarce` | perturbation | 0.85 | 0.99 |
| `rooms` | perturbation | 0.47 | 0.54 |
| `sensor_local` | morphology | 0.59 → 0.61 | 0.71 → 0.81 |
| `sensor_nonspatial` | morphology | -0.04 → -0.03 | -0.02 → -0.03 |
| `slow_actuator` | perturbation | 2.40 | 3.07 |

## 5. Compute

* `random`: mean 0 interactions per seed over 40 seed(s).
* `heuristic`: mean 0 interactions per seed over 40 seed(s).
* `fixed_objective_ga`: mean 487,961 interactions per seed over 40 seed(s).
* `map_elites`: mean 495,269 interactions per seed over 40 seed(s).

## 6. Failures

Failed trials: **0** of 160.
No failures were observed; every recorded trial completed.

## 7. Limitations

* A reactive controller is a low-ceiling policy class on tasks requiring planning; this
  bounds achievable effect sizes and compresses between-method differences.
* Single task family. No claim about generality beyond this world.
* The scripted BFS heuristic is a privileged reference, not a like-for-like competitor.
* `reinforce` is a functional, non-confirmatory policy-gradient control. It is
  excluded from powered primary comparisons until a fresh RL-specific study
  establishes held-out performance.

## 8. Reproduction

```bash
uv venv --python 3.12 .venv && uv pip install -e '.[dev]' --python .venv/bin/python
.venv/bin/origin-run --config configs/single_niche_strict_cap_replication_v4.json --store runs --jobs $(nproc)
.venv/bin/python scripts/make_report.py --store runs --experiment 59427f9116fa --design paired --analysis-file H1_v4_strict_cap_analysis.md --bootstrap-seed 20261016 --out research\reports\ORIGIN_Single_Niche_v4_Research_Report.md
.venv/bin/python scripts/analyze.py --store runs --experiment 59427f9116fa --design paired --bootstrap-seed 20261016 --protocol-doc research/protocols/paired_v4_strict_cap.md --out research/reports/H1_v4_strict_cap_analysis.md
```

Reference environment: Python 3.13.9, Windows-11-10.0.29683-SP0, 24 CPUs.

## 9. Generated artifacts

* `runs\59427f9116fa\plots\training_curves.png`
* `runs\59427f9116fa\plots\transfer.png`
* `runs\59427f9116fa\plots\descriptors.png`

## 10. Next milestone

The strict-cap single-niche replication is complete. Any extension must use a new
pre-registered endpoint and fresh method seeds; the registered v4 analysis remains
the only basis for its current confirmatory conclusion.
