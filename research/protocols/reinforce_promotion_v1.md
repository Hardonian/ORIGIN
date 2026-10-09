# Protocol — REINFORCE promotion v1: strict-cap held-out control study

**Registered before execution.** This study tests the existing pure-NumPy
REINFORCE implementation after its hidden-layer derivative correction. It does
not use the earlier held-out diagnostic to choose seeds, task parameters, or
hyperparameters.

## Hypothesis and scope

**H-RL.** Under a fixed maximum training-interaction budget on the registered
single-niche grid task, the fixed REINFORCE implementation achieves higher
held-out base-task reward than the random policy control.

This is a promotion study for the RL control, not a comparison against
MAP-Elites or GA. Its only confirmatory endpoint is held-out base-task reward;
all transfer rows are descriptive.

## Fixed task and learner

`configs/reinforce_promotion_v1.json` fixes the 10x10 egocentric random-terrain
environment, train seeds `[11, 22, 33, 44]`, held-out test seeds
`[101, 202, 303, 404]`, and a 500,000-step maximum training budget per
REINFORCE seed. The learner is a 7-24-5 MLP with `episodes_per_update=4`,
`lr=0.01`, `gamma=0.99`, and `entropy_coef=0.02`, exactly matching the prior
versioned control configuration. No tuning is permitted after this document.

Each policy-gradient update reserves the complete rollout batch plus its
held-in evaluator episodes before training. A trial that cannot fit a complete
update stops rather than exceeding the cap. Stored training `interactions` must
be no greater than 500,000; held-out evaluation interactions are separate.

## Design

* **Methods:** confirmatory `reinforce` versus `random`; `heuristic` is a
  descriptive solvability reference only.
* **Method seeds:** `[200 ... 239]` (n = 40), fresh and disjoint from all
  prior single-niche and multi-niche campaigns.
* **Sample size:** n = 40 is fixed before execution for a precision-oriented
  control-promotion decision. No earlier effect estimate is used for sizing.
* **Train/test isolation:** only the four train seeds may occur in RL updates;
  all primary scores use only the four held-out test seeds.

## Registered primary analysis and decision rule

For each method seed \(s\), define

\[
d_s = \operatorname{held\_out\_reward}(\mathrm{reinforce}, s)
      - \operatorname{held\_out\_reward}(\mathrm{random}, s).
\]

1. `scripts/analyze_reinforce.py` must fail closed unless every registered
   REINFORCE and random-control seed has a finite held-out score.
2. Compute a percentile paired-bootstrap 95% interval for `mean(d)` using
   10,000 resamples and RNG seed **20261017**.
3. Report a two-sided Wilcoxon signed-rank test as a concordance check. The
   bootstrap interval is the registered decision rule.
4. H-RL is **supported** if the point estimate is positive and the interval
   excludes zero, **falsified** if negative and the interval excludes zero, and
   otherwise **inconclusive**. A supported result promotes REINFORCE only as a
   reproducible control on this task, not as a general RL claim.

## Reporting

Report all completed and failed trials, actual training interactions, separate
evaluation interactions, the exact configuration hash, and the registered
analysis command. Do not combine this interval with prior diagnostics or
substitute a comparison against another learned method.
