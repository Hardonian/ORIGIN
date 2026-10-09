# Protocol — Study v3: Embodied Morphology Transfer (H2 Confirmatory Campaign)

**Registered before execution.** This is the confirmatory replacement for the retracted
Milestone 4 pilot. It runs exclusively on the physically calibrated, yaw-jointed crawler
with anisotropic ground contact that passed physical acceptance verification
(`runs/embodied-calibration.json`, hash `e12ed6c25b774523`, forward displacement $+1.007\text{ m} \ge 0.050\text{ m}$).

## Hypothesis and Scope

**H2.** Under an equivalent interaction budget, a **quality-diversity** search
(MAP-Elites over behavioral descriptors) produces controllers that transfer to unfamiliar
**physical morphologies** at least as well as a fixed-objective evolutionary search (GA),
and adapts faster when given a fixed budget on the new body.

Primary confirmatory comparison: MAP-Elites vs Fixed-Objective GA on held-out test reward.
Secondary confirmatory comparison: zero-shot transfer and post-adaptation gain across distinct
body morphologies (`body_centipede`, `body_short_stiff`, `body_heavy_slow`, `body_slippery`)
and environmental perturbations (`far_target`, `heavy_gravity`, `low_gravity`, `low_grip`, `short_episode`).

## Calibrated Morphology & Environment Contract

`configs/embodied_transfer_v3.json` fixes:
* **Simulator:** PyBullet DIRECT engine (headless physics client, deterministic substeps $\Delta t = 1/240\text{ s}$, control $\Delta t = 1/30\text{ s}$).
* **Morphology:** 10-link yaw-jointed planar crawler (`morphology: "centipede"`), link length $0.10\text{ m}$, link radius $0.028\text{ m}$, mass $0.12\text{ kg}$, joint torque $1.4\text{ N}\cdot\text{m}$, lateral friction $0.9$, longitudinal friction $0.18$.
* **Task Semantics:** Potential-based progress shaping to target distance $3.0\text{ m}$ (tolerance $0.25\text{ m}$) within episode limit $6.0\text{ s}$ ($180$ control steps). Upright posture strictly required: base height threshold $0.12\text{ m}$. A fall forfeits all accumulated shaping and returns fixed penalty $-1.000$. Success requires arriving upright at the target.
* **Control Interface:** 7-D continuous egocentric observation vector; 5 discrete motor primitives (`flex`, `extend`, `wave_a`, `wave_b`, `brake`).

## Budget & Train/Test Isolation

* **Training Budget:** 40,000 environment steps per trial.
* **Training Seeds:** `[11, 22, 33]`.
* **Held-Out Test Seeds:** `[101, 202, 303]` (strictly disjoint from training seeds).
* **Adaptation Budget:** 8,000 environment steps per foreign body plan.
* **Adaptation Seeds:** Adapted strictly on `train_seeds[:2]` (`[11, 22]`), and evaluated strictly on held-out `test_seeds` (`[101, 202, 303]`). Zero in-sample leakage.
* **Accounting:** Training interactions and evaluation interactions are counted in separate currencies. Baselines do not train (`interactions = 0`).

## Experimental Design

* **Algorithms:**
  - Confirmatory learners: `map_elites` (batch size 12, grid shape $8 \times 8$, mutation rate 0.3, mutation scale 0.4), `fixed_objective_ga` (pop size 24, max generations 400, mutation rate 0.3, mutation scale 0.4).
  - Descriptive learner: `novelty_search` (pop size 24, archive size 400).
  - Descriptive baselines: `random` (uniform motor primitives), `scripted_gait` (alternating travelling wave).
* **Method Seeds:** Paired seeds `[1, 2, 3, 4, 5]` ($n = 5$ paired runs per algorithm, 25 total trials).
* **Compute Infrastructure:** Distributed multi-process execution across remote node `epyc` (32 cores / 64 threads, Ubuntu Linux).

## Decision Rule & Statistical Analysis

For each method seed $s$:

\[
d_s = \text{held\_out\_reward}(\text{map\_elites}, s) - \text{held\_out\_reward}(\text{fixed\_objective\_ga}, s)
\]

1. Analysis executes via `scripts/analyze_embodied.py` against the experiment store.
2. Calculate a 95% paired percentile bootstrap confidence interval for $\text{mean}(d)$ across shared seeds using 10,000 resamples and seed **20261012**.
3. Report two-sided Wilcoxon signed-rank concordance test.
4. Compute and report the Minimum Detectable Effect (MDE).
5. If the 95% CI excludes zero:
   - Positive $\to$ H2 supported on held-out base task.
   - Negative $\to$ H2 falsified on held-out base task.
   - If CI spans zero $\to$ result declared inconclusive at this sample size with explicit MDE bounds (no trend language).
6. Transfer across body plans: report mean zero-shot performance, post-adaptation performance, and adaptation gain per body variant and perturbation.
