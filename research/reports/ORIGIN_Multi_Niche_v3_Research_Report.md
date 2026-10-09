# Open-Ended Evolution and Cross-Morphology Generalization: A Reproducible Experimental Framework

**Author:** Scott Hardie (Hardonian) · **Status:** 64 seeds; interval-based registered analysis in `research/reports/H1_multi_niche_v3_analysis.md`. Not peer reviewed.

> This report was generated automatically from the stored experiment artifacts by
> `scripts/make_report.py`. Every figure below is read from the experiment store; no
> number is hand-entered. Experiment id: `1e8559d6de45`.

---

## 1. Research question and hypothesis

Fresh, strictly budget-capped replication of H1.MN (research/protocols/multi_niche_replication_v3.md). The confirmatory endpoint is the per-seed mean held-out adapted transfer reward across the five registered ecological shocks. Every full optimizer batch is reserved before evaluation, so no learned trial may exceed 25,000 training environment steps.

**H1.** Under an equivalent environment-interaction budget, maintaining behaviourally
diverse populations (novelty search, quality-diversity) improves adaptation to unseen
evaluation environments and to changed morphology relative to fixed-objective evolution.

## 2. Method

Deterministic 10×10 egocentric foraging world; observation is 7-D (energy + resource/hazard bearings), absolute position excluded so policies cannot memorise a layout. Budget: **25,000 environment interactions per method per seed**. Training seeds [11, 22, 33, 44]; held-out test seeds [101, 202, 303, 404] (disjoint). 64 independent RNG seeds.

## 3. Held-out performance (train/test isolated)

| method | n seeds | held-out reward (mean) | standard error | train fitness | mean interactions |
| --- | --- | --- | --- | --- | --- |
| `random` | 64 | 3.513 | ±0.000 | 3.800 | 0 |
| `heuristic` | 64 | 70.175 | ±0.000 | 73.675 | 0 |
| `fixed_objective_ga` | 64 | -2.043 | ±0.190 | -0.427 | 23,026 |
| `map_elites` | 64 | -1.730 | ±0.168 | 0.125 | 23,018 |

_held-out reward is measured on evaluation seeds never used for training._

### Unperturbed base-task context (not ecological-transfer analysis)

The following held-out table is descriptive only. It cannot decide a multi-niche transfer
hypothesis because that requires an explicitly fixed aggregation across the registered shocks.
Use `scripts/analyze_multi_niche.py` for a complete, fail-closed transfer analysis.

## 4. Cross-morphology and perturbation transfer

Values are reached reward; morphology variants show `zero-shot → adapted`.

| variant | kind | `fixed_objective_ga` | `map_elites` |
| --- | --- | --- | --- |
| `body_fast` | morphology | -2.25 → -2.63 | -1.77 → -2.07 |
| `body_small` | morphology | -2.33 → -2.70 | -1.71 → -2.01 |
| `hazard_dense` | perturbation | -3.80 | -3.34 |
| `niche_a_only` | niche | -2.71 → -2.06 | -3.21 → -1.87 |
| `niche_b_only` | niche | -1.66 → -1.13 | -1.23 → -0.35 |
| `niche_payoff_swap` | niche | -2.45 → -3.08 | -1.95 → -2.24 |
| `niche_scarcity_shock` | niche | -2.65 → -2.42 | -2.02 → -2.52 |
| `niche_toxic_hazard` | niche | -2.87 → -3.11 | -2.29 → -2.72 |
| `obs_sparse` | perturbation | -3.82 | -3.92 |
| `resource_scarce` | perturbation | -2.38 | -1.76 |
| `rooms` | perturbation | -4.02 | -4.46 |
| `sensor_local` | morphology | -2.79 → -2.93 | -3.70 → -3.91 |
| `sensor_nonspatial` | morphology | -3.49 → -3.69 | -5.23 → -5.45 |
| `slow_actuator` | perturbation | -2.35 | -1.71 |

### Ecological Shock Adaptation Analysis

Adaptation gains ($\Delta = \text{adapted} - \text{zero\_shot}$) under ecological shocks:

| variant | GA zero → adapt (gain) | MAP-Elites zero → adapt (gain) | gain advantage (ME − GA) |
| --- | --- | --- | --- |
| `niche_a_only` | -2.71 → -2.06 (+0.64) | -3.21 → -1.87 (+1.33) | **+0.69** |
| `niche_b_only` | -1.66 → -1.13 (+0.54) | -1.23 → -0.35 (+0.88) | **+0.34** |
| `niche_payoff_swap` | -2.45 → -3.08 (-0.63) | -1.95 → -2.24 (-0.29) | **+0.33** |
| `niche_scarcity_shock` | -2.65 → -2.42 (+0.23) | -2.02 → -2.52 (-0.51) | **-0.73** |
| `niche_toxic_hazard` | -2.87 → -3.11 (-0.24) | -2.29 → -2.72 (-0.43) | **-0.19** |

## 5. Compute

* `random`: mean 0 interactions per seed over 64 seed(s).
* `heuristic`: mean 0 interactions per seed over 64 seed(s).
* `fixed_objective_ga`: mean 23,026 interactions per seed over 64 seed(s).
* `map_elites`: mean 23,018 interactions per seed over 64 seed(s).

## 6. Failures

Failed trials: **0** of 256.
No failures were observed; every recorded trial completed.

## 7. Limitations

* **PRELIMINARY.** 64 seeds per method; confidence intervals are wide and no null-hypothesis test is powered.
* The automatic base-task report intentionally does not supply a primary transfer verdict;
  shocks are repeated measurements within a method seed and require the dedicated analysis.
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
.venv/bin/origin-run --config configs/multi_niche_transfer_replication_v3.json --store runs --jobs $(nproc)
.venv/bin/python scripts/make_report.py --store runs --experiment 1e8559d6de45
.venv/bin/python scripts/analyze_multi_niche.py --store runs --experiment 1e8559d6de45 --bootstrap-seed 20261015 --protocol-doc research/protocols/multi_niche_pilot.md --out research/reports/H1_multi_niche_v3_analysis.md
```

Reference environment: Python 3.13.9, Windows-11-10.0.29683-SP0, 24 CPUs.

## 9. Generated artifacts

* `runs\1e8559d6de45\plots\training_curves.png`
* `runs\1e8559d6de45\plots\transfer.png`
* `runs\1e8559d6de45\plots\descriptors.png`

## 10. Next milestone

Pre-register and run the powered multi-niche replication campaign (n=40 paired seeds)
to decisively evaluate ecological shock adaptation and asymmetric specialist advantage.
