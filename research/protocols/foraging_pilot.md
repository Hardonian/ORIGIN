# Protocol — Foraging Pilot (Milestone 8)

## Task

A deterministic 10×10 egocentric foraging world. The agent must collect
resources while remaining within its energy budget. Training worlds contain
**no lethal hazards** (hazards are reserved as a robustness perturbation), so
that a reactive controller is a viable policy class.

Environment (`configs/pilot.json` → `env`):

* 10×10, `max_steps` 140, obstacle density 0.02, 5 resources, 0 hazards
* finite resources (`resource_regen = false`); episode ends when all collected
* step penalty 0.001, no wall penalty (so movement is never punished relative to
  standing still — this avoids a degenerate "do nothing" local optimum)
* observation: 7-D egocentric bearings only

## Conditions

| Method | Family | Budget |
|---|---|---|
| random | control | n/a (evaluation only) |
| heuristic | scripted BFS control | n/a (evaluation only) |
| fixed_objective_ga | evolution | 500 000 interactions |
| novelty_search | evolution | 500 000 interactions |
| map_elites | quality-diversity | 500 000 interactions |
| reinforce | RL | 500 000 interactions |

Seeds: 5 independent RNG seeds. Train seeds `[11,22,33,44]`; held-out test seeds
`[101,202,303,404]`.

## Transfer evaluation

For each trained artifact:

* held-out test seeds (same morphology);
* **morphology variants**: `sensor_local`, `sensor_nonspatial`, `body_fast`,
  `body_small` — zero-shot, plus adapted under a 50 000-interaction budget;
* **perturbation variants**: `obs_sparse`, `resource_scarce`, `hazard_dense`,
  `rooms`, `slow_actuator` — zero-shot.

## Outcomes

See `research/reports/ORIGIN_Initial_Research_Report.md` and
`docs/VERIFICATION_REPORT.md`.
