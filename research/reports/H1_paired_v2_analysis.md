# H1 — Pre-registered analysis (paired design, study v2)

Experiment `c7363fb00344` · protocol `paired_replication_v2_H1` · 10 seeds · budget 500,000 interactions/method/seed.

Analysis fixed in advance at `research/protocols/paired_v2.md`:
paired bootstrap 10,000 resamples (seed 20261009) over the mean of the
per-seed differences, and a two-sided Wilcoxon signed-rank test (α = 0.05). Per the
registration, no other test decides the verdict and it is not switched.

## Descriptive (held-out mean reward per method)

| method | n | mean | sd | min | max |
|---|---|---|---|---|---|
| `random` | 10 | 1.585 | 0.558 | 0.860 | 2.610 |
| `heuristic` | 10 | 4.977 | 0.000 | 4.977 | 4.977 |
| `fixed_objective_ga` | 10 | 2.395 | 1.437 | 0.110 | 4.698 |
| `novelty_search` | 10 | 2.726 | 1.409 | 0.360 | 4.417 |
| `map_elites` | 10 | 3.185 | 0.878 | 1.360 | 4.140 |
| `reinforce` | 10 | 1.453 | 1.410 | -0.140 | 3.419 |

## Registered primary: paired test, diversity method vs fixed-objective GA

| comparison | mean paired diff | 95% paired bootstrap CI | CI excludes 0? | Wilcoxon p | verdict |
|---|---|---|---|---|---|
| `novelty_search` − `fixed_objective_ga` | +0.331 | [-0.932, +1.549] | no | 0.5566 (W=21.0) | **inconclusive** |
| `map_elites` − `fixed_objective_ga` | +0.790 | [-0.161, +1.645] | no | 0.2031 (W=11.0) | **inconclusive** |

Paired on 10 method seeds. Uncorrected p-values are shown;
a Bonferroni threshold for two comparisons is α/2 = 0.025 (reported, not applied).

### Secondary (reported, not decisive)

The unpaired Mann–Whitney U on the same data, for comparability with study 1:

* `novelty_search`: U=56.0, p=0.6768 (unpaired, secondary).
* `map_elites`: U=64.5, p=0.2853 (unpaired, secondary).

## Interpretation

* **`novelty_search`**: inconclusive. Point estimate +0.331 (95% CI [-0.932, +1.549]).
* **`map_elites`**: inconclusive. Point estimate +0.790 (95% CI [-0.161, +1.645]).

Reminder of scope: this is a single task family with reactive controllers. A
positive direction is evidence about *this* world, not a general claim, and a
CI spanning 0 is reported as inconclusive rather than as a near-miss.
