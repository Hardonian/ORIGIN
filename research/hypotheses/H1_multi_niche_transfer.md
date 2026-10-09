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
  - Held-out base environment seeds (`test_seeds`).
  - Transfer variants (`niche_payoff_swap`, `niche_toxic_hazard`, `niche_scarcity_shock`, `niche_a_only`, `niche_b_only`).
* **Dependent variables**:
  - Held-out base test reward.
  - Zero-shot transfer reward across niche variants.
  - Adapted transfer reward and adaptation gain ($\Delta = \text{adapted} - \text{zero\_shot}$).
* **Controls**: Equal interaction budget (25,000 interactions/seed); identical training environments (`train_seeds = [11, 22, 33, 44]`); paired random seeds (`[1, 2, 3, 4, 5]`).

## Falsification Criterion

H1.MN is falsified if `map_elites` achieves equal or lower transfer reward than `fixed_objective_ga` across the pre-registered transfer shocks, or if the paired bootstrap 95% confidence interval spans zero in favor of no advantage.
