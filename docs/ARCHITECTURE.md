# ORIGIN Architecture

## Overview

ORIGIN is a monorepo with a single Python research platform (`packages/origin`)
and one front-end (`apps/lab`). Subsystems are independent but interoperable and
communicate only through explicit, serializable interfaces.

```
                 ┌──────────────────────────────────────────┐
                 │              experiments                 │
                 │  runner · store(SQLite) · read API       │
                 └───────────────┬──────────────────────────┘
                                 │ consumes
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
  ┌───────────┐           ┌────────────┐           ┌────────────┐
  │ evolution │           │  learning  │           │ evaluation │
  │ GA · NS   │           │ REINFORCE  │◀──────────│ Evaluator  │
  │ MAP-Elites│           └────────────┘           │ transfer   │
  └─────┬─────┘                                     └─────┬──────┘
        │                 ┌────────────┐                  │
        └────────────────▶│ organisms  │◀─────────────────┘
                          │ genome     │
                          │ morphology │
                          │ lineage    │
                          └─────┬──────┘
                                │ acts in
                          ┌─────▼──────┐
                          │environments│
                          │ GridWorld  │
                          └────────────┘
```

## Core design decisions

### 1. Determinism is a first-class contract
Every stochastic component is seeded through an explicit `numpy.random.Generator`.
Terrain, episode dynamics and RNG state are fully serializable
(`GridWorld.get_state` / `set_state`), enabling exact replay (`Replay`).
The acceptance criterion for Milestone 1 is enforced by tests.

### 2. A fixed control interface, variable morphology
The controller always consumes a **7-D egocentric observation**
`[energy, res_dr, res_dc, res_dist, haz_dr, haz_dc, haz_dist]`. Absolute position
is excluded so that policies cannot memorise a maze layout. Morphology changes:

* **sensor fidelity** — `obs_mode` ∈ {`vector`, `local`, `nonspatial`}
* **actuation** — `max_speed`
* **body** — `energy_capacity`

This is what makes cross-morphology transfer a *well-posed* question rather than
a shape error, and it is why `MLPController.resize_input` exists as a safety net
for structural mutation.

### 3. One interaction currency
`Evaluator` counts every environment `step` as one *interaction*. All algorithm
families consume an `Evaluator`, so "equal interaction budget" comparisons are
meaningful and computed identically everywhere.

### 4. Data-only organisms
A controller genome is JSON arrays. No pickle, no externally supplied code.
`tests/test_security.py` enforces this.

### 5. Honest persistence
Trials are recorded transactionally. A failed trial is stored as `failed` with an
error string; a crashed worker leaves a resumable `running` row. Benchmark
summaries never drop failures silently.

## Package map

| Package | Responsibility |
|---|---|
| `origin.environments` | Deterministic `GridWorld`, config schema, replay |
| `origin.organisms` | `MLPController`, `Morphology`, `Organism`, `Lineage`, baselines |
| `origin.evolution` | `fixed_objective_ga`, `novelty_search`, `map_elites`, `fine_tune` |
| `origin.learning` | `reinforce` (NumPy policy gradient) |
| `origin.evaluation` | `Evaluator`, episode runner, morphology/perturbation variants |
| `origin.experiments` | `runner`, `Store`, read `api` |
| `origin.telemetry` | `MetricLogger` (JSONL) |
| `origin.visualization` | training / transfer / descriptor plots |

## Data model (SQLite)

* `experiments(id, name, protocol, config_hash, config_json, git_sha, status)`
* `trials(id, experiment_id, algorithm, seed, status, interactions, budget,
  best_fitness, train_fitness, metrics_json, transfer_json, error)`
* `artifacts(id, experiment_id, trial_id, kind, path)`

Experiment id = `sha256(config)[:12]`; trial id = `sha256(exp|algo|seed)[:16]`.

## Extensibility

New algorithms implement a `(evaluator, base_env, seed, **kwargs) ->
OptimizationResult` signature and register in `ALGORITHMS`. New environments
expose the Gymnasium API and a `_descriptor()` for novelty/QD.

## Embodied simulation (Milestone 4)

Two simulators share one optimizer stack, selected by `env_kind` in the config:

| | `gridworld` | `embodied` |
|---|---|---|
| Environment | deterministic seeded grid | articulated bodies in **PyBullet** |
| Observation | 7-D egocentric | 7-D body state |
| Actions | 5 (or 9 diagonal) | 5 motor primitives |
| Descriptor | 5-D behaviour | `[travelled, upright_frac, energy, rate, time_frac]` |
| Baselines | `random`, `heuristic` | `random`, `scripted_gait` |

The optimizers depend only on an **evaluator contract** — `exhausted`,
`interactions`, `budget`, `train_seeds`, `evaluate_organism(org) -> (fitness,
descriptor, episodes)` — so the same GA / novelty search / MAP-Elites / REINFORCE
code drives either simulator. Only three things are simulator-specific, and each is
explicit rather than assumed:

1. **RL env factory** — `reinforce(..., env_factory=...)` builds the episodes' envs,
   so the RL loop is not hard-wired to `GridWorld`.
2. **QD descriptor axes** — `map_elites(..., desc_dims, bounds)` receives the
   archive axes and ranges; the grid defaults are preserved, but no simulator's
   descriptor semantics are assumed by the archive.
3. **Baseline set** — `BASELINES[kind]`, validated at config load.

Bodies are built procedurally (`createMultiBody` over a chain of capsule links with
revolute joints about +y), simulated at 8 physics substeps per control step in
`DIRECT` mode. Determinism is exact for a fixed config/seed/action sequence, and
`get_state`/`set_state` round-trips base pose **and velocity** plus joint states —
omitting base velocity was a real bug that made replays diverge immediately.

## Non-goals

No microservices, no cloud database, no orchestration framework. ORIGIN stays a
single-process (optionally multi-process) local tool by design.
