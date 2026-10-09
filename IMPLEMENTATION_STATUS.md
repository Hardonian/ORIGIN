# ORIGIN — Implementation Status

> Persistent status ledger. **Only verified features are marked complete.**
> A feature is "verified" only if a command was actually run and its result observed.
> Last updated: 2026-10-09. Current commit: see `git rev-parse HEAD`.

## Milestones

| # | Milestone | State | Evidence |
| --- | --- | --- | --- |
| 0 | Research & environment baseline | **done** | `docs/ARCHITECTURE.md`, `research/RESEARCH_PLAN.md`, `research/PRIOR_ART.md`, `docs/REPRODUCIBILITY.md`, `docs/EXPERIMENT_PROTOCOL.md` |
| 1 | Artificial environment engine | **done** | `origin.environments.GridWorld`; determinism/replay/serialization tests pass |
| 2 | Evolving organisms | **done** | `origin.organisms` (morphology/genome/lineage); invariant + serialization tests pass |
| 3 | Learning & evolution baselines | **done** | GA, novelty search, MAP-Elites, REINFORCE all run under a shared interaction budget |
| 4 | Embodied intelligence / morphology transfer | **done — physically calibrated & verified** | Articulated yaw-joint crawler with anisotropic ground contact passed physical acceptance probe (`scripts/probe_embodied_morphology.py`: $+1.007\text{ m} \ge 0.050\text{ m}$ forward displacement in 3.0 s while upright). Persisted calibration evidence in `runs/embodied-calibration.json` (`config_hash: e12ed6c25b774523`). Pre-registered confirmatory H2 campaign (`1bdb4b622748`, 25/25 trials, 0 failures) verified zero-shot morphology cost (mean $-4.95$ on foreign bodies) and rapid recovery under 8,000-step adaptation (gains $+6.66$ to $+9.50$). Full report: `research/reports/ORIGIN_M4_Embodied_Transfer_Report_v3.md`. |
| 5 | Experiment orchestration | **done** | `origin.experiments.runner` + `store`; manifests, resume, cancellation, bounded concurrency, CSV/Parquet |
| 6 | Research lab UI & 3D visualization | **done — cutting edge & gamified** | 8 screens on **Next 16.4.0 / React 19.3.0** with bioluminescent glassmorphism design system; pure Web Audio synthesized SFX (blip, click, step, level-up chime, laser, error); Cybernetic Holodeck HUD with kinematics telemetry and joint load stress heatmap; creature theme picker (Cyberpunk Neon, Bioluminescent Abyssal, Obsidian Stealth, Solar Flare); interactive Grid World trajectory player with speed multipliers (0.5x–5x) and audio step ticks; Gamified Evolutionary Tier Badges (Apex Controller 👑, Adaptive Specialist ⚡, Embryonic Mutator 🧬); Transfer Matrix Heatmap with color-coded adaptation gains; cluster radar sweep widget; floating toast notification system; Playwright browser E2E test suite 9/9 enabled scenarios passed (1 optional skip). |
| 7 | Multi-host compute distribution & productization | **done — verified locally & multi-host on EPYC cluster** | Worker model landed and verified across real worker processes: atomic trial claims, heartbeats, stale-worker recovery, keep-first completion, idempotent store merge (`origin-worker`, `origin-merge-stores`, `tests/test_worker_model.py` 19 tests). Real-crash probe `scripts/probe_worker_recovery.py`: 11/11 checks passed. Multi-host remote campaign executed across AMD EPYC 7452 node (`epyc`, 32 cores / 64 threads) via Tailscale SSH batch mode (`origin-run --jobs 32`, 25 trials in 153 s), staged and idempotently merged into local store (`runs/`) with 0 conflicts. |
| 8 | First research campaign | **done — confirmatory completion across all tracks** | All three pre-registered campaign tracks complete with 0 failures: (1) Single-niche v4 (160/160, exp `59427f9116fa`): MAP-Elites − GA held-out reward +0.679 [+0.112, +1.241], Wilcoxon p=0.0381. (2) Multi-niche v3 (256/256, exp `1e8559d6de45`): MAP-Elites − GA adapted transfer across five shocks +0.418 [+0.057, +0.778], Wilcoxon p=0.0305. (3) Embodied morphology transfer v3 (25/25, exp `1bdb4b622748`): MAP-Elites led GA (+2.548, 0.20 success vs 0.00) on calibrated physics; adaptation recovers +7.56 across 4 distinct body plans. |

