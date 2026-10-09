# Protocol — H1.MN v3: strict-budget, paired multi-niche transfer replication

**Registered before execution.** This is a fresh replacement for v2, whose execution is invalid for confirmatory use because the former optimizer loop permitted a final full generation or batch to exceed the configured training-step cap. v2 values are retained as an implementation audit only and are not used to decide this study or size it.

## Hypothesis and fixed task

**H1.MN.** Under an equal maximum training-interaction budget in this dual-resource ecology, MAP-Elites achieves greater held-out transfer performance after a fixed adaptation budget than fixed-objective GA.

`configs/multi_niche_transfer_replication_v3.json` fixes the 10×10 dual-resource task, optimizer settings, 25,000-step training cap, training seeds `[11, 22, 33, 44]`, held-out test seeds `[101, 202, 303, 404]`, and 5,000-step adaptation cap. The five fixed ecological shocks are `niche_payoff_swap`, `niche_toxic_hazard`, `niche_scarcity_shock`, `niche_a_only`, and `niche_b_only`.

The runner now reserves each complete population/batch evaluation against its maximum episode horizon before starting it. A learned trial that would exceed 25,000 training environment steps is refused rather than partially or over-budget evaluated. Actual steps may be lower because episodes can end naturally; the stored `interactions` field must be ≤25,000 for every learned trial.

## Design

* **Methods:** confirmatory `map_elites` versus `fixed_objective_ga`; `random` and `heuristic` are descriptive controls only.
* **Method seeds:** `[70 … 133]` (n = 64), fresh and disjoint from the pilot `[1 … 5]` and invalid v2 execution `[6 … 69]`. Both learned methods use each method seed.
* **Unit of inference:** one seeded training run. The five shocks are repeated measurements within that unit, never independent observations.
* **Adaptation isolation:** each adapted score is trained only on `[11, 22]` and evaluated only on `[101, 202, 303, 404]`.

The sample size is fixed before this run as a precision-oriented replication. Its observed minimum detectable paired effect will be reported; no invalid prior effect estimate is used as a power justification.

## Registered primary endpoint and decision rule

For algorithm $a$ and method seed $s$, define

$$T_{a,s} = \frac{1}{5}\sum_{v \in V} \operatorname{adapted\_mean\_reward}(a,s,v),$$

where $V$ is the five shocks above. The sole confirmatory contrast is

$$d_s = T_{\mathrm{map\_elites},s} - T_{\mathrm{fixed\_objective\_ga},s}.$$

1. `scripts/analyze_multi_niche.py` must fail closed unless every registered method seed has finite `adapted_mean_reward` for every registered shock.
2. Calculate a percentile paired-bootstrap 95% CI for `mean(d)` with 10,000 resamples and fixed RNG seed **20261015**.
3. Report a two-sided Wilcoxon signed-rank statistic as a concordance check (α = 0.05). The CI is the registered decision rule.
4. H1.MN is **supported** for this task if the point estimate is positive and its paired CI excludes zero; **falsified** for this task if negative and the CI excludes zero; otherwise **inconclusive**.

Base-task reward, zero-shot transfer, adaptation gain, individual shocks, and controls are descriptive only. They cannot replace this endpoint after results are known.

## Reporting

Report every trial's actual interaction count and any failed trial. Do not pool 64 × 5 shock values as independent observations. A confidence interval spanning zero is inconclusive rather than evidence of equivalence.
