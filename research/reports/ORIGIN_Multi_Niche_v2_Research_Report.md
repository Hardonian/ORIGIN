# Open-Ended Evolution and Cross-Morphology Generalization: A Reproducible Experimental Framework

**Author:** Scott Hardie (Hardonian) · **Status:** 64 seeds; interval-based registered analysis in `research/reports/H1_multi_niche_v2_analysis.md`. Not peer reviewed.

> This report was generated automatically from the stored experiment artifacts by
> `scripts/make_report.py`. Every figure below is read from the experiment store; no
> number is hand-entered. Experiment id: `5058bcacd3de`.

---

## 1. Research question and hypothesis

Pre-registered, paired replication of H1.MN (research/protocols/multi_niche_replication_v2.md). The sole confirmatory endpoint is the per-seed mean held-out adapted transfer reward across the five registered ecological shocks; its exact aggregation and decision rule are fixed before the run.

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
| `fixed_objective_ga` | 64 | -2.082 | ±0.180 | -0.275 | 34,534 |
| `map_elites` | 64 | -2.072 | ±0.165 | 0.228 | 28,778 |

_held-out reward is measured on evaluation seeds never used for training._

### Unperturbed base-task context (not ecological-transfer analysis)

The following held-out table is descriptive only. It cannot decide a multi-niche transfer
hypothesis because that requires an explicitly fixed aggregation across the registered shocks.
Use `scripts/analyze_multi_niche.py` for a complete, fail-closed transfer analysis.

## 4. Cross-morphology and perturbation transfer

Values are reached reward; morphology variants show `zero-shot → adapted`.

| variant | kind | `fixed_objective_ga` | `map_elites` |
| --- | --- | --- | --- |
| `body_fast` | morphology | -2.56 → -2.72 | -2.10 → -2.38 |
| `body_small` | morphology | -2.68 → -2.83 | -2.08 → -2.29 |
| `hazard_dense` | perturbation | -3.99 | -3.17 |
| `niche_a_only` | niche | -2.86 → -2.25 | -2.93 → -1.71 |
| `niche_b_only` | niche | -1.61 → -1.27 | -1.65 → -0.20 |
| `niche_payoff_swap` | niche | -2.76 → -2.87 | -2.32 → -2.50 |
| `niche_scarcity_shock` | niche | -2.72 → -2.86 | -2.41 → -2.29 |
| `niche_toxic_hazard` | niche | -3.19 → -3.23 | -2.57 → -2.50 |
| `obs_sparse` | perturbation | -4.03 | -4.04 |
| `resource_scarce` | perturbation | -2.75 | -2.11 |
| `rooms` | perturbation | -4.15 | -4.35 |
| `sensor_local` | morphology | -3.10 → -3.18 | -3.37 → -4.07 |
| `sensor_nonspatial` | morphology | -4.26 → -4.26 | -4.93 → -5.94 |
| `slow_actuator` | perturbation | -2.62 | -2.06 |

### Ecological Shock Adaptation Analysis

Adaptation gains ($\Delta = \text{adapted} - \text{zero\_shot}$) under ecological shocks:

| variant | GA zero → adapt (gain) | MAP-Elites zero → adapt (gain) | gain advantage (ME − GA) |
| --- | --- | --- | --- |
| `niche_a_only` | -2.86 → -2.25 (+0.61) | -2.93 → -1.71 (+1.23) | **+0.62** |
| `niche_b_only` | -1.61 → -1.27 (+0.34) | -1.65 → -0.20 (+1.45) | **+1.11** |
| `niche_payoff_swap` | -2.76 → -2.87 (-0.11) | -2.32 → -2.50 (-0.17) | **-0.06** |
| `niche_scarcity_shock` | -2.72 → -2.86 (-0.14) | -2.41 → -2.29 (+0.12) | **+0.27** |
| `niche_toxic_hazard` | -3.19 → -3.23 (-0.04) | -2.57 → -2.50 (+0.08) | **+0.12** |

## 5. Compute

* `random`: mean 0 interactions per seed over 64 seed(s).
* `heuristic`: mean 0 interactions per seed over 64 seed(s).
* `fixed_objective_ga`: mean 34,534 interactions per seed over 64 seed(s).
* `map_elites`: mean 28,778 interactions per seed over 64 seed(s).

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
.venv/bin/origin-run --config configs/multi_niche_transfer_replication_v2.json --store runs --jobs $(nproc)
.venv/bin/python scripts/make_report.py --store runs --experiment 5058bcacd3de
.venv/bin/python scripts/analyze_multi_niche.py --store runs --experiment 5058bcacd3de --bootstrap-seed 20261014 --protocol-doc research/protocols/multi_niche_pilot.md --out research/reports/H1_multi_niche_v2_analysis.md
```

Reference environment: Python 3.13.9, Windows-11-10.0.29683-SP0, 24 CPUs.

## 9. Generated artifacts

* `runs\5058bcacd3de\plots\training_curves.png`
* `runs\5058bcacd3de\plots\transfer.png`
* `runs\5058bcacd3de\plots\descriptors.png`

## 10. Next milestone

Pre-register and run the powered multi-niche replication campaign (n=40 paired seeds)
to decisively evaluate ecological shock adaptation and asymmetric specialist advantage.
