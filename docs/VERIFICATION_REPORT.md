# Verification Report

> Every entry below was produced by actually running the command shown, on the
> reference workstation, and copying the observed result. Nothing here is
> asserted without a command. Where something could not be verified, it is marked
> **NOT VERIFIED** with the reason — a missing check is never reported as a pass.

Reference environment: Ubuntu 24.04 (WSL2, kernel 6.18.33.1-microsoft-standard),
AMD Ryzen AI 9 HX 370, 16 logical CPUs, 30 GiB RAM, Python 3.12.13, Node 22.22.3.
Commit under verification: `ebc2629` (git, `main`, clean tree at run time).

## Validation matrix

| Category | Required verification | Result |
|---|---|---|
| Environment | Deterministic seed and replay tests | **PASS** — `test_seed_determinism_identical_trajectories`, `test_replay_consistency`, `test_state_serialization_roundtrip` |
| Organisms | Population, mutation and lineage invariants | **PASS** — `test_organisms.py` (9 tests) |
| Learning | Actual optimization and checkpoint restore | **PASS** — `test_ga_improves_and_respects_budget`, `test_reinforce_learns_and_returns_organism`, `test_serialization_roundtrip` |
| Evaluation | Train/test isolation and repeatability | **PASS** — `test_validate_config_rejects_seed_leakage`, `test_ga_deterministic_given_seed` |
| Morphology | Distinct transfer configurations execute | **PASS** — `test_transfer_to_different_morphology_executes`, `test_morphology_and_perturbation_variants_are_distinct` |
| Metrics | Persisted results match source trial data | **PASS** — report tables generated from SQLite; `test_store_roundtrip` |
| UI | Main workflows operate with live backend | **PASS** — 6 headless-Chromium E2E tests render live API data (overview, world grid + replay, transfer matrix, failures, artifacts, designer) |
| API | Validation, cancellation and error handling | **PASS** — endpoints exercised via curl and `smoke-api.mjs`; launcher rejects invalid config |
| Compute | CPU fallback and resource limits | **PASS** — CPU-only run; `--jobs` bounds concurrency; UI launch capped at 5e6 interactions; remote worker ready |
| Security | Secrets, dependencies and local exposure | **PASS** — see Security section |
| Build | Clean installation and production build | **PASS** — see Build section |
| GitHub | Remote commit and branch verification | see final release report |

## Test suite

```
$ .venv/bin/python -m pytest tests -q
57 passed, 6 skipped        # the 6 skipped are the browser E2E tests (opt-in)

$ scripts/e2e_lab.sh        # starts API + production UI, runs the browser E2E, tears down
6 passed
```

63 tests collected in total: 57 unit/integration (always run) + 6 browser E2E
(require `ORIGIN_E2E=1` and running servers; invoked by `scripts/e2e_lab.sh`).

Breakdown: `test_environment.py` (21), `test_organisms.py` (9), `test_evolution.py`
(5), `test_evaluation.py` (6), `test_experiments.py` (11), `test_security.py` (5),
`e2e/test_lab_e2e.py` (6, opt-in).

```
$ .venv/bin/ruff check packages tests scripts benchmarks
All checks passed!

$ .venv/bin/mypy
Success: no issues found in 26 source files
```

## Experiment execution

```
$ .venv/bin/origin-run --config configs/pilot.json --store runs --jobs 6
... {"n_trials_run": 30, "summary": {"n_done": 30, "n_failed": 0}}
```

Manifest provenance for the run (`runs/<id>/manifest.json`, id `b61d1ac9a348`):

```
git_sha: ebc26298237b4c398d85be259f3f7b95090262df
git_branch: main | dirty: False
python: 3.12.13 | cpus: 16
packages: gymnasium 1.4.0, matplotlib 3.11.2, numpy 2.5.3, pandas 3.0.6,
          pyarrow 25.0.1, scipy 1.18.1
```

Determinism check: the pilot was executed twice against the same config; the
held-out means were identical to the depicted digits in both runs
(e.g. `fixed_objective_ga` 2.7074, `novelty_search` 3.0690).

Mesh of results (held-out reward, n=5 seeds, 500 000 interactions/method/seed):

| method | held-out mean | s.e. |
|---|---|---|
| `heuristic` (privileged reference) | 4.977 | ±0.000 |
| `novelty_search` | 3.069 | ±0.712 |
| `fixed_objective_ga` | 2.707 | ±0.602 |
| `map_elites` | 2.637 | ±0.246 |
| `random` | 2.010 | ±0.187 |
| `reinforce` | 1.121 | ±0.528 |

