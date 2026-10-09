# H1.MN — Quality-Diversity Outperforms Fixed-Objective Evolution Under Multi-Niche Ecological Shocks

## Statement

In environments structured into distinct resource niches (Resource A sustenance vs. Resource B high-payoff items partitioned across biomes), maintaining a Quality-Diversity archive over niche specializations (`map_elites` archiving along $(collected\_a, collected\_b)$) produces policy repertoires that transfer and adapt more effectively to environmental shocks (payoff inversion, niche toxicity, and scarcity shocks) than single-objective evolutionary optimization (`fixed_objective_ga`).

## Theoretical Motivation

Prior studies in ORIGIN on single-resource homogeneous foraging (Studies 1, v2, v3) established a bounded null: when an environment contains only one resource type, maximizing fitness selects for the singular dominant foraging gradient, leaving no functional role for behavioral diversity.

In an ecology with multiple competing resource types:

1. `fixed_objective_ga` overfits to the single highest-return foraging strategy (or a single fixed compromise).
2. `map_elites` explicitly populates cells across the 2D behavioral niche spectrum: pure Resource A foragers, pure Resource B foragers, and balanced dual-resource foragers.
3. When the environment undergoes a sudden structural shift (e.g., Payoff Swap where Resource A and B rewards swap, or Toxic Hazard where Resource B becomes hazardous), single-objective GA experiences catastrophic collapse, whereas the Quality-Diversity archive contains pre-adapted specialists that transfer zero-shot or adapt with minimal fine-tuning.

## Operationalisation

* **Independent variable**: evolutionary algorithm (`map_elites` vs `fixed_objective_ga`, with `random` and `heuristic` baselines).
* **Environment**: 10×10 Grid World with dual resource biomes (`zones`), egocentric 7-D multi-niche sensing vector (`[en, a_dr, a_dc, a_dist, b_dr, b_dc, b_dist]`).
* **Evaluation Scenarios**:
  * Held-out base environment seeds (`test_seeds`).
  * Transfer variants (`niche_payoff_swap`, `niche_toxic_hazard`, `niche_scarcity_shock`, `niche_a_only`, `niche_b_only`).
* **Dependent variables**:
  * Held-out base test reward.
  * Zero-shot transfer reward across niche variants.
  * Adapted transfer reward and adaptation gain ($\Delta = \text{adapted} - \text{zero\_shot}$).
* **Controls**: Equal interaction budget; identical training environments;
  paired method seeds. The five-seed values were the original pilot; the
  strict-cap replication's fixed values are in
  `research/protocols/multi_niche_replication_v3.md`.

## Falsification Criterion

H1.MN is falsified for its registered task if the paired effect is negative and
the paired bootstrap 95% confidence interval excludes zero. An interval spanning
zero is inconclusive, not evidence of equivalence.

## Current registered result

The historical five-seed values above describe the original pilot design only.
The authoritative strict-cap replication is
`research/protocols/multi_niche_replication_v3.md`: 64 paired method seeds,
25,000 training interactions per learned-method seed, and one primary endpoint
per seed (mean adapted held-out reward over the five fixed shocks). MAP-Elites
minus GA was +0.418 with 95% paired CI [+0.057, +0.778] and Wilcoxon p=0.0305.
It supports H1.MN for that registered multi-niche endpoint, not a general claim
about all task families. See `research/reports/RESULT_PROVENANCE.md`.
