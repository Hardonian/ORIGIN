> ## Archival evidence notice — 2026-10-09
>
> This pilot analysis predates strict batch reservation and a uniquely fixed
> ecological-shock aggregation. Its adaptation-gain values also predate the
> held-out adaptation correction. It is retained as an instrumentation record,
> not H1.MN evidence; use `H1_multi_niche_v3_analysis.md` and
> `RESULT_PROVENANCE.md` for the current citation rule.

# H1.MN — Pre-registered analysis (multi-niche ecological transfer)

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

## Held-Out Base Generalization: paired test vs fixed-objective GA

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

## Registered Primary: Ecological Shock Transfer (H1.MN Decision Rule)

Per `research/protocols/multi_niche_pilot.md`, the primary transfer criterion evaluates
paired differences across the 5 ecological shock variants:
$$d_s = \text{transfer\_reward}(\text{diversity}, s) - \text{transfer\_reward}(\text{fixed\_objective\_ga}, s)$$
Registered niche variants: `niche_payoff_swap`, `niche_toxic_hazard`, `niche_scarcity_shock`, `niche_a_only`, `niche_b_only`.

| comparison | metric | mean paired diff | 95% paired bootstrap CI | CI excludes 0? | Wilcoxon p | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| `map_elites` − `fixed_objective_ga` | aggregate zero-shot | +0.120 | [-1.462, +1.727] | no | 1.0000 (W=5.0) | **inconclusive** |
| `map_elites` − `fixed_objective_ga` | aggregate adapted | -0.298 | [-0.863, +0.365] | no | 0.6250 (W=3.0) | **inconclusive** |
| `map_elites` − `fixed_objective_ga` | aggregate adaptation gain | -0.418 | [-1.639, +0.803] | no | 0.6250 (W=3.0) | **inconclusive** |

### Bounded null for aggregate niche transfer

* `map_elites`: zero-shot minimum detectable paired effect = 2.605 (observed |mean diff| = 0.120).

### Per-Variant Ecological Shock Breakdown

| variant | GA zero | ME zero | zero diff [95% CI] | GA adapt | ME adapt | adapt diff [95% CI] | GA gain | ME gain | gain diff [95% CI] |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `niche_payoff_swap` | -1.86 | -2.50 | -0.64 [-2.67, +1.22] | -2.14 | -2.25 | -0.11 [-1.31, +1.12] | -0.28 | 0.25 | +0.52 [-1.23, +2.49] |
| `niche_toxic_hazard` | -2.33 | -1.94 | +0.39 [-2.14, +2.92] | -2.61 | -3.71 | -1.10 [-2.49, +0.11] | -0.27 | -1.77 | -1.49 [-3.35, -0.02] |
| `niche_scarcity_shock` | -1.96 | -1.75 | +0.21 [-1.25, +1.86] | -1.67 | -1.60 | +0.07 [-0.93, +0.89] | 0.29 | 0.15 | -0.14 [-1.12, +0.82] |
| `niche_a_only` | -2.35 | -2.64 | -0.29 [-1.13, +0.60] | -2.77 | -0.94 | +1.82 [+0.30, +3.92] | -0.42 | 1.69 | +2.11 [+0.79, +3.57] |
| `niche_b_only` | -2.87 | -1.94 | +0.92 [-0.58, +2.87] | 0.53 | -1.64 | -2.17 [-4.58, +0.29] | 3.40 | 0.30 | -3.10 [-6.75, +0.06] |

## Interpretation

* **`map_elites` (base held-out)**: inconclusive. Point estimate +0.036 (95% CI [-2.202, +2.275]).
* **`map_elites` (niche shock zero_shot)**: inconclusive.
* **`map_elites` (niche shock adapted)**: inconclusive.
* **`map_elites` (niche shock gain)**: inconclusive.

Reminder of scope: this is a single task family with reactive controllers. A
positive direction is evidence about *this* world, not a general claim, and a
CI spanning 0 is reported as inconclusive rather than as a near-miss.
