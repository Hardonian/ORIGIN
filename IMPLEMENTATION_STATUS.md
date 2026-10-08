# ORIGIN — Implementation Status

> Persistent status ledger. **Only verified features are marked complete.**
> A feature is "verified" only if a command was actually run and its result observed.
> Last updated: 2026-10-08. Current commit: see `git rev-parse HEAD`.

## Milestones

| # | Milestone | State | Evidence |
|---|---|---|---|
| 0 | Research & environment baseline | **done** | `docs/ARCHITECTURE.md`, `research/RESEARCH_PLAN.md`, `research/PRIOR_ART.md`, `docs/REPRODUCIBILITY.md`, `docs/EXPERIMENT_PROTOCOL.md` |
| 1 | Artificial environment engine | **done** | `origin.environments.GridWorld`; determinism/replay/serialization tests pass |
| 2 | Evolving organisms | **done** | `origin.organisms` (morphology/genome/lineage); invariant + serialization tests pass |
| 3 | Learning & evolution baselines | **done** | GA, novelty search, MAP-Elites, REINFORCE all run under a shared interaction budget |
| 4 | Embodied intelligence / morphology transfer | **INVALIDATED — redesigned, awaiting physical acceptance** | The instrument was physically broken (links clumped at one point, capsules vertical) and three measurement defects made every number untrustworthy. All M4 results **retracted** — see the correction at the top of `research/reports/ORIGIN_M4_Embodied_Transfer_Report.md`. The new yaw-jointed, anisotropic-friction crawler has regression coverage and a fail-closed calibration probe, but it has **not yet passed that probe on a supported PyBullet host**; no embodied claim is restored. |
| 5 | Experiment orchestration | **done** | `origin.experiments.runner` + `store`; manifests, resume, cancellation, bounded concurrency, CSV/Parquet |
| 6 | Research lab UI | **done** | 7 screens on **Next 16.4.0**; ESLint 9 flat config; 6 headless-Chromium E2E tests verify live-data rendering |
| 7 | Local compute distribution | **partial — worker model verified; multi-host run pending** | Real worker model landed and verified across **real worker processes**: atomic trial claims, heartbeats, stale-worker recovery, keep-first completion, idempotent store merge (`origin-worker`, `origin-merge-stores`, `tests/test_worker_model.py` 19 tests). 3-process CLI campaign: 9/9 trials, claims disjoint (2+4+3), 0 duplicates. Real-crash probe `scripts/probe_worker_recovery.py`: SIGKILL mid-trial → orphan recovered, 11/11 checks. `--jobs` concurrency and `scripts/origin_remote_worker.sh` (SSH path, staged merge) ready. Remaining: one real multi-host campaign — the EPYC tailnode is **offline** (see Blockers) |
| 8 | First research campaign | **partial — grid half stands** | Grid: pilot 30/30 + study 1 (60/60) + v2 (60/60) + v3 (160/160), all 0 failures. **H1 not established, null BOUNDED**: v3 at n=40 (MDE 0.708) found −0.221 [−0.72, +0.26]. Embodied half is **retracted** with milestone 4. Caveat: any *adaptation-gain* number produced before 2026-10-08 (grid included) was measured in-sample and must be re-run before being cited |

## Verified features

* **Environment determinism** — identical config+seed ⇒ identical terrain and trajectory (`tests/test_environment.py`).
* **Replay** — recorded action sequence reproduces rewards exactly (`Replay.re_run`).
* **Interaction budget accounting** — every algorithm consumes a shared `Evaluator`; budgets comparable.
* **Train/test isolation** — the runner *refuses* overlapping train/test seeds.
* **Transfer** — zero-shot + adapted morphology transfer; perturbation robustness measured.
* **Persistence** — SQLite (metadata) + JSONL (history) + CSV/Parquet (tables) + PNG (plots).
* **Safety** — data-only JSON genomes (no pickle), loopback-bound services; asserted in `tests/test_security.py`.
* **Embodied physics** — procedural articulated chains in PyBullet (serial
  chain, capsules oriented along the link direction); identical
  config+seed+actions reproduce identical trajectories and rewards exactly, and
  `get_state`/`set_state` round-trips to an exact reward match (including the
  banked shaping a fall forfeits). Episodes always disconnect their physics
  client (no leak across a campaign).
* **Embodied task semantics** — a fall cancels the shaping banked so far (a
  fallen episode returns exactly `-fall_penalty`, so "travel far, then fall"
  cannot outscore upright locomotion) and success requires reaching the target
  while upright. Asserted in `tests/test_embodied.py`.
