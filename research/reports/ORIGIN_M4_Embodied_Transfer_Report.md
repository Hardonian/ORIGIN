# ORIGIN — Milestone 4: Embodied Morphology Transfer (Preliminary)

> ## ⚠ CORRECTION AND RETRACTION — 2026-10-08
>
> **Every result in this report is retracted.** The embodied instrument these
> numbers came from was physically broken, and three independent measurement
> defects made the numbers untrustworthy even for the body that did run. The
> original text is retained below for the record only.
>
> **What was wrong (all verified by reproducible probes, not inference):**
>
> 1. **The body was not the body the report describes.** `_build_body` parented
>    every link to the base at a single point (`link_parent = [0] * n`), so the
>    "10-link centipede" was a clump of overlapping capsules, not a chain. The
>    capsules were also z-aligned (vertical posts) while the layout extended
>    along +x — a standing multi-pendulum that topples with **zero input**.
> 2. **The fall metric was wrap-broken.** `_is_upright` read Euler pitch, which
>    wraps at ±90°, so upside-down bodies read as "upright". The report's
>    `fall rate` column is unreliable.
> 3. **Adaptation gains were in-sample.** The transfer path fine-tuned on
>    `test_seeds[:2]` and then scored on the same `test_seeds`, so every
>    "adaptation gain" in Result 2 is optimistically biased and is withdrawn.
> 4. **The reward rewarded crashing.** Progress shaping accumulated regardless
>    of posture, so "travel far, then face-plant" outscored upright locomotion —
>    exactly what the `map_elites` row shows (highest score, 100% fall rate).
>
> **What was fixed** (code + regression guards, same session): real serial chain
> (`link_parent = list(range(n))`), capsules oriented along the link direction,
> wrap-immune tilt test, fall now cancels banked shaping (a fallen episode
> returns exactly `-fall_penalty`), success requires arriving upright, and
> adaptation trains on `train_seeds` only (the runner *refuses* overlapping
> adaptation/eval seeds in both simulators).
>
> **What the corrected instrument shows** (`scripts/probe_embodied_morphology.py`,
> and pilot campaign `589217adbe9e`, 15/15 trials, 0 failed):
>
> * the corrected chain **topples at rest** at steps 137–162 (all link counts),
>   so "stay upright" is unmeetable even doing nothing;
> * **no motor program, joint axis (pitch or yaw), or torque in 0.2–1.4 N·m
>   produces locomotion** — net displacement ≤ 0.02 m over a 6 s episode;
> * under the corrected task every method scores exactly **−1.000** (fall),
>   success rate **0.00** across all methods, bodies and perturbations.
>
> **Status of the milestone: INVALIDATED.** The morphology needs a design pass
> (anisotropic friction and/or a different actuation scheme — the standard snake
> robot arrangement) before any embodied transfer claim can be made. No embodied
> QD-vs-GA or transfer claim stands. Milestone 4 moves from "done (pilot)" to
> "blocked: morphology does not locomote".

**Status: retracted — see the correction above. Retained for the record.**
Every number below is produced by `scripts/analyze_embodied.py` from stored trial
rows; nothing is hand-entered. Raw artifacts live in `runs/aa1175d6c5aa/`
(gitignored, reproducible from the config).

```
experiment id   aa1175d6c5aa
config          configs/embodied_transfer.json
config hash     edbdded998dc
git sha         ccecf9f61cdbe5d0fdae91562fffd275ab840a1d
trials          15  (5 methods x 3 seeds), 0 failed
budget          40,000 environment interactions per algorithm trial
                (adaptation uses a separate 8,000-interaction budget per body)
wall clock      6 jobs on a Ryzen AI 9 HX370 (WSL2), CPU only
```

## Question

Milestone 3 asked whether behavioural diversity helps on a **single-niche grid
world**; the answer there was a bounded null (any MAP-Elites advantage < ~0.71
reward units, study v3). Milestone 4 asks a narrower, more physical question:

> Does a controller evolved on one articulated body **transfer** to genuinely
> different bodies — and if it does not, does a fixed adaptation budget recover it?

## System

Bodies are procedural planar articulated chains simulated in **PyBullet**
(8 physics substeps per control step). The controller interface is held fixed at
**7 observations / 5 discrete motor primitives** regardless of the number of
joints, so "transfer to another body" is well-posed rather than a shape error. The
source body is a **10-link centipede**; the transfer bodies change link count,
link length, mass, joint torque and friction (`body_centipede`, `body_short_stiff`,
`body_heavy_slow`, `body_slippery`).

## Result 1 — held-out performance on the source body

Evaluation on 3 seeds never used in training:

