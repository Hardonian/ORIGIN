# H1.MN v2 — Invalidated over-budget execution audit

> ## Retraction — 2026-10-09
>
> This execution does **not** provide confirmatory evidence for H1.MN. The former
> optimizer loop allowed a final full generation or MAP-Elites batch after the
> nominal 25,000-step cap. Across v2, fixed-objective GA consumed 34,452–34,560
> training steps and MAP-Elites consumed 28,603–28,800. The registered equal-cap
> condition was therefore violated. The numerical audit is retained below for
> debugging only; its verdict must not be cited. The evaluator now reserves full
> batches before evaluation, and `multi_niche_replication_v3.md` registers fresh
> method seeds for a strict-cap rerun.

Experiment `5058bcacd3de` · protocol `multi_niche_transfer_v2_H1MN` · 64 paired method seeds · budget 25,000 interactions/method/seed.

Analysis fixed in advance at `research/protocols/multi_niche_replication_v2.md`. The endpoint is each seed's arithmetic mean of `adapted_mean_reward` over the five registered niche shocks; shocks are **not** independent samples.

## Endpoint completeness

All 64 registered seeds were present and finite for both methods and all five shocks: `niche_payoff_swap`, `niche_toxic_hazard`, `niche_scarcity_shock`, `niche_a_only`, `niche_b_only`.

## Descriptive primary endpoint

| method | n | mean | sd | min | max |
| --- | --- | --- | --- | --- | --- |
| `map_elites` | 64 | -1.838 | 1.125 | -4.440 | +0.948 |
| `fixed_objective_ga` | 64 | -2.498 | 1.110 | -5.040 | +1.033 |

## Registered primary comparison

| comparison | mean paired diff | 95% paired bootstrap CI | CI excludes 0? | Wilcoxon p | verdict |
| --- | --- | --- | --- | --- | --- |
| `map_elites` − `fixed_objective_ga` | +0.660 | [+0.298, +1.036] | yes | 0.0019 (W=514.0) | **invalid — over budget** |

Paired bootstrap: 10,000 resamples, fixed RNG seed `20261014`. The confidence interval is the registered decision rule; Wilcoxon is reported as a concordance check.

## Per-shock descriptive values

| shock | MAP-Elites mean | fixed-objective GA mean | paired diff |
| --- | --- | --- | --- |
| `niche_payoff_swap` | -2.496 | -2.874 | +0.379 |
| `niche_toxic_hazard` | -2.496 | -3.232 | +0.736 |
| `niche_scarcity_shock` | -2.287 | -2.863 | +0.576 |
| `niche_a_only` | -1.705 | -2.249 | +0.544 |
| `niche_b_only` | -0.205 | -1.271 | +1.066 |

## Bounded-null context

At n=64, the normal-approximation minimum detectable paired effect at 80% power and α=0.05 (two-sided) is 0.528; observed |mean difference| is 0.660.

This audit is invalid because its training-cap condition failed; no inferential conclusion follows.
