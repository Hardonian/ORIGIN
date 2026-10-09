# H1-ME — Pre-registered strict-cap single-niche replication

Experiment `59427f9116fa` · protocol `paired_power_v4_strict_cap_H1ME` · 40 seeds · budget 500,000 interactions/method/seed.

Analysis fixed in advance at `research\protocols\paired_v4_strict_cap.md`:
paired bootstrap 10,000 resamples (seed 20261016) over the mean of the
per-seed differences, and a two-sided Wilcoxon signed-rank test (α = 0.05). Per the
registration, no other test decides the verdict and it is not switched.

## Descriptive (held-out mean reward per method)

| method | n | mean | sd | min | max |
| --- | --- | --- | --- | --- | --- |
| `random` | 40 | 2.610 | 0.000 | 2.610 | 2.610 |
| `heuristic` | 40 | 4.977 | 0.000 | 4.977 | 4.977 |
| `fixed_objective_ga` | 40 | 2.194 | 1.452 | -0.140 | 4.698 |
| `map_elites` | 40 | 2.873 | 1.195 | 0.360 | 4.977 |

## Held-Out Base Generalization: paired test vs fixed-objective GA

| comparison | mean paired diff | 95% paired bootstrap CI | CI excludes 0? | Wilcoxon p | verdict |
| --- | --- | --- | --- | --- | --- |
| `map_elites` − `fixed_objective_ga` | +0.679 | [+0.112, +1.241] | yes | 0.0381 (W=227.5) | **supported (direction)** |

Paired on 40 method seeds. Uncorrected p-values are shown;
the sole registered comparison does not require a multiplicity adjustment.

### Bounded null (minimum detectable effect)

An inconclusive result is only meaningful with the effect size the design could
have detected. At this n, 80% power, α = 0.05 (two-sided):

* `map_elites`: minimum detectable paired effect = 0.817 (observed |mean diff| = 0.679).

If the CI spans zero, the correct statement is that any true effect is smaller
than the minimum detectable effect — not that no effect exists.

### Secondary (reported, not decisive)

The unpaired Mann–Whitney U on the same data, for comparability with study 1:

* `map_elites`: U=989.5, p=0.0683 (unpaired, secondary).

## Interpretation

* **`map_elites` (base held-out)**: supported (direction). Point estimate +0.679 (95% CI [+0.112, +1.241]).

Reminder of scope: this is a single task family with reactive controllers. A
positive direction is evidence about *this* world, not a general claim, and a
CI spanning 0 is reported as inconclusive rather than as a near-miss.
