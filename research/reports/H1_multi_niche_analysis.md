# H1.MN pilot — Exploratory base-task analysis (corrected)

> ## Correction — 2026-10-09
>
> This file originally labelled a comparison of unperturbed held-out base-task
> reward as the pilot's "registered primary" analysis. That was incorrect: the
> protocol registered ecological-shock transfer, while this script read only
> `test_mean_reward`. The pilot protocol also did not define one exact aggregate
> across its five shocks, so selecting one after seeing the data would not repair
> the confirmatory claim. The base-task comparison below is retained as an
> **exploratory descriptive result only**; it neither supports nor falsifies
> H1.MN's transfer claim.
>
> `research/protocols/multi_niche_replication_v2.md` now fixes a single
> per-seed transfer endpoint before the fresh v2 campaign, and
> `scripts/analyze_multi_niche.py` refuses missing seeds, shocks, or endpoints.

Experiment `f8f4c952a5c3` · protocol `multi_niche_pilot_v1` · 5 seeds · budget 25,000 interactions/method/seed.

This post-run base-task audit uses a paired bootstrap (10,000 resamples, seed
20261011) over the per-seed differences and a two-sided Wilcoxon signed-rank
test (α = 0.05). Those calculations are reproducible, but they are not the
pilot's registered transfer primary.

## Descriptive (held-out mean reward per method)

| method | n | mean | sd | min | max |
| --- | --- | --- | --- | --- | --- |
| `random` | 5 | 3.513 | 0.000 | 3.513 | 3.513 |
| `heuristic` | 5 | 70.175 | 0.000 | 70.175 | 70.175 |
| `fixed_objective_ga` | 5 | -2.010 | 2.348 | -5.087 | 0.050 |
| `map_elites` | 5 | -1.973 | 1.616 | -3.655 | 0.050 |

## Exploratory base-task contrast: diversity method vs fixed-objective GA

| comparison | mean paired diff | 95% paired bootstrap CI | CI excludes 0? | Wilcoxon p | descriptive status |
| --- | --- | --- | --- | --- | --- |
| `map_elites` − `fixed_objective_ga` | +0.036 | [-2.202, +2.275] | no | 1.0000 (W=5.0) | **inconclusive (exploratory)** |

Paired on 5 method seeds. There is only one diversity method in this campaign;
the p-value is descriptive and no multiple-comparison threshold is applied.

### Sensitivity context (minimum detectable effect)

At this n, the base-task contrast had the following normal-approximation
sensitivity at 80% power, α = 0.05 (two-sided):

* `map_elites`: minimum detectable paired effect = 3.538 (observed |mean diff| = 0.036).

This is not a bound on the transfer endpoint, and a CI spanning zero does not
establish equivalence.

### Additional descriptive check

The unpaired Mann–Whitney U on the same data, for comparability with study 1:

* `map_elites`: U=13.0, p=1.0000 (unpaired, secondary).

## Interpretation and scope

* **`map_elites` on the unperturbed base task**: inconclusive. Point estimate
  +0.036 (95% CI [-2.202, +2.275]).

The ecological-shock transfer result remains unresolved. It will be measured by
the pre-specified aggregate in the fresh, paired v2 replication rather than
retroactively selecting an aggregate from this pilot.
