# H1 — Pre-registered analysis (powered replication)

Experiment `d0ef7208a010` · protocol `powered_replication_H1` · 10 seeds · budget 500,000 interactions/method/seed.

Analysis fixed in advance at `research/protocols/powered_replication.md`:
bootstrap 10,000 resamples (seed 20261008) and a two-sided
Mann–Whitney U (α = 0.05). No other test is run and the conclusion is not switched.

## Descriptive (held-out mean reward per method)

| method | n | mean | sd | min | max |
|---|---|---|---|---|---|
| `random` | 10 | 2.085 | 0.322 | 1.360 | 2.360 |
| `heuristic` | 10 | 4.977 | 0.000 | 4.977 | 4.977 |
| `fixed_objective_ga` | 10 | 2.554 | 1.335 | 0.360 | 3.699 |
| `novelty_search` | 10 | 2.326 | 1.557 | 0.360 | 4.977 |
| `map_elites` | 10 | 2.516 | 0.961 | 0.610 | 3.699 |
| `reinforce` | 10 | 0.769 | 1.091 | -0.140 | 2.917 |

## Registered test: diversity method vs fixed-objective GA

| comparison | mean diff | 95% bootstrap CI | CI excludes 0? | Mann–Whitney U p | verdict |
|---|---|---|---|---|---|
| `novelty_search` − `fixed_objective_ga` | -0.228 | [-1.427, +0.998] | no | 0.5423 (U=41.5) | **inconclusive** |
| `map_elites` − `fixed_objective_ga` | -0.038 | [-0.972, +0.965] | no | 0.6219 (U=43.0) | **inconclusive** |

Uncorrected p-values are shown. For reference, a Bonferroni threshold for two
comparisons is α/2 = 0.025. No correction is applied to the verdict.

## Interpretation

* **`novelty_search`**: inconclusive. Point estimate -0.228 (95% CI [-1.427, +0.998]).
* **`map_elites`**: inconclusive. Point estimate -0.038 (95% CI [-0.972, +0.965]).

Reminder of scope: this is a single task family with reactive controllers. A
positive direction is evidence about *this* world, not a general claim, and a
CI spanning 0 is reported as inconclusive rather than as a near-miss.
