# Protocol — Study v2: paired-design replication of H1 (pre-registered)

**Registered before the run.** Study 1 (`powered_replication.md`) used an *unpaired*
test and, with n=10, produced CIs spanning zero. Study 1's registration stated that
no other test would be run on its data, and that is honoured — **study 1 is not
re-analysed**. This is a new, prospective study with a different design and
**fresh seeds**.

## Motivation

All methods are trained on the *same* fixed training environments
(`train_seeds = [11, 22, 33, 44]`); only the method's internal RNG differs. The
environment variation between seeds is therefore zero, and the correct efficient
design is **paired by method seed** (common random numbers), not independent
sampling. An unpaired test discards that structure, which is the most likely reason
study 1's intervals were wide.

## Hypothesis

**H1** (unchanged). Under an equal interaction budget, behaviourally diverse
populations (novelty search, quality-diversity) yield higher held-out reward than
fixed-objective evolutionary optimization.

H0: the mean *paired* difference in held-out reward is zero.

## Design (fixed)

* **Task and budget:** identical to the pilot and study 1 (10×10 egocentric
  foraging, 500,000 interactions/method/seed). No re-tuning.
* **Seeds:** `[11, 12, 13, 14, 15, 16, 17, 18, 19, 20]` — **disjoint from study 1**
  (which used 1–10), so no seed is reused and the analysis is prospective.
* **Methods:** `fixed_objective_ga`, `novelty_search`, `map_elites`, `reinforce`,
  plus `random` and `heuristic` controls.
* **Held-out evaluation:** `test_seeds = [101, 202, 303, 404]`, never used for tuning.

## Registered primary analysis (fixed)

For each diversity method and each seed `s`:

    d_s = held_out_reward(method, s) - held_out_reward(fixed_objective_ga, s)

1. **Paired bootstrap 95% percentile CI** on `mean(d)`: resample the **paired
   differences** (not the groups independently), 10,000 resamples, fixed RNG seed
   **20261009** (distinct from study 1's seed, so the two analyses are independent).
2. **Wilcoxon signed-rank test**, two-sided, α = 0.05.
3. **Decision rule (identical in spirit to study 1):** H1 is *supported in
   direction* for a method if the point estimate is positive **and** the paired CI
   excludes 0; *falsified* for that method if the CI excludes 0 on the negative
   side; otherwise **inconclusive**.

## Secondary (reported, not decisive)

* The unpaired Mann–Whitney U and unpaired bootstrap CI, for direct comparability
  with study 1. Reported as secondary only; the verdict comes from the paired
  primary.

## Reporting rules

* Negative, null and inconclusive outcomes are reported with equal prominence.
* All numbers are produced by `scripts/analyze.py --design paired` from the store.
* If the paired CI also spans zero, the conclusion is stated as inconclusive and
  the quest for a task where diversity can express an advantage becomes the next
  study — it is not spun as a near-miss.
