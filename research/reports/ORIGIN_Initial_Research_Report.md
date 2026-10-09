> ## Legacy evidence notice — 2026-10-09
>
> This generated single-niche report is retained for historical audit only. Its
> interaction totals predate strict-cap semantics, and its adaptation-gain
> figures predate disjoint adaptation/evaluation seeds. Do not cite it as
> current compute or held-out transfer evidence; see `RESULT_PROVENANCE.md`.

# Open-Ended Evolution and Cross-Morphology Generalization: A Reproducible Experimental Framework

**Author:** Scott Hardie (Hardonian) · **Status:** 40 seeds; interval-based registered analysis in `research/reports/H1_v3_decisive_analysis.md`. Not peer reviewed.

> This report was generated automatically from the stored experiment artifacts by
> `scripts/make_report.py`. Every figure below is read from the experiment store; no
> number is hand-entered. Experiment id: `8f92870eaeb0`.

---

## 1. Research question and hypothesis

Study v3 (research/protocols/paired_v3_power.md): power-sized and scoped BEFORE the run to the one comparison that can be resolved. MAP-Elites vs fixed-objective GA, paired design, 40 fresh seeds (21-60, disjoint from studies 1 and v2) giving a minimum detectable paired effect of ~0.70 at 80% power. novelty_search is out of scope: the power analysis requires n~321 for the effect it showed. Same task and budget as studies 1/v2; no re-tuning.

**H1.** Under an equivalent environment-interaction budget, maintaining behaviourally
diverse populations (novelty search, quality-diversity) improves adaptation to unseen
evaluation environments and to changed morphology relative to fixed-objective evolution.

## 2. Method

Deterministic 10×10 egocentric foraging world; observation is 7-D (energy + resource/hazard bearings), absolute position excluded so policies cannot memorise a layout. Budget: **500,000 environment interactions per method per seed**. Training seeds [11, 22, 33, 44]; held-out test seeds [101, 202, 303, 404] (disjoint). 40 independent RNG seeds.

## 3. Held-out performance (train/test isolated)

| method | n seeds | held-out reward (mean) | standard error | train fitness | mean interactions |
|---|---|---|---|---|---|
| `random` | 40 | 1.785 | ±0.094 | 1.779 | 559 |
| `heuristic` | 40 | 4.977 | ±0.000 | 4.980 | 91 |
| `fixed_objective_ga` | 40 | 2.698 | ±0.176 | 3.574 | 507,982 |
| `map_elites` | 40 | 2.477 | ±0.202 | 3.402 | 503,543 |

_held-out reward is measured on evaluation seeds never used for training._

### Registered analysis of H1 (paired design)

* MAP-Elites − fixed-objective GA: **-0.221** (95% bootstrap CI [-0.721, +0.262], n=40) → **inconclusive**.

* The registered interval analysis overrides any informal reading of the point
  estimates. Where the 95% CI spans zero the result is reported as **inconclusive**,
  not as a near-miss. Full analysis of this run:
  `research/reports/H1_v3_decisive_analysis.md`; earlier studies are in the same directory.

## 4. Cross-morphology and perturbation transfer

Values are reached reward; morphology variants show `zero-shot → adapted`.

| variant | kind | `fixed_objective_ga` | `map_elites` |
|---|---|---|---|
| `body_fast` | morphology | 2.19 → 4.22 | 2.06 → 4.18 |
| `body_small` | morphology | 2.79 → 4.22 | 2.42 → 4.18 |
| `hazard_dense` | perturbation | -2.46 | -6.52 |
| `obs_sparse` | perturbation | 0.33 | 0.28 |
| `resource_scarce` | perturbation | 0.92 | 0.82 |
| `rooms` | perturbation | 0.49 | 0.48 |
| `sensor_local` | morphology | 0.55 → 4.22 | 0.70 → 4.18 |
| `sensor_nonspatial` | morphology | -0.04 → 4.22 | -0.00 → 4.18 |
| `slow_actuator` | perturbation | 2.86 | 2.51 |

## Prior exploratory run and replication check

Exploratory experiment `c7363fb00344` vs the primary run `8f92870eaeb0`. The task and budget are identical; only the seed count differs, so this is a
replication, not a re-tune.

| method | exploratory n | exploratory mean | primary n | primary mean | change |
|---|---|---|---|---|---|
| `random` | 10 | 1.585 | 40 | 1.785 | 0.200 |
| `heuristic` | 10 | 4.977 | 40 | 4.977 | 0.000 |
| `fixed_objective_ga` | 10 | 2.395 | 40 | 2.698 | 0.303 |
| `map_elites` | 10 | 3.185 | 40 | 2.477 | -0.708 |

**Determinism cross-check:** the two experiments share **no** seeds by design (disjoint seed sets), so no cross-experiment comparison applies here. Cross-experiment determinism was verified separately on the pilot and study 1 (30 overlapping pairs, **0 mismatches**, exact to 6 dp).

> The registered analysis of the primary run is in `research/reports/H1_v3_decisive_analysis.md`.
> Where a direction is not established by its registered interval analysis, it is
> reported as inconclusive rather than as a near-miss or a trend.

## 5. Compute

* `random`: mean 559 interactions per seed over 40 seed(s).
* `heuristic`: mean 91 interactions per seed over 40 seed(s).
* `fixed_objective_ga`: mean 507,982 interactions per seed over 40 seed(s).
* `map_elites`: mean 503,543 interactions per seed over 40 seed(s).

## 6. Failures

Failed trials: **0** of 160.
No failures were observed; every recorded trial completed.

## 7. Limitations

* **PRELIMINARY.** 40 seeds per method; confidence intervals are wide and no null-hypothesis test is powered.
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
.venv/bin/python scripts/make_report.py --store runs --experiment 8f92870eaeb0
```

Reference environment: Python 3.12.13, Linux-6.18.33.1-microsoft-standard-WSL2-x86_64-with-glibc2.39, 16 CPUs.

## 9. Generated artifacts

* `runs/8f92870eaeb0/plots/training_curves.png`
* `runs/8f92870eaeb0/plots/transfer.png`
* `runs/8f92870eaeb0/plots/descriptors.png`

## 10. Next milestone

Pre-register a powered replication of H1: more seeds, larger budgets, and a
descriptor-designed task where quality-diversity can express its advantage, plus an
articulated-physics embodiment benchmark (Milestone 4) to test morphology transfer beyond
sensor/actuator changes.
