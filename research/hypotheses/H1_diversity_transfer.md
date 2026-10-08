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

**Tested and INCONCLUSIVE at n=10.** The pre-registered powered replication is in
`../../reports/H1_powered_analysis.md`; results and non-replication of the 5-seed
pilot are discussed in `../../reports/ORIGIN_Initial_Research_Report.md`.
