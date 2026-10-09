# Protocol — Study v4: strict-cap single-niche replication of H1-ME

**Registered before execution.** This is a fresh replacement for the prior
single-niche studies' compute and adaptation claims. It does not pool, resize,
or otherwise reuse legacy results.

## Hypothesis and scope

**H1-ME.** Under an equal maximum training-interaction budget on the registered
single-niche grid task, MAP-Elites achieves higher held-out base-task reward
than fixed-objective GA.

The sole confirmatory endpoint is held-out base-task reward. Transfer, zero-shot
scores, and adaptation gains are descriptive: they cannot replace the primary
endpoint after results are known.

## Fixed task and budget

`configs/single_niche_strict_cap_replication_v4.json` fixes the 10x10
egocentric random-terrain environment, all optimizer hyperparameters, training
seeds `[11, 22, 33, 44]`, held-out test seeds `[101, 202, 303, 404]`, and a
500,000-step maximum training budget per learned method seed. The adaptation
budget is 50,000 steps and adapts only on training seeds `[11, 22]`; it is
evaluated only on all four held-out test seeds.

Before every population or MAP-Elites batch, the evaluator reserves the full
worst-case episode cost. A learned trial for which a full batch does not fit
stops rather than exceeding 500,000 training steps. `interactions` must be at
most 500,000 for every learned trial; evaluation interactions are recorded
separately and are not included in that budget.

## Design

* **Methods:** confirmatory `map_elites` versus `fixed_objective_ga`; `random`
  and `heuristic` are descriptive controls only.
* **Method seeds:** `[140 ... 179]` (n = 40), disjoint from the prior
  single-niche seeds `[1 ... 60]` and the multi-niche strict-cap seeds
  `[70 ... 133]`. Both learned methods use every method seed.
* **Sample size:** n = 40 is fixed before execution for a precision-oriented
  replication. No legacy effect estimate is used to declare power.
* **Train/test isolation:** test seeds are never used during optimizer training,
  fine-tuning, or hyperparameter selection.

## Registered primary analysis and decision rule

For each method seed \(s\), let

\[
d_s = \operatorname{held\_out\_reward}(\mathrm{map\_elites}, s)
      - \operatorname{held\_out\_reward}(\mathrm{fixed\_objective\_ga}, s).
\]

1. `scripts/analyze.py` must fail closed if any registered learned-method seed
   is missing or non-finite.
2. Calculate a 95% percentile paired-bootstrap interval for `mean(d)` using
   10,000 resamples and RNG seed **20261016**.
3. Report a two-sided Wilcoxon signed-rank test as a concordance check. The
   bootstrap interval is the decision rule.
4. H1-ME is **supported** if the point estimate is positive and the interval
   excludes zero, **falsified** if negative and the interval excludes zero, and
   otherwise **inconclusive**. An inconclusive result reports its observed
   minimum detectable effect; it is not relabelled a trend.

## Reporting

Report every completed and failed trial, actual training interactions, separate
evaluation interactions, the exact configuration hash, and the registered
analysis command. No result from the legacy experiments is combined with this
study's interval or used to switch endpoints.
