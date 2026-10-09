# Protocol — Multi-Niche Transfer Pilot (Pre-Registered)

**Registered before execution.** Following the bounded null in single-resource foraging (Study v3), this prospective protocol establishes the first empirical test of evolutionary diversity on multi-niche ecological transfer.

## Task & Environment Parameters

* **Environment configuration**: `configs/multi_niche_transfer.json`
  - Grid: 10×10, `terrain: "zones"`
  - Resource A: 4 items (reward 1.0, energy 20.0, Zone A rows < 5)
  - Resource B: 4 items (reward 2.5, energy 15.0, Zone B rows >= 5)
  - Hazards: 2 items (penalty 0.5, energy drain 10.0)
  - Observation mode: `multi_niche` (7-D egocentric vector)
  - Max steps: 120
* **Budget**: 25,000 interactions per method seed.
* **Seeds**: Paired method seeds `[1, 2, 3, 4, 5]`.
* **Training environments**: `train_seeds = [11, 22, 33, 44]`.
* **Held-out test environments**: `test_seeds = [101, 202, 303, 404]`.
* **Adaptation budget**: 5,000 interactions on training seeds `[11, 22]`, measured strictly on held-out `test_seeds`.

## Comparison Methods

1. `random`: Uniform action selection (null control).
2. `heuristic`: Multi-target BFS foraging heuristic (upper reference baseline).
3. `fixed_objective_ga`: Single-objective evolutionary optimization on task return.
4. `map_elites`: Quality-Diversity archiving over $(collected\_a, collected\_b)$ specializations.

## Registered Transfer Variants

Transfer evaluation is executed against 5 distinct ecological perturbations:
1. `niche_payoff_swap`: Resource A pays 2.5/15.0 energy, Resource B pays 1.0/20.0 energy (inverts the payoff landscape).
2. `niche_toxic_hazard`: Resource B is replaced entirely with hazards (penalizing over-reliance on high-reward items).
3. `niche_scarcity_shock`: Resource counts reduced to 1 each (extreme resource scarcity).
4. `niche_a_only`: Resource B removed entirely (tests Resource A specialist transfer).
5. `niche_b_only`: Resource A removed entirely (tests Resource B specialist transfer).

## Primary Analysis & Decision Rules

1. **Paired Differences**: For each seed $s \in \{1..5\}$:
   $$d_s = \text{transfer\_reward}(\text{map\_elites}, s) - \text{transfer\_reward}(\text{fixed\_objective\_ga}, s)$$
2. **Paired Bootstrap 95% Percentile CI**: 10,000 resamples over the paired differences, fixed RNG seed **20261011**.
3. **Decision Criteria**:
   - **Supported**: If the point estimate is positive and the 95% paired bootstrap CI excludes 0 across the aggregate niche transfer variants.
   - **Falsified**: If the point estimate is negative and the 95% CI excludes 0.
   - **Inconclusive**: If the 95% CI spans 0.