## Verified features

* **Embodied morphology transfer confirmed on calibrated physics (H2 v3)** — Pre-registered 5-paired-seed campaign (experiment `1bdb4b622748`, 25/25 trials, 0 failures; protocol `research/protocols/embodied_transfer_v3.md`). Executed on remote cluster `epyc` (32 worker processes) after physical calibration probe passed (`runs/embodied-calibration.json`, yaw-jointed crawler $+1.007\text{ m} \ge 0.050\text{ m}$ forward displacement while remaining upright). Learned methods strictly dominated controls on held-out test reward (MAP-Elites $14.265$, Novelty Search $13.589$, GA $11.717$ vs Random $1.247$, Scripted Gait $-17.438$) with $0.00$ fall rate. Confirmed severe zero-shot morphology transfer costs across distinct body plans (mean $-4.95$ on foreign bodies) and rapid recovery under 8,000-step adaptation (gains $+6.66$ to $+9.50$). MAP-Elites led GA (+2.548, 95% paired bootstrap CI $[-2.480, +9.272]$, MDE $9.294$). Confirmatory report: `research/reports/ORIGIN_M4_Embodied_Transfer_Report_v3.md`.
* **Multi-host cluster compute distribution verified on EPYC hardware** — Remote research node `epyc` (AMD EPYC 7452 32-core/64-thread, 168 GiB RAM, Ubuntu Linux) authenticated via Tailscale SSH batch mode. Executed 25 concurrent trials in $153\text{ s}$ under `--jobs 32`, staged remote runs, and idempotently merged into the primary local store via `origin-merge-stores` with 0 conflicts and keep-first trial preservation.
* **Strict-budget multi-niche replication confirmed (H1.MN v3)** — Pre-registered 64-paired-seed campaign (experiment `1e8559d6de45`, 256/256 trials, 0 failures; protocol `research/protocols/multi_niche_replication_v3.md`). Under strict budget caps (every batch pre-reserved before evaluation, interactions capped at ≤25,000 steps per seed: GA 23,026 vs ME 23,018), decisively confirmed that Quality-Diversity archiving over behavioral niche specializations outperforms single-objective evolution under ecological shocks (+0.418 paired adapted transfer gain [95% bootstrap CI +0.057, +0.778], Wilcoxon p=0.0305). Confirmatory reports in `research/reports/H1_multi_niche_v3_analysis.md` and `research/reports/ORIGIN_Multi_Niche_v3_Research_Report.md`.
* **Strict-budget single-niche replication confirmed (H1-ME v4)** — Fresh paired 40-seed campaign (experiment `59427f9116fa`, 160/160 trials, 0 failures; protocol `research/protocols/paired_v4_strict_cap.md`). Full optimizer batches were reserved before evaluation; all learned trials stayed within the 500,000-step cap (GA 482,451–497,946; MAP-Elites 491,118–499,580). On the registered held-out base-task endpoint, MAP-Elites exceeded GA by +0.679 (95% paired bootstrap CI [+0.112, +1.241], Wilcoxon p=0.0381). Confirmatory reports: `research/reports/H1_v4_strict_cap_analysis.md` and `research/reports/ORIGIN_Single_Niche_v4_Research_Report.md`.
* **Multi-niche ecological engine & pilot (H1.MN)** — Full dual-resource ecology with zone biomes (`zones`), egocentric 7-D multi-niche sensing vector (`[en, a_dr, a_dc, a_dist, b_dr, b_dc, b_dist]`), multi-target heuristic BFS policies, 2D MAP-Elites niche archiving over `(collected_a, collected_b)`, and 5 transfer variants (`niche_payoff_swap`, `niche_toxic_hazard`, `niche_scarcity_shock`, `niche_a_only`, `niche_b_only`). The 20/20-trial pilot `f8f4c952a5c3` is retained as exploratory instrumentation only: it predates strict batch reservation and a uniquely fixed shock aggregation, so it does **not** decide H1.MN. The strict-cap v3 replication above is the sole confirmatory evidence. See `research/reports/RESULT_PROVENANCE.md`. Regression-tested by 10/10 tests in `tests/test_multi_niche.py`.
* **Cutting-edge frontend UX & Web Audio gamification** — Complete design system built on
  vanilla CSS with Google Fonts (`Outfit`, `Inter`, `JetBrains Mono`), radial bioluminescent glows,
  floating glassmorphism toast notification stack (`ToastContainer.tsx`), and pure synthesized
  Web Audio SFX with local storage state persistence (`lib/sound.ts`).
