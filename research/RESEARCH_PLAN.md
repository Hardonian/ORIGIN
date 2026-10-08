# ORIGIN Research Plan

## Research question

> Can evolutionary diversity and open-ended learning produce capabilities that
> transfer more effectively to unfamiliar environments and physical morphologies
> than conventional fixed-objective training?

## Hypothesis H1 (primary)

> Under an equivalent environment-interaction budget, maintaining behaviourally
> diverse populations (novelty search, quality-diversity) improves adaptation to
> unseen evaluation environments and to changed morphology relative to
> fixed-objective evolutionary optimization.

Status: **tested across four studies. NOT ESTABLISHED; the null is now BOUNDED.**

| study | seeds | design | novelty − GA | QD/MAP-Elites − GA | verdict |
|---|---|---|---|---|---|
| pilot | 1–5 | exploratory | +0.362 | −0.071 | — |
| 1 | 1–10 | independent | −0.228 [−1.43, +1.00] | −0.038 [−0.97, +0.97] | inconclusive |
| v2 | 11–20 | paired | +0.331 [−0.93, +1.55] | **+0.790** [−0.16, +1.65] | inconclusive |
| v3 | 21–60 (n=40) | **paired, power-sized** | out of scope (needs n≈321) | **−0.221** [−0.72, +0.26] | inconclusive, **bounded null** |

Study v3 was sized from a power analysis performed *before* it ran and scoped to the
one comparison with feasible power. At n=40 the design could detect a paired effect
of **≥ 0.708** at 80% power; the observed paired difference was **−0.221**. The
v2 hint of +0.790 therefore did not replicate, and the honest conclusion is
**bounded**: on this task any MAP-Elites advantage is smaller than ≈0.71 reward
units. `novelty_search` cannot be resolved at any feasible sample size here (the
power analysis requires n ≈ 321 for the effect it showed), so no claim about it is
made in either direction.

Every analysis was fixed in advance; no study was re-analysed after the fact and no
test was chosen after seeing results. See `reports/H1_powered_analysis.md` (study 1),
`reports/H1_paired_v2_analysis.md` (study v2) and `reports/H1_v3_decisive_analysis.md`
(study v3, bounded null).

## Falsification

H1 is falsified if, across independent seeds and under equal budgets,
diversity-maintaining methods show no improvement (within dispersion) over
fixed-objective evolution on held-out environments and transfer variants.

## Methods under comparison

1. `random` — uniform random policy (control)
2. `heuristic` — scripted BFS resource-seeker (privileged upper reference)
3. `fixed_objective_ga` — task-fitness-only evolution
4. `novelty_search` — novelty-archive evolution
5. `map_elites` — quality-diversity archive
6. `reinforce` — policy-gradient RL

## Metrics

Task performance (train and held-out), cross-morphology transfer (zero-shot and
adapted), adaptation gain, behavioural diversity (descriptor spread), archive
coverage (QD), robustness under perturbation, interaction cost and wall time,
variance across seeds.

## Programme

* **M8 pilot** — small task, 5 seeds, equal budget; establish the pipeline and a
  preliminary signal. (this repo)
* **M8 follow-up** — larger budgets, more seeds, richer morphology space, and a
  pre-registered analysis of transfer; see the release report's "Next milestone".

## Threats to validity

* Reactive controllers have a low ceiling on tasks requiring planning around
  obstacles/hazards; this bounds achievable effect sizes.
* Small seed counts widen confidence intervals; results are labelled preliminary.
* A single task family does not license general claims.

## What ORIGIN is not claiming

ORIGIN does not claim that artificial life, novelty search, MAP-Elites or
morphology transfer are new. See `PRIOR_ART.md`.