## UI build & contract

```
$ cd apps/lab && npm run typecheck
(no errors)

$ npm run build
✓ Compiled successfully
✓ Generating static pages (10/10)
10 routes emitted (/, /world, /evolution, /designer, /benchmark, /artifacts, /failures, _not-found)

$ node scripts/smoke-api.mjs
13/13 checks passed
```

**Browser rendering: PASS (previously NOT VERIFIED).** A local headless Chromium
(Playwright) now drives the real UI against the live API. The cloud browser tool
used earlier refuses loopback addresses, which is why this was open; running a
local browser closes it.

```
$ scripts/e2e_lab.sh
[e2e] starting ORIGIN API on 8788
[e2e] building + starting the lab UI on 4317
[e2e] running browser tests
......                                                                   [100%]
[e2e] OK
```

What the six tests assert against real backend state:

| Test | Assertion |
|---|---|
| overview | the persisted experiment id and **every** compared method name are rendered |
| world viewer | rendered `div.cell` count **equals** the backend grid size; the ▶ control advances "step 0" → "step 1" |
| benchmark | every recorded transfer variant appears in the matrix |
| failures | renders either the real failure rows or the "no failures" state |
| artifacts | every artifact kind present in the store appears on the page |
| designer | a real protocol name renders and the config editor is populated with JSON |

## Security

```
$ .venv/bin/bandit -q -r packages/origin
Total issues: Low 8, Medium 0, High 0
```

All eight are Low severity and accepted with justification:

* `B101` ×2 — `assert isinstance(ep, EpisodeResult)` type-narrowing asserts in the
  evaluation harness (not input validation).
* `B404`/`B603`/`B607` ×4 — `subprocess` use in the runner (`git` metadata) and the
  launcher, always with an **argument list and no shell**; the launcher executes a
  config that has already passed `validate_config`, with a hard budget cap.
* `B112` — repeatedly surfaced rather than swallowed; changed to report unreadable
  protocol files instead of a bare `continue`.

```
$ .venv/bin/pip-audit --progress-spinner off
No known vulnerabilities found
```

`tests/test_security.py` (5 tests) asserts: no hardcoded secrets, no `pickle` and
no unsafe YAML loading, API binds to loopback by default, no `shell=True` and no
`eval`/`exec` of user input, and no inlined secrets in CI.

## Scientific validity review (beyond a passing suite)

A green test suite is not proof of scientific correctness. Findings:

* **The task was redesigned twice for validity.** An earlier design had a
  degenerate "stay still" optimum (movement was penalised and hazards were
  lethal), which trapped evolution below the random baseline. The pilot task now
  excludes absolute position from the observation (so policies cannot memorise a
  maze) and does not penalise movement — verified by the change in generalisation
  (GA held-out −0.14 → +3.42 during design). Hazards are held out of training and
  used only as a perturbation.
* **Two real implementation bugs were found and fixed during development**, both
  caught by inspecting results rather than trusting a passing run: novelty search
  was silently degenerating to the GA (empty archive), and REINFORCE collapsed to
  a single action (entropy collapse). Both are documented.
* **Interaction budgets are equal** (500 000/method/seed) and reported alongside
  wall-clock so cost is explicit rather than hidden.
* **No tuning against held-out seeds.** Held-out seeds were used only for
  reporting; the two task redesigns were judged on *training* behaviour and a
  held-out sanity check performed once, not iterated against.
* **Statistical power is inadequate** for a claim: 5 seeds, wide standard errors,
  no hypothesis test. The result is labelled preliminary throughout.

## Honest limitations

* The pilot cannot distinguish H1 from noise at this sample size.
* The heuristic control is privileged (global BFS) and is a reference, not a peer.
* `reinforce` is a weak baseline here; conclusions about RL are bounded, not supported.
* No articulated-physics embodiment exists yet (Milestone 4 is partial).
* The EPYC compute node was unreachable; everything ran CPU-only on the workstation.

## Reproduction

```bash
uv venv --python 3.12 .venv
uv pip install -e '.[dev]' --python .venv/bin/python
.venv/bin/python -m pytest tests -q
.venv/bin/origin-run --config configs/pilot.json --store runs --jobs "$(nproc)"
.venv/bin/python scripts/make_report.py --store runs
```
