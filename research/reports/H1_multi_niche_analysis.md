# H1 — Pre-registered analysis (paired design, study v2)

Experiment `f8f4c952a5c3` · protocol `multi_niche_pilot_v1` · 5 seeds · budget 25,000 interactions/method/seed.

Analysis fixed in advance at `research/protocols/multi_niche_pilot.md`:
paired bootstrap 10,000 resamples (seed 20261011) over the mean of the
per-seed differences, and a two-sided Wilcoxon signed-rank test (α = 0.05). Per the
registration, no other test decides the verdict and it is not switched.

## Descriptive (held-out mean reward per method)

| method | n | mean | sd | min | max |
| --- | --- | --- | --- | --- | --- |
| `random` | 5 | 3.513 | 0.000 | 3.513 | 3.513 |
| `heuristic` | 5 | 70.175 | 0.000 | 70.175 | 70.175 |
| `fixed_objective_ga` | 5 | -2.010 | 2.348 | -5.087 | 0.050 |
| `map_elites` | 5 | -1.973 | 1.616 | -3.655 | 0.050 |

## Registered primary: paired test, diversity method vs fixed-objective GA

| comparison | mean paired diff | 95% paired bootstrap CI | CI excludes 0? | Wilcoxon p | verdict |
| --- | --- | --- | --- | --- | --- |
| `map_elites` − `fixed_objective_ga` | +0.036 | [-2.202, +2.275] | no | 1.0000 (W=5.0) | **inconclusive** |

Paired on 5 method seeds. Uncorrected p-values are shown;
a Bonferroni threshold for two comparisons is α/2 = 0.025 (reported, not applied).

### Bounded null (minimum detectable effect)

An inconclusive result is only meaningful with the effect size the design could
have detected. At this n, 80% power, α = 0.05 (two-sided):

* `map_elites`: minimum detectable paired effect = 3.538 (observed |mean diff| = 0.036).

If the CI spans zero, the correct statement is that any true effect is smaller
than the minimum detectable effect — not that no effect exists.

### Secondary (reported, not decisive)

The unpaired Mann–Whitney U on the same data, for comparability with study 1:

* `map_elites`: U=13.0, p=1.0000 (unpaired, secondary).

## Interpretation

* **`map_elites`**: inconclusive. Point estimate +0.036 (95% CI [-2.202, +2.275]).

Reminder of scope: this is a single task family with reactive controllers. A
positive direction is evidence about *this* world, not a general claim, and a
CI spanning 0 is reported as inconclusive rather than as a near-miss.
