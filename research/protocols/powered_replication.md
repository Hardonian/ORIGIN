# Protocol — Powered Replication of H1 (pre-registered)

**Registered before the run.** This document fixes the design and the analysis
*before* any result from this experiment is observed, so the analysis cannot be
chosen after the fact to fit an outcome.

## Hypothesis

**H1.** Under an equivalent environment-interaction budget, maintaining
behaviourally diverse populations (novelty search, quality-diversity) yields
higher **held-out** task reward than fixed-objective evolutionary optimization.

H0: no difference in held-out reward between diversity methods and fixed-objective GA.

## Design (fixed)

* **Task:** identical to the pilot (`configs/pilot.json`) — deterministic 10×10
  egocentric foraging world, no lethal hazards in training, 7-D observation.
  The task is **unchanged** so this is a replication, not a re-tune.
* **Budget:** 500,000 environment interactions per method per seed (unchanged).
* **Seeds:** 10 independent RNG seeds (10, 1–10) — up from 5 in the pilot.
* **Train seeds:** [11, 22, 33, 44]; **held-out seeds:** [101, 202, 303, 404].
  Disjoint, enforced by the runner.
* **Methods:** `fixed_objective_ga`, `novelty_search`, `map_elites`, `reinforce`,
  plus `random` and `heuristic` controls.
* **No tuning against held-out seeds.** Held-out seeds are used only for the
  registered analysis below.

## Registered analysis (fixed)

Primary outcome: **held-out mean reward**.

1. **Effect size with uncertainty:** difference in means between each diversity
   method and `fixed_objective_ga`, with a **bootstrap 95% percentile CI**
   (10,000 resamples, fixed RNG seed 20261008) over the per-seed held-out rewards.
2. **Non-parametric test:** two-sided **Mann–Whitney U** on the per-seed held-out
   rewards of each diversity method vs `fixed_objective_ga` (α = 0.05).
   With n = 10 per group this is still low-powered; it is reported as a
   magnitude-and-interval result, not as proof.
3. **Direction:** H1 is *supported in direction* if the point estimate of the
   mean difference is positive for a diversity method AND its bootstrap CI
   excludes 0; it is *falsified* for that method if the CI excludes 0 on the
   negative side; otherwise the result is **inconclusive** and is reported as such.
4. Secondary outcomes (reported, not used to claim H1): transfer zero-shot and
   adapted reward on morphology variants; perturbation robustness; compute cost.

## Multiplicity

Two diversity methods are compared against one baseline. No family-wise
correction is applied; the raw p-values are reported **and** explicitly labelled
uncorrected. A Bonferroni threshold (α/2 = 0.025) is also reported for reference.

## Reporting rules

* Negative, null and inconclusive results are reported with equal prominence.
* The generated report is produced by `scripts/make_report.py` + `scripts/analyze.py`
  directly from the store; no number is hand-entered.
* If the CI is wide, the conclusion is stated as inconclusive rather than spun.
