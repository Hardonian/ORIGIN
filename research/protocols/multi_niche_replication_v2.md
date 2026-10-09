# Protocol — H1.MN v2: paired, powered multi-niche transfer replication

> ## Execution correction — 2026-10-09
>
> This document is retained as the original v2 registration. Its execution is
> invalid for confirmatory use: the then-current optimizers could evaluate a
> final complete generation/batch after crossing the 25,000-step cap. See
> `research/reports/H1_multi_niche_v2_analysis.md`. The fresh strict-cap rerun
> is registered at `research/protocols/multi_niche_replication_v3.md`; v2 data
> are not used to decide H1.MN.

**Registered before execution.** This protocol supersedes neither the pilot nor its data. It fixes the transfer endpoint that the pilot described but did not uniquely aggregate, before any v2 trial is started.

## Question and scope

**H1.MN.** Under an equal interaction budget in a dual-resource ecology, MAP-Elites maintains a repertoire that achieves greater held-out transfer performance after a fixed adaptation budget than fixed-objective GA.

The confirmatory scope is deliberately one comparison: `map_elites` versus `fixed_objective_ga`. `random` and `heuristic` are descriptive controls only. No conclusion about another algorithm or a chosen individual shock is confirmatory.

## Fixed task and interventions

The task, optimizer settings, 25,000-training-interaction budget, training seeds `[11, 22, 33, 44]`, held-out evaluation seeds `[101, 202, 303, 404]`, and 5,000-interaction adaptation budget are exactly those in `configs/multi_niche_transfer_replication_v2.json` and the pilot. The five registered shocks are:

1. `niche_payoff_swap`
2. `niche_toxic_hazard`
3. `niche_scarcity_shock`
4. `niche_a_only`
5. `niche_b_only`

Each adapted score is evaluated only on the held-out test seeds. No test seed is used for adaptation.

## Design and power

* **Method seeds:** `[6 … 69]` (n = 64), fresh and disjoint from the pilot's method seeds `[1 … 5]`. These are paired: both algorithms use every method seed and the same fixed train/test environments.
* **Unit of inference:** one method seed. The five shocks are repeated measurements within that unit, not five independent samples.
* **Power basis:** on the pilot's exact prospective aggregate (mean `adapted_mean_reward` over all five shocks), the paired SD was 0.797 and the observed mean difference was −0.298. A normal approximation gives n = 57 for 80% power at α = 0.05 (two-sided) for that magnitude. n = 64 exceeds this and has a pilot-variance minimum detectable effect of 0.279. The pilot's direction does not determine the decision rule.

## Registered primary endpoint and analysis

For every algorithm $a$ and method seed $s$, define

$$T_{a,s} = \frac{1}{5}\sum_{v \in V} \operatorname{adapted\_mean\_reward}(a,s,v),$$

where $V$ is the five shocks listed above. The sole primary paired difference is

$$d_s = T_{\mathrm{map\_elites},s} - T_{\mathrm{fixed\_objective\_ga},s}.$$

1. `scripts/analyze_multi_niche.py` must verify that every registered seed, method, shock, and endpoint is present and finite. Missing or failed values stop the analysis; they are never silently dropped.
2. A percentile paired-bootstrap 95% CI for `mean(d)` uses 10,000 resamples and fixed RNG seed **20261014**.
3. A two-sided Wilcoxon signed-rank statistic is reported as a concordance check, α = 0.05; it does not replace the interval decision rule.
4. **Decision:** H1.MN is supported if the mean paired difference is positive and its 95% paired bootstrap CI excludes zero; it is falsified for this task if the difference is negative and the CI excludes zero; otherwise it is inconclusive.

The script's `zero_shot_mean_reward` and `adaptation_gain` modes, per-shock rows, base-task reward, and all controls are descriptive only for this study. They cannot replace the primary endpoint after results are known.

## Reporting rules

* Report every completed v2 trial and any failure or incomplete endpoint.
* State the per-seed aggregation explicitly; do not pool 64 × 5 shock measurements as independent observations.
* If the CI spans zero, report the observed minimum detectable effect rather than calling the methods equivalent.
* The pilot's base-environment comparison is retained as exploratory context only; it was not the transfer primary specified here.
