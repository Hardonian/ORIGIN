# ORIGIN — Implementation Status

> Persistent status ledger. **Only verified features are marked complete.**
> A feature is "verified" only if a command was actually run and its result observed.
> Last updated: 2026-10-07. Current commit: see `git rev-parse HEAD`.

## Milestones

| # | Milestone | State | Evidence |
|---|---|---|---|
| 0 | Research & environment baseline | **done** | `docs/ARCHITECTURE.md`, `research/RESEARCH_PLAN.md`, `research/PRIOR_ART.md`, `docs/REPRODUCIBILITY.md`, `docs/EXPERIMENT_PROTOCOL.md` |
| 1 | Artificial environment engine | **done** | `origin.environments.GridWorld`; determinism/replay/serialization tests pass |
| 2 | Evolving organisms | **done** | `origin.organisms` (morphology/genome/lineage); invariant + serialization tests pass |
| 3 | Learning & evolution baselines | **done** | GA, novelty search, MAP-Elites, REINFORCE all run under a shared interaction budget |
| 4 | Embodied intelligence / morphology transfer | **partial** | 2D sensor/actuator/body transfer + adaptation implemented and measured. **Not done:** articulated-body physics (PyBullet/MuJoCo) |
| 5 | Experiment orchestration | **done** | `origin.experiments.runner` + `store`; manifests, resume, cancellation, bounded concurrency, CSV/Parquet |
| 6 | Research lab UI | **partial** | 7 screens build and render live API data; see "UI" below for the one unverified item |
| 7 | Local compute distribution | **partial** | CPU-first; `--jobs` concurrency + documented multi-host pattern. EPYC compute node was **not reachable** from this host (see Blockers) |
| 8 | First research campaign | **done** | 30/30 trials, 0 failures; report auto-generated from stored artifacts |

## Verified features

* **Environment determinism** — identical config+seed ⇒ identical terrain and trajectory (`tests/test_environment.py`).
* **Replay** — recorded action sequence reproduces rewards exactly (`Replay.re_run`).
* **Interaction budget accounting** — every algorithm consumes a shared `Evaluator`; budgets comparable.
* **Train/test isolation** — the runner *refuses* overlapping train/test seeds.
* **Transfer** — zero-shot + adapted morphology transfer; perturbation robustness measured.
* **Persistence** — SQLite (metadata) + JSONL (history) + CSV/Parquet (tables) + PNG (plots).
* **Safety** — data-only JSON genomes (no pickle), loopback-bound services; asserted in `tests/test_security.py`.

## Latest successful tests

```
$ .venv/bin/python -m pytest tests -q
57 passed

$ .venv/bin/ruff check packages tests scripts benchmarks
All checks passed!

$ .venv/bin/mypy
Success: no issues found in 26 source files

$ cd apps/lab && npm run typecheck && npm run build
✓ compiled successfully; 10 routes; production build OK

$ node apps/lab/scripts/smoke-api.mjs   # UI↔API contract
13/13 checks passed

$ .venv/bin/origin-run --config configs/pilot.json --store runs --jobs 6
30 trials run, 0 failed
```

## Current architecture decisions

* Fixed **7-D egocentric** control interface; morphology varies sensor fidelity
  (`vector`/`local`/`nonspatial`), actuation (`max_speed`) and body
  (`energy_capacity`). Absolute position is excluded to prevent memorisation.
* Movement is **not** penalised relative to standing still (avoids a degenerate
  "do nothing" optimum); hazards are held out of training and used only as a
  robustness perturbation in the pilot.
* One interaction currency (`env.step` calls) for all methods.
* No `pickle`, no arbitrary code execution, loopback-only services.

## Known defects / limitations

* **REINFORCE is weak** at the pilot budget and previously collapsed to a
  single action; an entropy bonus was added, which raised it above the collapse
  but it still trails the random control. Reported honestly; it bounds RL claims.
* The **scripted heuristic** is privileged (global BFS) and is a reference, not a
  like-for-like competitor.
* **Interactive browser smoke test not run**: the available browser tool cannot
  reach loopback addresses, so the UI was verified by build + static types + an
  API-contract test, not by a live headless render. This is a limitation, not a pass.
* Pilots use ≤5 seeds; results are **preliminary**.

## Blockers

* **EPYC compute server unreachable** from this workstation (no SSH host entry; the
  hostname does not resolve; port 22 closed). Work stayed CPU-only on the
  workstation. Documented in `infra/README.md`; `--jobs` distribution is ready for
  when the node is reachable.

## Remaining work

1. Articulated-physics embodiment (Milestone 4) with a real physics engine.
2. A powered replication of H1 (more seeds/budgets) and a QD-favouring task.
3. Optional GPU-accelerated population evaluation on the compute node.
4. A headless browser (Playwright) smoke test for the UI in CI.

## Reproduction commands

```bash
uv venv --python 3.12 .venv && uv pip install -e '.[dev]' --python .venv/bin/python
.venv/bin/python -m pytest tests -q
.venv/bin/origin-run --config configs/pilot.json --store runs --jobs "$(nproc)"
.venv/bin/origin-api  --store runs --host 127.0.0.1 --port 8788 &
(cd apps/lab && npm install && npm run build && npm run start)
.venv/bin/python scripts/make_report.py --store runs
```

## Next executable action

Run the powered H1 replication: increase `seeds` and `budget` in
`configs/pilot.json`, add a descriptor-designed task where quality-diversity can
express its advantage, and pre-register the analysis before running.
