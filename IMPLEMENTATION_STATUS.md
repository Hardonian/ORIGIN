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
| 6 | Research lab UI | **done** | 7 screens build; 6 headless-Chromium E2E tests verify live-data rendering |
| 7 | Local compute distribution | **partial** | CPU-first; `--jobs` concurrency; `scripts/origin_remote_worker.sh` ready. The EPYC tailnode is **offline** (see Blockers) |
| 8 | First research campaign | **done** | Pilot 30/30 + study 1 (60/60) + study v2 (60/60) + study v3 (160/160) — all 0 failures. **H1 not established, null BOUNDED**: v3 at n=40 (MDE 0.708) found −0.221 [−0.72, +0.26], so any MAP-Elites advantage is < ~0.71; the v2 hint did not replicate |

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
74 passed, 6 skipped        # skipped = browser E2E (opt-in)

$ .venv/bin/ruff check packages tests scripts benchmarks
All checks passed!

$ .venv/bin/mypy
Success: no issues found in 27 source files

$ cd apps/lab && npm run lint && npm run typecheck && npm run build
✔ No ESLint warnings or errors; typecheck clean; production build OK (10 routes)

$ node apps/lab/scripts/smoke-api.mjs   # UI↔API contract
13/13 checks passed

$ scripts/e2e_lab.sh                    # real headless browser against live API
6 passed

$ .venv/bin/origin-run --config configs/pilot_paired_v3.json --store runs --jobs 8
160 trials run, 0 failed

$ .venv/bin/python scripts/analyze.py --store runs --experiment 8f92870eaeb0 --design paired \
    --bootstrap-seed 20261010 --protocol-doc research/protocols/paired_v3_power.md
map_elites - fixed_objective_ga: -0.221, 95% paired CI [-0.721, +0.262], p=0.538 -> inconclusive
  minimum detectable paired effect = 0.708 (observed |mean diff| = 0.221)   # bounded null

$ scripts/origin_remote_worker.sh --check
ERROR: epyc is not reachable over SSH.   (expected: node offline — see Blockers)
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

* **Frontend dependency advisories.** `npm audit` reports 4 advisories against
  `next@14.2.35` requiring a breaking `next@16` upgrade (which also removes
  `next lint`). None apply to this configuration (no rewrites, no server actions,
  no `next/image`/AVIF, Linux host, loopback-only). Documented in `SECURITY.md`;
  the upgrade is tracked below. PostCSS advisories were fixed via an override.
* **REINFORCE is weak** at the pilot budget and previously collapsed to a
  single action; an entropy bonus was added, which raised it above the collapse
  but it still trails the random control. Reported honestly; it bounds RL claims.
* The **scripted heuristic** is privileged (global BFS) and is a reference, not a
  like-for-like competitor.
* **Interactive browser smoke test** — now covered: `scripts/e2e_lab.sh` runs 6
  Playwright/Chromium tests against the live API + production UI, and CI runs them.
* Pilots use ≤5 seeds; results are **preliminary**.

## Blockers

* **EPYC compute node is offline.** Diagnosed precisely: the node is on the
  Tailscale tailnet as `epyc` = `100.127.74.34`
  (`epyc.taile5788a.ts.net`), but `tailscale status` reports
  **`offline, last seen 4d ago`** and SSH:22 times out. This is not a
  configuration gap on this host — the machine is powered down / off the tailnet.
  The multi-host path is ready and correct: `scripts/origin_remote_worker.sh`
  mirrors the repo, runs the campaign remotely under `--jobs`, and pulls results
  back (trial ids are deterministic, so the merge is idempotent). When the node
  returns, one command distributes the work. Related nodes seen on the tailnet:
  `hx370` (windows), `hx370-1` (this WSL host), `poco-f7` (android).

## Remaining work

1. Upgrade the lab frontend to `next@16` to clear the 4 documented advisories
   (requires migrating `next lint` → ESLint CLI and React 19).
2. Articulated-physics embodiment (Milestone 4) with a real physics engine.
3. A QD-favouring task and a higher-powered replication: at n=10 the CIs still
   span 0, so no diversity-method advantage is established. A paired design (the
   methods share seeds) would be more efficient than the registered unpaired test.
4. Optional GPU-accelerated population evaluation on the compute node.
5. A headless browser (Playwright) smoke test for the UI in CI — **done**, in CI.

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

H1 is closed for this task as a bounded null (< ~0.71). The remaining scientific
question is a different one: whether a task with **genuine multi-niche structure**
(where quality-diversity has somewhere to put its diversity) shows an advantage that
this single-niche foraging world cannot. Pre-register the environment and the
analysis together *before* running it, and size it from a power analysis as study v3 was.
