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

Status: **task-specific strict-cap evidence; no universal H1 conclusion.**

| study | paired seeds | primary endpoint | MAP-Elites − GA | verdict |
|---|---:|---|---:|---|
| legacy single-niche v3 | 40 | held-out base reward under its historical protocol | −0.221 [−0.72, +0.26] | inconclusive / bounded for that legacy task |
| strict-cap single-niche v4 | 40 | held-out base reward | +0.679 [+0.112, +1.241] | supported for the registered endpoint |
| strict-cap multi-niche v3 | 64 | mean adapted reward over fixed ecological shocks | +0.418 [+0.057, +0.778] | supported for the registered endpoint |
| calibrated embodied H2 v3 | 5 | held-out base reward | +2.548 [−2.480, +9.272] | inconclusive for MAP-Elites vs GA |

The legacy v3 bounded-null result is retained rather than overwritten: it
showed that the earlier single-niche design could not support the prior v2
signal. The v4 and multi-niche registrations use strict pre-reserved caps and
their own fixed endpoints. Their positive intervals are evidence for those
tasks, not proof that behavioural diversity wins generally. Novelty search has
no confirmed general advantage. The authoritative study classifications and
reports are listed in `research/reports/RESULT_PROVENANCE.md`.

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
* **Independent follow-up** — fresh environments, new morphology families, and
  pre-registered analyses that test whether the task-specific strict-cap results
  replicate without retuning against the observed endpoints.

## Threats to validity

* Reactive controllers have a low ceiling on tasks requiring planning around
  obstacles/hazards; this bounds achievable effect sizes.
* Small seed counts widen confidence intervals; results are labelled preliminary.
* A single task family does not license general claims.

## What ORIGIN is not claiming

ORIGIN does not claim that artificial life, novelty search, MAP-Elites or
morphology transfer are new. See `PRIOR_ART.md`.
