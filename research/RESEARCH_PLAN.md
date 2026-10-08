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

Status: **tested across three studies; NOT ESTABLISHED (inconclusive in all three).**

| study | seeds | design | novelty − GA | QD − GA | verdict |
|---|---|---|---|---|---|
| pilot | 1–5 | none (exploratory) | +0.362 | −0.071 | — |
| study 1 | 1–10 | independent (unpaired) | −0.228, CI [−1.43, +1.00] | −0.038, CI [−0.97, +0.97] | inconclusive |
| study v2 | 11–20 | **paired** | +0.331, CI [−0.93, +1.55] | +0.790, CI [−0.16, +1.65] | inconclusive |

The sign is unstable across studies and every registered 95% CI spans zero. Both
study analyses were fixed in advance and neither study was re-analysed after the
fact. The honest conclusion is that **no advantage for diversity methods is
established on this task**, and that the exploratory pilot's positive direction was
noise. See `reports/H1_powered_analysis.md` and `reports/H1_paired_v2_analysis.md`.

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
