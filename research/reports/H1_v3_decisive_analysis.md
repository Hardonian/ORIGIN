> ## Legacy evidence notice — 2026-10-09
>
> This analysis is retained for historical audit only. Its interaction accounting
> predates strict-cap semantics, and any adaptation-gain value produced before
> 2026-10-08 used overlapping adaptation and evaluation seeds. Do not cite it as
> current compute or held-out transfer evidence; see `RESULT_PROVENANCE.md`.

# H1 — Pre-registered analysis (paired design, study v3)

Experiment `8f92870eaeb0` · protocol `paired_power_v3_H1ME` · 40 seeds · budget 500,000 interactions/method/seed.

Analysis fixed in advance at `research/protocols/paired_v3_power.md`:
paired bootstrap 10,000 resamples (seed 20261010) over the mean of the
per-seed differences, and a two-sided Wilcoxon signed-rank test (α = 0.05). Per the
registration, no other test decides the verdict and it is not switched.

## Descriptive (held-out mean reward per method)

| method | n | mean | sd | min | max |
|---|---|---|---|---|---|
| `random` | 40 | 1.785 | 0.595 | 0.610 | 3.119 |
| `heuristic` | 40 | 4.977 | 0.000 | 4.977 | 4.977 |
| `fixed_objective_ga` | 40 | 2.698 | 1.114 | 0.110 | 4.697 |
| `map_elites` | 40 | 2.477 | 1.275 | 0.110 | 4.698 |

## Registered primary: paired test, diversity method vs fixed-objective GA

| comparison | mean paired diff | 95% paired bootstrap CI | CI excludes 0? | Wilcoxon p | verdict |
|---|---|---|---|---|---|
| `map_elites` − `fixed_objective_ga` | -0.221 | [-0.721, +0.262] | no | 0.5377 (W=328.0) | **inconclusive** |

Paired on 40 method seeds. Uncorrected p-values are shown;
a Bonferroni threshold for two comparisons is α/2 = 0.025 (reported, not applied).

### Bounded null (minimum detectable effect)

An inconclusive result is only meaningful with the effect size the design could
have detected. At this n, 80% power, α = 0.05 (two-sided):

* `map_elites`: minimum detectable paired effect = 0.708 (observed |mean diff| = 0.221).

If the CI spans zero, the correct statement is that any true effect is smaller
than the minimum detectable effect — not that no effect exists.

### Secondary (reported, not decisive)

The unpaired Mann–Whitney U on the same data, for comparability with study 1:

* `map_elites`: U=758.5, p=0.6928 (unpaired, secondary).

## Interpretation

* **`map_elites`**: inconclusive. Point estimate -0.221 (95% CI [-0.721, +0.262]).

Reminder of scope: this is a single task family with reactive controllers. A
positive direction is evidence about *this* world, not a general claim, and a
CI spanning 0 is reported as inconclusive rather than as a near-miss.
