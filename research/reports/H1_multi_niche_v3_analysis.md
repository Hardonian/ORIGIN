# H1.MN — Pre-registered multi-niche transfer analysis

Experiment `1e8559d6de45` · protocol `multi_niche_transfer_v3_strict_cap_H1MN` · 64 paired method seeds · budget 25,000 interactions/method/seed.

Analysis fixed in advance at `research/protocols/multi_niche_replication_v3.md`. The endpoint is each seed's arithmetic mean of `adapted_mean_reward` over the five registered niche shocks; shocks are **not** independent samples.

## Endpoint completeness

All 64 registered seeds were present and finite for both methods and all five shocks: `niche_payoff_swap`, `niche_toxic_hazard`, `niche_scarcity_shock`, `niche_a_only`, `niche_b_only`.

## Descriptive primary endpoint

| method | n | mean | sd | min | max |
| --- | --- | --- | --- | --- | --- |
| `map_elites` | 64 | -1.940 | 1.080 | -4.577 | +2.021 |
| `fixed_objective_ga` | 64 | -2.359 | 0.900 | -4.307 | -0.162 |

## Registered primary comparison

| comparison | mean paired diff | 95% paired bootstrap CI | CI excludes 0? | Wilcoxon p | verdict |
| --- | --- | --- | --- | --- | --- |
| `map_elites` − `fixed_objective_ga` | +0.418 | [+0.057, +0.778] | yes | 0.0305 (W=668.0) | **supported (direction)** |

Paired bootstrap: 10,000 resamples, fixed RNG seed `20261015`. The confidence interval is the registered decision rule; Wilcoxon is reported as a concordance check.

## Per-shock descriptive values

| shock | MAP-Elites mean | fixed-objective GA mean | paired diff |
| --- | --- | --- | --- |
| `niche_payoff_swap` | -2.243 | -3.076 | +0.834 |
| `niche_toxic_hazard` | -2.715 | -3.108 | +0.393 |
| `niche_scarcity_shock` | -2.524 | -2.418 | -0.106 |
| `niche_a_only` | -1.875 | -2.065 | +0.190 |
| `niche_b_only` | -0.345 | -1.126 | +0.780 |

## Bounded-null context

At n=64, the normal-approximation minimum detectable paired effect at 80% power and α=0.05 (two-sided) is 0.525; observed |mean difference| is 0.418.

A confidence interval spanning zero is reported as inconclusive, not as evidence for equivalence.