| method | n | mean test reward | sd | distance travelled (m) | fall rate | interactions |
|---|---|---|---|---|---|---|
| `map_elites` (QD) | 3 | **14.529** | 6.058 | 1.6125 | 1.00 | 41,327 |
| `fixed_objective_ga` | 3 | 7.530 | 6.283 | 1.0977 | 0.67 | 43,449 |
| `novelty_search` | 3 | 5.279 | 2.376 | 0.6586 | 1.00 | 43,713 |
| `random` | 3 | −0.010 | 1.281 | 0.1315 | 1.00 | 13 |
| `scripted_gait` (open-loop) | 3 | −3.547 | 0.000 | 0.2358 | 0.00 | 540 |

All three learned methods beat both controls. Unlike the grid world, **the
quality-diversity archive leads the fixed-objective GA** on the point estimate
(14.53 vs 7.53), which is the direction the diversity hypothesis predicts.

## Result 2 — transfer across physically distinct bodies

Zero-shot (no further training) vs adapted (8,000 interactions on the new body),
pooled over all methods and seeds (n=15 per body):

| body plan | zero-shot | adapted | gain | zs fall | adapted fall |
|---|---|---|---|---|---|
| `body_centipede` (source) | 5.257 | **27.982** | +18.828 | 0.89 | 0.67 |
| `body_heavy_slow` | −2.722 | 0.110 | +2.246 | 0.78 | 0.67 |
| `body_short_stiff` | −1.584 | 4.840 | +5.480 | 1.00 | 1.00 |
| `body_slippery` | −2.193 | 0.191 | +2.087 | 1.00 | 0.89 |
| **mean** | **1.120** | **8.281** | | | |

Two clear effects:

1. **Zero-shot transfer is weak.** Even the best controllers lose most of their
   competence on an unfamiliar body (mean 5.26 on the source body vs 1.12 across
   the others; three of four non-source bodies score *negative* zero-shot).
2. **A fixed adaptation budget largely recovers it.** Every body improves, and the
   pooled mean rises from 1.12 to 8.28. Adaptation is doing real work, not
   noise: the centipede body alone gains +18.8.

## Result 3 — environmental perturbations (zero-shot)

Held-out environmental changes are handled *without* adaptation:

| perturbation | mean reward (n=9) |
|---|---|
| `short_episode` | +9.300 |
| `far_target` | +9.181 |
| `rough_friction` | +8.246 |
| `heavy_gravity` | +4.702 |
| `low_gravity` | +3.143 |

Environmental robustness is much stronger than **morphological** robustness. This
is the substantive finding of the milestone: the bottleneck is the *body*, not the
*surroundings*.

## What is NOT established

**The QD-vs-GA difference is not statistically resolved at this sample size.**

```
map_elites - fixed_objective_ga = +6.999
  95% paired bootstrap CI [-2.617, +13.876]
  Wilcoxon signed-rank p = 0.5000
  minimum detectable effect at n=3 = 13.880  (observed |diff| = 6.999)
```

The CI spans zero. The point estimate favours QD and is consistent with the H2
direction, but n=3 cannot resolve an effect of this size — the MDE is twice the
observed difference. **This is a pilot, and it is reported as one.** No claim of a
QD advantage on embodied tasks is made.

Other limitations:

* **Fall rate is not a success criterion.** `map_elites` scores highest while
  falling in 100% of evaluated episodes: the reward accumulates forward progress,
  so a policy can travel far and then topple. High reward therefore means
  "travelled a long way", not "locomoted successfully". A stricter task
  (reach the target *and* remain upright) is the obvious next task revision, and
  the current numbers should not be read as stable locomotion.
* **No GPU.** The RX/EPYC node is offline; everything ran CPU-only. The 10-link
  body at 8 substeps/step is the practical ceiling here (~700–900 interactions/s
  across 6 workers).
* **Three seeds.** Every comparison in this report is underpowered by design.
* **No published baseline was re-implemented.** These are ORIGIN's own
  implementations; no external implementation was reproduced for cross-checking.

## Reproduction

```bash
.venv/bin/origin-run --config configs/embodied_transfer.json --store runs --jobs 6
.venv/bin/python scripts/analyze_embodied.py --store runs --experiment aa1175d6c5aa
```

Determinism is enforced by the test suite: identical config + seed + actions
reproduce identical trajectories and rewards exactly, and a saved body state
round-trips through `get_state`/`set_state` with an exact reward match
(`tests/test_embodied.py`, `tests/test_embodied_eval.py`).

## Next step

Size the embodied QD-vs-GA comparison properly. The MDE at n=3 is 13.88; the
observed difference is 7.00, so roughly an order of magnitude more seeds are
needed for the same effect size — and the task should be revised to score
*reaching the target upright* before that power is spent, otherwise the metric
being powered is the wrong one.