* **Train/test isolation in transfer** — adaptation runs on `train_seeds` only;
  `transfer_embodied` *refuses* adaptation without disjoint held-out seeds, and
  the runner's transfer reports (both simulators) are guarded by tests that
  capture the actual adaptation seeds. Asserted in
  `tests/test_embodied_eval.py`, `tests/test_runner_embodied.py`,
  `tests/test_experiments.py`.
* **Order-independent baseline evaluation** — policies are reseeded per episode
  (a stateful baseline's result on a seed does not depend on what ran before it),
  the env owns a copy of its config (a caller's shared config is never mutated),
  and `set_state` fails closed on joint-count mismatch. Asserted in
  `tests/test_embodied_eval.py`, `tests/test_embodied.py`.
* **Simulator-agnostic optimizers** — GA, novelty search, MAP-Elites and
  REINFORCE run unchanged against either simulator; the only per-simulator
  differences are an env factory (RL), descriptor axes (QD) and baseline set.
  Asserted in `tests/test_runner_embodied.py`.
* **Distributed worker model** — independent worker processes share one store.
  Each trial is claimed atomically (exactly one live, heartbeating owner),
  workers heartbeat while they work, and a stale worker's trials return to the
  pool for another worker to take over. Verified across **real worker
  processes** (3-process CLI campaign: 9/9 trials, disjoint claims, 0
  duplicates) and against a **real crash** (`scripts/probe_worker_recovery.py`
  SIGKILLs a worker mid-trial: the orphaned `running` row is detected, the
  worker is reaped, the trial is recovered and every trial ends `done` exactly
  once). Asserted in `tests/test_worker_model.py`.
* **Idempotent completion and store merge** — trial ids are deterministic
  (`sha256(experiment|algorithm|seed)`); completion is keep-first (a `done` row
  is never overwritten — duplicate computations are reported as dropped), and
  `origin-merge-stores` merges stores by trial id idempotently (a second merge
  is a no-op; both-done conflicts are reported, never silently resolved).
  Asserted in `tests/test_worker_model.py`.

## Latest successful tests (all re-run 2026-10-08)

```
$ .venv/bin/python -m pytest tests
143 passed, 6 skipped        # 149 collected; skipped = browser E2E (opt-in)
$ .venv/bin/ruff check packages tests scripts benchmarks
All checks passed!
$ .venv/bin/mypy
Success: no issues found in 30 source files
$ cd apps/lab && npm run lint && npm run typecheck && npm run build
✔ No ESLint warnings or errors; typecheck clean; production build OK
$ node apps/lab/scripts/smoke-api.mjs   # UI↔API contract (API on :8788)
16/16 checks passed          # grid world payload + embodied graceful-400 contracts
$ scripts/e2e_lab.sh                    # real headless browser against live API
6 passed; all 7 routes HTTP 200
$ .venv/bin/origin-run --config configs/embodied_transfer.json --store runs --jobs 6
15 trials run, 0 failed      # experiment 589217adbe9e — corrected task; result is
                             # a constant -1.000 with 0 successes (task unsolvable)
$ .venv/bin/python scripts/probe_embodied_morphology.py
rest: topples at steps 137-162 for 5/10/20 links (zero input)
primitives x torque: max net displacement 0.194 m (tumbling episodes)
joint axis x torque x gait: x <= 0.002 m in every variant
$ .venv/bin/python scripts/analyze_embodied.py --store runs --experiment 589217adbe9e
all methods: mean -1.000, fall 1.00, success 0.00   # morphology does not locomote
$ .venv/bin/python scripts/analyze.py --store runs --experiment 8f92870eaeb0 --design paired \
    --bootstrap-seed 20261010 --protocol-doc research/protocols/paired_v3_power.md \
    --out research/reports/H1_v3_decisive_analysis.md     # NOTE: --out, or it clobbers
map_elites - fixed_objective_ga: -0.221, 95% paired CI [-0.721, +0.262], p=0.538 -> inconclusive
  minimum detectable paired effect = 0.708 (observed |mean diff| = 0.221)   # bounded null
$ .venv/bin/bandit -q -r packages/origin  # CI gates medium+
0 medium/high; 13 low (8 B101 invariant asserts; 5 subprocess-scan lows from
  runner.py's git manifest helper — static argv, no shell) — all documented
$ .venv/bin/origin-worker --config <campaign> --store <store>   # x3, real processes
cli-worker-1 claimed=2 completed=2; cli-worker-2 claimed=4 completed=4;
  cli-worker-3 claimed=3 completed=3     # 9/9 trials, claims disjoint, 0 duplicates
$ .venv/bin/origin-merge-stores --from <src> --into <dst>       # run twice
first:  {trials: 9, conflicts: []}; second: {trials: 0, trials_skipped_done: 9}
$ .venv/bin/python scripts/probe_worker_recovery.py             # real SIGKILL mid-trial
11/11 checks passed   # orphan detected, victim reaped, trial recovered,
                      # every trial done exactly once under the rescuer
$ .venv/bin/origin-worker --store runs --status
workers listed with heartbeat ages; trial counts per status
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
* One interaction currency (`env.step` calls) for all methods, on both simulators.
* **Simulators are pluggable.** `env_kind` selects `gridworld` or `embodied`. The
  optimizers depend only on an evaluator contract (`exhausted` / `interactions` /
  `budget` / `train_seeds` / `evaluate_organism`), so the same GA, novelty search,
  MAP-Elites and REINFORCE code drives a grid agent or a physics body. Per-simulator
  differences are isolated to three places: an **env factory** for RL, explicit
  **descriptor axes/bounds** for QD (no simulator-silent assumptions), and the
  **baseline set** (`random`/`heuristic` vs `random`/`scripted_gait`).
* **Body changes ≠ environment changes.** Morphology transfer varies the *body*
  (links, mass, torque, friction); perturbation transfer varies the *world* (gravity,
  target distance, friction, episode length). They are reported separately because
  they measure different things.
* **The control interface is fixed at 7 observations / 5 actions in both
  simulators.** For the articulated bodies this means the morphology changes the
  dynamics the controller must cope with, never the size of its interface — which is
  what makes "transfer this controller to that body" a well-posed experiment.
* **The embodied task is "reach the target while upright".** Success requires
  arriving upright; a fall cancels the shaping banked so far (a fallen episode
  returns exactly `-fall_penalty`, potential-based shaping with zero potential at
  the failure state), so "travel far, then crash" cannot outscore upright
  locomotion. Partial competence stays visible in the metrics (distance
  travelled, upright fraction, fall rate), not in the return of a failed episode.
* No `pickle`, no arbitrary code execution, loopback-only services.


## Known defects / limitations

* **The retired v2 morphology does not locomote; the replacement is unverified.**
  The old isotropic, vertical-plane torque chain failed the 2026-10-08 probe.
  The replacement uses yaw joints, direction-dependent contact and force-limited
  position motors, with a probe that fails unless a production gait gains 5 cm in
  3 s. That acceptance run must complete on a supported PyBullet host before any
  embodied result is reported.
* **All M4 embodied results are retracted** (2026-10-08): the body was not the
  body the report described, the fall metric was wrap-broken, and adaptation
  gains were measured in-sample. See the correction at the top of
  `research/reports/ORIGIN_M4_Embodied_Transfer_Report.md`. The pre-registered
  H2 is **untested** until re-run on a working morphology.
* **Adaptation-gain numbers produced before 2026-10-08 are in-sample** (the
  transfer paths fine-tuned on `test_seeds[:2]` and scored on the same seeds).
  The code is fixed and guarded by tests; any old "adaptation gain" quoted
  anywhere must be re-measured before use.
* **`interactions` semantics changed 2026-10-08.** It now means *training*
  interactions (0 for baselines), with `evaluation_interactions` reported
  separately — previously baselines reported evaluation steps while learners
  reported training steps, so "compute cost per method" mixed currencies. Rows
  stored before this change need a re-run before their compute cost is cited.
* **`scripts/analyze.py` writes a fixed default report path**
  (`research/reports/H1_powered_analysis.md`) — running it without `--out`
  clobbers that file. Always pass `--out` (documented in the reproduction
  commands below).
* **Frontend dependency advisories.** The 4 Next.js runtime advisories are
  **resolved** by the `next@16.4.0` upgrade (with ESLint 9 flat config replacing
  the removed `next lint`). One **dev-only** advisory remains unfixable at
  present: `braces` (via the Next lint plugin), where `braces@3.0.3` is the
  newest release and the advisory covers all versions. Documented in
  `SECURITY.md`; not shipped in the app bundle.
* **REINFORCE is weak** at the pilot budget and previously collapsed to a
  single action; an entropy bonus was added, which raised it above the collapse
  but it still trails the random control on the grid task. Reported honestly; it
  bounds RL claims.
* **The scripted heuristic is privileged** (global BFS) and is a reference, not a
  like-for-like competitor. The embodied `scripted_gait` is open-loop and cannot
  adapt at all by construction.
* **The world viewer is grid-only.** `/api/world` now *degrades gracefully*
  (structured 400 naming the reason) for embodied experiments instead of
  crashing with a 500; a 3-D morphology viewer is not built. Covered by the API
  smoke test and the browser E2E suite.
* Grid pilots use ≤5 seeds per study tier (v3 uses 40 paired seeds). Embodied
  sample sizes are moot until the morphology works.

## Blockers

* **Embodied physics calibration.** The yaw-joint + anisotropic-friction design
  has replaced the inert v2 chain, but this Windows host cannot install PyBullet
  (no compatible wheel and no C++ build tools). Run
  `scripts/probe_embodied_morphology.py` on a supported host; it must pass before
  a new transfer campaign spends seeds.
* **EPYC compute node is offline.** Diagnosed precisely: the node is on the
  Tailscale tailnet as `epyc` = `100.127.74.34`
  (`epyc.taile5788a.ts.net`), but `tailscale status` reports
  **`offline, last seen 4d ago`** and SSH:22 times out. This is not a
  configuration gap on this host — the machine is powered down / off the tailnet.
  The multi-host path is ready: `scripts/origin_remote_worker.sh` mirrors the
  repo, runs the campaign remotely, and pulls results back via a **staged
  `origin-merge-stores` merge** (deterministic trial ids → idempotent, local
  rows never clobbered). Remote workers can also simply run `origin-worker`
  against a shared store. When the node returns, one command distributes the
  work. Related nodes seen on the tailnet:
  `hx370` (windows), `hx370-1` (this WSL host), `poco-f7` (android).

## Remaining work

1. **Embodied crawler calibration** (blocked on a supported PyBullet host).
   Acceptance: `scripts/probe_embodied_morphology.py` shows a production gait
   that remains upright and gains ≥5 cm in 3 s. Then set a target distance from
   that measured speed and pre-register a fresh H2 campaign; the retracted v2
   campaign is not reused.
2. **Milestone 7 (compute distribution)**: the worker model is **done and
   verified** — heartbeats, atomic claims, stale-worker recovery (real SIGKILL
   probe), keep-first completion, idempotent merge by deterministic trial id,
   all proven across real local worker processes
   (`tests/test_worker_model.py`, `scripts/probe_worker_recovery.py`). What
   remains is exactly one real multi-host campaign once the EPYC node is back
   (Blockers) — the remote path is the same mechanism over SSH.
3. **Milestone 6 (UI)**: 7 screens E2E-tested; the 3-D morphology viewer is not
   built (grid viewer only, now with graceful degradation).
4. A multi-niche grid task: H1 is closed for the current single-niche world as a
   bounded null (< ~0.71).
5. Watch for an upstream fix to the dev-only `braces` advisory (Next lint plugin).

## Reproduction commands

```bash
uv venv --python 3.12 .venv && uv pip install -e '.[dev]' --python .venv/bin/python
.venv/bin/python -m pytest tests -q
.venv/bin/origin-run --config configs/pilot.json --store runs --jobs "$(nproc)"
# distributed worker model (any number of processes, one shared store):
.venv/bin/origin-worker --config configs/pilot.json --store runs --stale-after 120
.venv/bin/origin-worker --store runs --status
.venv/bin/python scripts/probe_worker_recovery.py        # real crash-recovery proof
.venv/bin/origin-merge-stores --from runs-remote --into runs   # idempotent merge
.venv/bin/origin-api  --store runs --host 127.0.0.1 --port 8788 &
(cd apps/lab && npm install && npm run build && npm run start)
.venv/bin/python scripts/make_report.py --store runs
.venv/bin/python scripts/probe_embodied_morphology.py     # morphology capability check
.venv/bin/python scripts/analyze.py --store runs --experiment 8f92870eaeb0 --design paired \
  --bootstrap-seed 20261010 --protocol-doc research/protocols/paired_v3_power.md \
  --out research/reports/H1_v3_decisive_analysis.md       # always pass --out
```

## Next executable action

**Run the embodied calibration probe on a supported PyBullet host** (see
Blockers). It gates milestone 4, a fresh pre-registered H2, and any seed spending
on the embodied task.

**While that decision is pending, the highest-ROI executable work is Milestone 7
(local compute distribution)** — the last milestone with an unverified core
claim. Make distribution real *without* the remote node: a proper worker model
(heartbeats, stale-worker recovery, idempotent merge by deterministic trial id)
verified by running a campaign across several real worker processes locally,
with the remote path as the same mechanism over SSH. That converts "ready but
unverified" into "verified, and the remote node is just another host".
