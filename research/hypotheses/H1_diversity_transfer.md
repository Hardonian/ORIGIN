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

**Task-specific evidence; no universal diversity claim.**

The earlier single-niche v3 study remains a legacy bounded-null observation: it
was power-sized at n=40 and found MAP-Elites − GA = −0.221 (95% CI [−0.72,
+0.26]), so it did not replicate the preceding v2 hint. It does not invalidate
or supersede later strict-cap registrations with a different fixed endpoint and
accounting rule.

The authoritative current results are separated in
`research/reports/RESULT_PROVENANCE.md`:

* **Single-niche strict-cap v4:** MAP-Elites − GA = +0.679, 95% paired CI
  [+0.112, +1.241], n=40; supported for that registered held-out base-task
  endpoint only.
* **Multi-niche strict-cap v3:** MAP-Elites − GA = +0.418, 95% paired CI
  [+0.057, +0.778], n=64, on the registered aggregate adaptation-under-shock
  endpoint; supported for that task only.
* **Embodied H2 v3:** calibrated locomotion, morphology cost, and adaptation
  recovery were measured, but the n=5 MAP-Elites-versus-GA primary comparison
  is statistically inconclusive.

No result establishes an advantage for novelty search generally, or licenses a
claim beyond the registered task, body, endpoint, and budget.
