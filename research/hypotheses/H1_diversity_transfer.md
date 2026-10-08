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

**Tested across three studies; NOT ESTABLISHED.** Study 1 (independent design) gave
novelty −0.228, CI [−1.43, +1.00]; study v2 (paired design, fresh seeds) gave
novelty +0.331, CI [−0.93, +1.55] and MAP-Elites +0.790, CI [−0.16, +1.65]. Every
registered 95% CI spans zero and the sign is unstable, so the honest verdict is
inconclusive — no diversity advantage is established on this task.
See `../../reports/H1_powered_analysis.md` and `../../reports/H1_paired_v2_analysis.md`.
