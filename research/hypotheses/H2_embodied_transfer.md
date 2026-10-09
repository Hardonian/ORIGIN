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
but **the outcome was void and this hypothesis was untested**: the instrument was
found to be physically broken (the "10-link centipede" was a clump of overlapping
capsules, not a chain), the fall metric was wrap-broken, and the adaptation gains
were measured in-sample. All embodied results were retracted — see the correction
at the top of `research/reports/ORIGIN_M4_Embodied_Transfer_Report.md`.

## Outcome — Confirmatory Study v3 on Calibrated Physics (2026-10-09)

Pre-registered under `research/protocols/embodied_transfer_v3.md` and executed
across 32 cores on remote node `epyc` (experiment `1bdb4b622748`, 25/25 trials, 0 failed)
after passing physical calibration (`runs/embodied-calibration.json`, $+1.007\text{ m} \ge 0.050\text{ m}$):

1. **Prediction 1 Confirmed:** Learned methods strictly dominated controls on held-out test reward
   (MAP-Elites $14.265$, Novelty Search $13.589$, GA $11.717$ vs Random $1.247$, Scripted Gait $-17.438$).
   Fall rate was $0.00$ across all evaluated methods.
2. **Prediction 2 (Directionally consistent, not statistically resolved):** MAP-Elites led GA in point estimate
   (+2.548 paired difference, highest net distance $4.516\text{ m}$ vs $4.111\text{ m}$, and was the only method
   with target arrival successes at 20%), with a 95% paired bootstrap CI of $[-2.480, +9.272]$ and Wilcoxon $p=0.4375$.
   At $n=5$, MDE was $9.294$; per pre-registered decision rules, this difference is bounded and not statistically resolved.
3. **Prediction 3 Confirmed:** Zero-shot transfer to distinct bodies was severely penalized (pooled mean dropped to $-1.748$,
   with non-source bodies averaging $-4.95$). Environmental perturbations were tolerated far better (mean $+3.36$),
   confirming that morphological coupling is the primary constraint.
4. **Prediction 4 Confirmed:** Adaptation with an 8,000-step budget on disjoint training seeds recovered positive performance
   across every single body plan (pooled mean rose to $+5.814$, gains of $+6.66$ to $+9.50$).

Full report: `research/reports/ORIGIN_M4_Embodied_Transfer_Report_v3.md`.
