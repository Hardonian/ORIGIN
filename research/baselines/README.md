# Baselines

Documented baseline policies and algorithms, with their provenance and the exact
ORIGIN implementation.

| Name | Kind | ORIGIN implementation | Reference |
|---|---|---|---|
| `random` | control | `origin.organisms.policies.RandomPolicy` | — |
| `heuristic` | scripted control (privileged BFS) | `origin.organisms.policies.HeuristicPolicy` | — |
| `fixed_objective_ga` | evolution | `origin.evolution.ga.fixed_objective_ga` | standard μ+λ GA w/ tournament selection |
| `novelty_search` | open-ended evolution | `origin.evolution.novelty.novelty_search` | Lehman & Stanley 2011 |
| `map_elites` | quality-diversity | `origin.evolution.qd.map_elites` | Mouret & Clune 2015 |
| `reinforce` | RL | `origin.learning.reinforce.reinforce` | Williams 1992 |

## Notes on the heuristic control

`HeuristicPolicy` performs breadth-first search to the nearest resource avoiding
obstacles and hazards. It uses privileged environment state and is a reference
upper bound, not a competitor: a learned policy is not expected to beat a planner
with full knowledge. It exists to sanity-check that the task is solvable and that
the reward signal is sane.

## Notes on `reinforce`

Pure-NumPy REINFORCE with return normalisation and Adam. It is included to
demonstrate a genuine gradient-based learner under the same interaction budget.
It is deliberately not tuned for peak sample efficiency; RL baselines are known
to be sample-hungry and this is reported honestly rather than hidden.
