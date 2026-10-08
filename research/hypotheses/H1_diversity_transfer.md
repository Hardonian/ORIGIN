# H1 — Behavioural diversity improves transfer to unseen environments and morphology

## Statement

Under an equivalent environment-interaction budget, maintaining behaviourally
diverse agent populations (novelty search / quality-diversity) improves adaptation
to unseen evaluation environments and to changed morphology relative to
fixed-objective evolutionary optimization.

## Operationalisation

* **Independent variable**: algorithm family
  (`fixed_objective_ga` vs `novelty_search` vs `map_elites`, plus `reinforce`,
  `random`, `heuristic` controls).
* **Dependent variables**: held-out mean reward; zero-shot transfer reward on
  morphology and perturbation variants; adaptation gain; descriptor spread.
* **Controls**: equal interaction budget; disjoint train/test seeds; multiple
  independent RNG seeds; random and scripted baselines.

## Falsification

No improvement (within reported dispersion) of diversity methods over
fixed-objective evolution on held-out and transfer metrics.

## Dependencies / assumptions

* The environment is deterministic and seed-controlled.
* A reactive controller is an adequate policy class for the pilot task.
* Transfer variants are genuinely distinct (verified by config hashes).

## Status

**NOT ESTABLISHED across four studies; the null is BOUNDED.**

Study v3 is decisive for the feasible comparison. It was power-sized before running
(n=40, from a power analysis on study v2 giving a requirement of 31.5) and scoped to
MAP-Elites vs fixed-objective GA because the same analysis showed `novelty_search`
would need n ≈ 321. At n=40 the design could detect a paired effect of ≥ 0.708 at
80% power; the observed paired difference was **−0.221** (95% CI [−0.72, +0.26]).
The v2 hint of +0.790 did not replicate.

Bounded conclusion: on this task **any MAP-Elites advantage is smaller than ≈0.71
reward units**, and no advantage for novelty search is claimed in either direction.
See `../../reports/H1_v3_decisive_analysis.md`.
