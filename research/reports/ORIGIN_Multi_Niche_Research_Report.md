> ## Exploratory evidence notice — 2026-10-09
>
> This pilot is retained as an archival instrument check, not a confirmatory
> H1.MN result: it predates strict batch reservation and a uniquely fixed
> ecological-shock aggregation. Use `H1_multi_niche_v3_analysis.md` for the
> strict-cap confirmatory replication and see `RESULT_PROVENANCE.md` before
> citing this artifact.

# Open-Ended Evolution and Cross-Morphology Generalization: A Reproducible Experimental Framework

**Author:** Scott Hardie (Hardonian) · **Status:** 5 seeds; interval-based registered analysis in `research/reports/H1_multi_niche_analysis.md`. Not peer reviewed.

> This report was generated automatically from the stored experiment artifacts by
> `scripts/make_report.py`. Every figure below is read from the experiment store; no
> number is hand-entered. Experiment id: `f8f4c952a5c3`.

---

## 1. Research question and hypothesis

Multi-Niche Grid World transfer pilot: testing whether Quality-Diversity (MAP-Elites) maintaining a 2D archive of resource-A and resource-B niche specializations adapts more effectively to ecological shocks (payoff swap, toxic niche, scarcity shock) than fixed-objective GA.

**H1.** Under an equivalent environment-interaction budget, maintaining behaviourally
diverse populations (novelty search, quality-diversity) improves adaptation to unseen
evaluation environments and to changed morphology relative to fixed-objective evolution.

## 2. Method

Deterministic 10×10 egocentric foraging world; observation is 7-D (energy + resource/hazard bearings), absolute position excluded so policies cannot memorise a layout. Budget: **25,000 environment interactions per method per seed**. Training seeds [11, 22, 33, 44]; held-out test seeds [101, 202, 303, 404] (disjoint). 5 independent RNG seeds.

## 3. Held-out performance (train/test isolated)

| method | n seeds | held-out reward (mean) | standard error | train fitness | mean interactions |
| --- | --- | --- | --- | --- | --- |
| `random` | 5 | 3.513 | ±0.000 | 3.800 | 0 |
| `heuristic` | 5 | 70.175 | ±0.000 | 73.675 | 0 |
| `fixed_objective_ga` | 5 | -2.010 | ±1.050 | 0.018 | 34,527 |
| `map_elites` | 5 | -1.973 | ±0.723 | 0.235 | 28,800 |

_held-out reward is measured on evaluation seeds never used for training._

### Unperturbed base-task context (not ecological-transfer analysis)

The following held-out table is descriptive only. It cannot decide a multi-niche transfer
hypothesis because that requires an explicitly fixed aggregation across the registered shocks.
Use `scripts/analyze_multi_niche.py` for a complete, fail-closed transfer analysis.

## 4. Cross-morphology and perturbation transfer

Values are reached reward; morphology variants show `zero-shot → adapted`.

| variant | kind | `fixed_objective_ga` | `map_elites` |
| --- | --- | --- | --- |
| `body_fast` | morphology | -1.72 → -1.65 | -2.50 → -2.93 |
| `body_small` | morphology | -2.01 → -1.66 | -1.83 → -2.21 |
| `hazard_dense` | perturbation | -2.95 | -2.44 |
| `niche_a_only` | niche | -2.35 → -2.77 | -2.64 → -0.94 |
| `niche_b_only` | niche | -2.87 → 0.53 | -1.94 → -1.64 |
| `niche_payoff_swap` | niche | -1.86 → -2.14 | -2.50 → -2.25 |
| `niche_scarcity_shock` | niche | -1.96 → -1.67 | -1.75 → -1.60 |
| `niche_toxic_hazard` | niche | -2.33 → -2.61 | -1.94 → -3.71 |
| `obs_sparse` | perturbation | -3.11 | -2.12 |
| `resource_scarce` | perturbation | -1.81 | -1.56 |
| `rooms` | perturbation | -2.43 | -2.24 |
| `sensor_local` | morphology | -4.06 → -5.61 | -4.12 → -4.09 |
| `sensor_nonspatial` | morphology | -5.53 → -6.79 | -5.62 → -5.62 |
| `slow_actuator` | perturbation | -2.02 | -1.82 |

### Ecological Shock Adaptation Analysis

Adaptation gains ($\Delta = \text{adapted} - \text{zero\_shot}$) under ecological shocks:

| variant | GA zero → adapt (gain) | MAP-Elites zero → adapt (gain) | gain advantage (ME − GA) |
| --- | --- | --- | --- |
| `niche_a_only` | -2.35 → -2.77 (-0.42) | -2.64 → -0.94 (+1.69) | **+2.11** |
| `niche_b_only` | -2.87 → +0.53 (+3.40) | -1.94 → -1.64 (+0.30) | **-3.10** |
| `niche_payoff_swap` | -1.86 → -2.14 (-0.28) | -2.50 → -2.25 (+0.25) | **+0.52** |
| `niche_scarcity_shock` | -1.96 → -1.67 (+0.29) | -1.75 → -1.60 (+0.15) | **-0.14** |
| `niche_toxic_hazard` | -2.33 → -2.61 (-0.27) | -1.94 → -3.71 (-1.77) | **-1.49** |

## 5. Compute

* `random`: mean 0 interactions per seed over 5 seed(s).
* `heuristic`: mean 0 interactions per seed over 5 seed(s).
* `fixed_objective_ga`: mean 34,527 interactions per seed over 5 seed(s).
* `map_elites`: mean 28,800 interactions per seed over 5 seed(s).

## 6. Failures

Failed trials: **0** of 20.
No failures were observed; every recorded trial completed.

## 7. Limitations

* **PRELIMINARY.** 5 seeds per method; confidence intervals are wide and no null-hypothesis test is powered.
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
.venv/bin/origin-run --config configs/multi_niche_transfer.json --store runs --jobs $(nproc)
.venv/bin/python scripts/make_report.py --store runs --experiment f8f4c952a5c3
.venv/bin/python scripts/analyze_multi_niche.py --store runs --experiment f8f4c952a5c3 --bootstrap-seed 20261011 --protocol-doc research/protocols/multi_niche_pilot.md --out research/reports/H1_multi_niche_analysis.md
```

Reference environment: Python 3.13.9, Windows-11-10.0.29683-SP0, 24 CPUs.

## 9. Generated artifacts

* `runs\f8f4c952a5c3\plots\training_curves.png`
* `runs\f8f4c952a5c3\plots\transfer.png`
* `runs\f8f4c952a5c3\plots\descriptors.png`

## 10. Next milestone

Pre-register and run the powered multi-niche replication campaign (n=40 paired seeds)
to decisively evaluate ecological shock adaptation and asymmetric specialist advantage.
