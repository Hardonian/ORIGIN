# H2 — Diversity and Transfer Across Physical Bodies

**Status:** pre-registered before the embodied campaign was run.
**Registered commit:** `ccecf9f` (campaign `aa1175d6c5aa` ran from this tree).

## Hypothesis

Under an equivalent interaction budget, a **quality-diversity** search
(MAP-Elites over behavioural descriptors) produces controllers that transfer to
unfamiliar **physical morphologies** at least as well as a fixed-objective
evolutionary search (GA), and adapts faster when given a fixed budget on the new
body.

## Design

* **Simulator.** PyBullet, planar articulated chains, 8 physics substeps per
  control step. Fixed control interface: 7 observations, 5 motor primitives.
* **Source body.** `centipede`, 10 links, episode 6 s, target 3 m along +x.
* **Budget.** 40,000 environment interactions per algorithm trial; adaptation
  budget 8,000 per transfer body.
* **Methods.** `fixed_objective_ga`, `map_elites`, `novelty_search`, plus
  `random` and `scripted_gait` controls.
* **Seeds.** 3 training seeds; evaluation on 3 disjoint held-out seeds.
* **Primary analysis.** Paired bootstrap CI (`map_elites - fixed_objective_ga`)
  on held-out test reward, with Wilcoxon signed-rank; report the minimum
  detectable effect and declare the result unresolved if the CI spans zero.
* **Secondary measurements.** Zero-shot vs adapted transfer per body plan;
  zero-shot under environmental perturbations.

## Pre-registered predictions

1. Learned methods beat both controls on held-out test reward.
2. MAP-Elites ≥ GA on held-out test reward (paired difference ≥ 0).
3. Zero-shot transfer to a new body is **worse** than performance on the source
   body — a controller is partly fitted to its own body.
4. Adaptation under a fixed budget improves performance on the new body.

## Outcome — VOID (amended 2026-10-08)

The campaign ran and predictions 1, 3 and 4 appeared to hold in point estimate,
but **the outcome is void and this hypothesis is untested**: the instrument was
found to be physically broken (the "10-link centipede" was a clump of overlapping
capsules, not a chain), the fall metric was wrap-broken, and the adaptation gains
were measured in-sample. All embodied results are retracted — see the correction
at the top of `research/reports/ORIGIN_M4_Embodied_Transfer_Report.md`. H2
remains pre-registered and **must be run again on a working morphology** before
any outcome is claimed; the pre-registration above stands as written.

Recorded during the failed run (post-hoc, not pre-registered): environmental
perturbations were tolerated far better than morphological ones, and the reward
as originally specified could be earned by travelling then falling — the task
has since been revised (see `docs/EXPERIMENT_PROTOCOL.md` §9) before any re-run.
