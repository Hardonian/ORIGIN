# Experiment Protocol

This document defines how ORIGIN experiments are designed, executed and reported,
so that results are comparable and falsifiable.

## 1. Hypothesis first

Every experiment names a falsifiable hypothesis (see `research/hypotheses/`). A
protocol that cannot be refuted is not run.

## 2. Controls

Each comparison includes, at minimum:

* a **random** policy control,
* a **scripted heuristic** control (privileged, so it is an upper reference, not
  a competitor to be beaten blindly).

## 3. Equal budgets

All learning/evolutionary methods run under the same **interaction budget**
(environment `step` calls), recorded exactly. Compute differences (wall time) are
reported explicitly but are not the optimisation target.

## 4. Seeds

* Training uses `train_seeds`; evaluation uses disjoint `test_seeds`.
* Each method is run across multiple **independent** `seeds` (RNG seeds).
* Reported metrics are means across seeds with dispersion reported; confidence
  intervals are given when the number of seeds supports them.

## 5. Held-out evaluation

Test environments are generated from held-out seeds and never used for tuning.
Transfer is measured on:

* **morphology variants** — sensor fidelity, actuation and body changes;
* **perturbation variants** — obstacles, resource scarcity, hazard density,
  terrain structure, actuarial cost.

For morphology variants we distinguish:

* **zero-shot** transfer (no further training),
* **adapted** performance after a fixed adaptation budget,
* **adaptation gain** = adapted − zero-shot.

## 6. Failure handling

* A failed trial is stored with status `failed` and its error. Benchmark
  summaries report failures; they are never silently dropped.
* A crashed worker leaves a `running` row that `--resume` re-attempts.

## 7. Reporting rules

* Raw metrics, baseline comparison tables, training curves, transfer plots,
  compute-cost summaries and reproduction commands are produced together.
* No metric is reported unless it comes from stored trial artifacts.
* Negative and null results are reported with the same prominence as positive
  ones. Do not force a positive outcome.
* If sample size or compute prevents reliable inference, the experiment is
  explicitly labelled **preliminary**.

## 8. Artifacts per experiment

| Artifact | Path |
|---|---|
| Config manifest | `runs/<id>/manifest.json` |
| Trial metrics | SQLite `trials` table |
| Training history | `runs/<id>/<trial>.jsonl` |
| Winning genomes | `runs/<id>/<trial>.organism.json` |
| Tables | `runs/<id>/trials.csv`, `trials.parquet` |
| Plots | `runs/<id>/plots/*.png` |
| Summary | `runs/<id>/summary.json` |

## 9. Embodied morphology-transfer protocol

Used for the articulated-physics campaign (`configs/embodied_transfer.json`,
hypothesis `H2`).

1. **Fixed interface.** 7 observations, 5 motor primitives, independent of the
   number of joints. A body change alters the dynamics, never the interface.
2. **Source body.** Train on one body plan (`centipede`, 10 links).
3. **Bodies are distinct, not cosmetic.** `body_centipede`, `body_short_stiff`,
   `body_heavy_slow`, `body_slippery` differ in link count, length, mass, joint
   torque and friction.
4. **Two separate measurements.**
   * *zero-shot* — the unchanged controller on the new body;
   * *adapted* — the same controller after a fixed interaction budget on the new
     body, then evaluated on held-out seeds.
   They are never averaged into one "transfer score".
5. **Body vs world.** Morphology variants change the body; perturbation variants
   (`far_target`, `heavy_gravity`, `low_gravity`, `rough_friction`,
   `short_episode`) change the world. Reported separately.
6. **Budget parity.** Every learned method gets the same interaction budget on the
   source body; adaptation gets its own declared budget per body.
7. **Statistics.** Paired bootstrap CI on shared seeds for the primary comparison,
   with the minimum detectable effect reported. If the CI spans zero, the result is
   declared **unresolved at this sample size** — not "no effect".
8. **Preliminary by default.** Fewer than ~20 seeds ⇒ labelled preliminary.

### Task definition and its enforcement (added 2026-10-08)

The embodied task is **"reach the target while upright"**:

* **Success** requires arriving at the target region upright
  (`info["success"]`); falling onto the target is a fall, not a success.
* **A fall forfeits the shaping banked so far** (potential-based shaping with
  the failure state's potential set to zero): a fallen episode returns exactly
  `-fall_penalty`, so "travel far, then face-plant" can never outscore upright
  locomotion.
* **Adaptation never trains on evaluation seeds.** `transfer_embodied` refuses
  adaptation without disjoint held-out seeds, and the runner's transfer reports
  (both simulators) are covered by tests that capture the actual adaptation
  seeds. An "adaptation gain" that is not measured on unseen seeds is a bug.

Each of these is asserted by tests (`tests/test_embodied.py`,
`tests/test_embodied_eval.py`, `tests/test_runner_embodied.py`,
`tests/test_experiments.py`). Note that the morphology itself must be shown to
be *capable* of the task (see `scripts/probe_embodied_morphology.py`) before a
powered comparison is meaningful.