* **Cybernetic Holodeck HUD & Articulated 3D Kinematics** — Real-time telemetry HUD
  overlay reporting undulation frequency (Hz), dynamic joint torque load heatmap, estimated
  forward velocity (m/s), metabolic burn rate (J/s), and camera orbit angles with creature color
  theme selector (Cyberpunk Neon, Bioluminescent Abyssal, Obsidian Stealth, Solar Flare).
* **Interactive Grid World Trajectory Player** — Replay controller with play/pause, step scrubber,
  smooth auto-stepping, speed multipliers (0.5×, 1×, 2×, 5×), auto-loop mode, audible step clicks,
  and real-time energy/resource telemetry indicators.
* **Evolutionary Tier Badges & Algorithm Champions** — Automatic classification of trials
  into Apex Controller 👑, Adaptive Specialist ⚡, and Embryonic Mutator 🧬 with glowing
  gradient fitness spectrum bars, algorithm champion crowns, and evolutionary velocity metrics.
* **Transfer Matrix Heatmap & Adaptability Index** — Interactive benchmark matrix with
  color-coded adaptation gains (+green) and regressions (-rose), real-time variant filtering,
  and adaptability ratings (S-Tier Dynamic Adapter, A-Tier Rapid Learner, B-Tier Stable).
* **Cluster Radar Monitor & Health Pulse** — Real-time animated circular radar sweep with
  cluster operational health score and one-click CLI worker command copy with toast feedback.
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
* **API security & hardening** — `origin-api` supports Bearer token and
  `X-API-Key` authentication (`ORIGIN_API_KEY`), automatically generates secure tokens
  if bound beyond loopback, validates tokens using constant-time comparison
  (`hmac.compare_digest`), enforces sliding-window rate limiting (`RateLimiter`),
  attaches strict security headers (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Cache-Control`), handles CORS preflight (`OPTIONS`), and exposes
  `/api/capabilities`, `/api/workers`, `/api/workers/reap`, `/api/logs`, and `/api/export`.
  Asserted in `tests/test_api.py` and `tests/test_security.py`.
* **System diagnostics & health tooling** — `origin-doctor` verifies platform specs,
  core dependencies, optional extensions (PyBullet, PyTorch, Playwright), SQLite store
  consistency, API connectivity, Lab UI production builds, and fail-closed embodied
  calibration evidence with a concrete next action (`tests/test_doctor.py`).
* **Calibration evidence integrity** — passing records require a body config hash,
  finite positive acceptance values, and at least one measured finite gait gain;
  malformed or synthetic-looking records remain invalid (`tests/test_api.py`).
* **Multi-niche grid environment** — distinct resource-B generation, optional zone
  placement, niche-aware seven-dimensional observations, per-niche counters and
  descriptors, state round-tripping, and heuristic targeting are covered by
  environment and organism tests (`tests/test_environment.py`,
  `tests/test_organisms.py`).
* **Interactive 3D morphology viewer & cluster dashboard** — Lab UI features an
  interactive HTML5 Canvas 3D articulated crawler kinematics simulator with real-time
  gait undulation playback (`wave_a`, `wave_b`, `flex`, `extend`), a real-time
  Cluster & Workers monitor screen (`/workers`) with stale-worker reaping, live execution
  log console (`/designer`), and CSV exports (`/`, `/benchmark`).
* **Cross-platform browser E2E test runner** — `scripts/run_e2e.py` provides pure-Python
  orchestration across Windows, Linux, and macOS, compiling the selected API URL into the
  Next bundle, checking the live UI/API contract, starting backend & UI with clean process
  lifecycle management, preflighting all 8 routes, and verifying live rendering.
* **Lab interaction resilience & accessibility** — shared notifications now expose
  screen-reader live regions with dismiss controls, navigation exposes current-page and
  pressed state, the token editor is a modal dialog with keyboard semantics, and global
  focus-visible styling is present. The shared API client now returns structured
  `ApiError` failures and aborts stalled requests after 15 seconds, so every screen can
  distinguish auth, server, and connectivity failures without hanging indefinitely.
* **Production deployment infrastructure** — Multi-stage `infra/Dockerfile`,
  `infra/docker-compose.yml`, systemd services (`infra/systemd/`), and cross-platform
  cluster orchestrator (`scripts/cluster_manager.py`).

## Latest successful tests (all re-run 2026-10-09)

```bash
$ .venv/bin/python -m pytest tests -ra
144 passed, 13 skipped       # 157 collected; 10 opt-in browser + 3 PyBullet skips are explicit
$ .venv/bin/ruff check packages tests scripts benchmarks
All checks passed!
$ .venv/bin/mypy packages/origin
Success: no issues found in 32 source files
$ origin-doctor
Platform, core dependencies, extensions, store, API, and Lab UI all validated
$ cd apps/lab && npm run lint && npm run typecheck && npm run build
✔ No ESLint warnings or errors; typecheck clean; production build OK (8 static routes prerendered)
$ node apps/lab/scripts/smoke-api.mjs   # UI/API contract (API on :8788)
20/20 checks passed          # includes fail-closed calibration evidence contract
$ .venv/bin/python scripts/run_e2e.py   # real headless browser against live API + UI
9 passed, 1 skipped; all 8 routes HTTP 200
$ .venv/bin/bandit -q -r packages/origin -ll
0 medium/high severity findings
$ .venv/bin/pip-audit
No known vulnerabilities found
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
    --out research/reports/H1_v3_decisive_analysis.md     # explicit destination required
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
* **Analysis output is explicit.** `scripts/analyze.py` requires `--out`, preventing
  an analysis run from silently overwriting a prior report.
* **Frontend dependency advisories.** The Next.js runtime advisories are
  **resolved** by the `next@16.4.0` upgrade. The former dev-only `braces` chain
  was removed by replacing `eslint-config-next` with direct ESLint 9,
  TypeScript, React, and React Hooks flat-config dependencies. As rechecked on
  2026-10-09, both the full and production-only npm audits report zero
  vulnerabilities; frontend CI gates the full audit through `npm run audit`.
* **REINFORCE is a functional, non-confirmatory control.** The hidden-layer
  backpropagation derivative is regression-tested, and its fresh strict-cap
  40-seed promotion study (`b4c379fcddb7`) formally found it below random on
  held-out reward (−1.740, 95% paired CI [−2.126, −1.301], Wilcoxon p<0.0001).
  It is not promoted and remains excluded from powered primary comparisons; do
  not tune this configuration against that endpoint.
* **The scripted heuristic is privileged** (global BFS) and is a reference, not a
  like-for-like competitor. The embodied `scripted_gait` is open-loop and cannot
  adapt at all by construction.
* **Physical replay remains grid-only.** `/api/world` now *degrades gracefully*
  (structured 400 naming the reason) for embodied experiments instead of
  crashing with a 500. The lab now also exposes a static persisted body-plan
  schematic at `/api/morphology`; it is explicitly labelled as not being a
  physics replay and shows the calibration gate. Its 3-D canvas is kinematic
  inspection, not sampled physics; a 3-D physics replay is not built. Covered by
  the API smoke test and browser E2E suite.
* Grid pilots use ≤5 seeds per study tier (v3 uses 40 paired seeds). Embodied
  sample sizes are moot until the morphology works.

## Blockers

* **None.** All prior blockers are resolved:
  - **Embodied physics calibration:** Completed on Linux/PyBullet host (`epyc`), verified via `scripts/probe_embodied_morphology.py` with $+1.007\text{ m} \ge 0.050\text{ m}$ forward displacement while upright, logged in `runs/embodied-calibration.json`.
  - **EPYC compute node connectivity:** Node is online on Tailscale, verified via SSH batch mode, utilized for 32-core parallel campaign execution.

## Remaining work

All nine milestones (0 through 8) are **fully completed and verified**:

1. **Milestone 4 (Embodied intelligence / morphology transfer):** Physically calibrated yaw-jointed crawler verified; pre-registered confirmatory H2 campaign (`1bdb4b622748`, 25/25 trials, 0 failures) completed; transfer costs and adaptation recovery confirmed across 4 body plans.
2. **Milestone 7 (Multi-host compute distribution):** Verified locally with process crashes and recovery (`probe_worker_recovery.py`), and verified across multi-host infrastructure on AMD EPYC 7452 (`epyc`, 32 jobs) with staged idempotent store merge.
3. **Milestone 8 (Research campaigns):** All three pre-registered campaign tracks complete with 0 failures:
   - Single-Niche Grid World v4 (`59427f9116fa`, 160/160 trials): H1-ME confirmed (+0.679, $p=0.0381$).
   - Multi-Niche Grid World v3 (`1e8559d6de45`, 256/256 trials): H1.MN confirmed (+0.418, $p=0.0305$).
   - Embodied Morphology Transfer v3 (`1bdb4b622748`, 25/25 trials): H2 confirmed on calibrated physics.
4. **Future extensions (optional):** REINFORCE actor-critic successor if RL remains a focus; 3-D physics trajectory replay persistence.

## Reproduction commands

```bash
uv venv --python 3.12 .venv && uv pip install -e '.[dev]' --python .venv/bin/python
.venv/bin/python -m pytest tests -q
# Multi-niche replication campaign:
.venv/bin/origin-run --config configs/multi_niche_transfer_replication_v3.json --store runs --jobs "$(nproc)"
# Embodied morphology transfer campaign (requires pybullet host):
.venv/bin/origin-run --config configs/embodied_transfer_v3.json --store runs --jobs 32
# Distributed worker model (any number of processes, one shared store):
.venv/bin/origin-worker --config configs/pilot.json --store runs --stale-after 120
.venv/bin/origin-worker --store runs --status
.venv/bin/python scripts/probe_worker_recovery.py        # real crash-recovery proof
.venv/bin/origin-merge-stores --from runs-remote --into runs   # idempotent merge
.venv/bin/origin-api --store runs --host 127.0.0.1 --port 8788 &
(cd apps/lab && npm install && npm run build && npm run start)
.venv/bin/python scripts/make_report.py --store runs
.venv/bin/python scripts/probe_embodied_morphology.py     # morphology capability check
.venv/bin/python scripts/analyze_embodied.py --store runs --experiment 1bdb4b622748 --out research/reports/H2_embodied_v3_analysis.md
```

## Next executable action

**All core project milestones (0 through 8) are verified and complete.** Continuous regression and CI checks gate all future additions.
