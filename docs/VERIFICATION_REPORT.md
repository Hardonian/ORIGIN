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
64 passed, 6 skipped        # the 6 skipped are the browser E2E tests (opt-in)

$ scripts/e2e_lab.sh        # starts API + production UI, runs the browser E2E, tears down
6 passed
```

70 tests collected in total: 64 unit/integration (always run) + 6 browser E2E
(require `ORIGIN_E2E=1` and running servers; invoked by `scripts/e2e_lab.sh`).

Breakdown: `test_environment.py` (21), `test_organisms.py` (9), `test_evolution.py`
(5), `test_evaluation.py` (6), `test_experiments.py` (11), `test_security.py` (5),
`test_stats.py` (7), `e2e/test_lab_e2e.py` (6, opt-in).

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

## Replication, paired design, and cross-experiment determinism

Two pre-registered studies followed the exploratory pilot, each with its analysis
fixed before the run (`research/protocols/powered_replication.md`,
`research/protocols/paired_v2.md`). Study 1's registration forbade re-analysis, so
it was **not** re-tested; study v2 is a separate prospective study on fresh seeds.

Cross-experiment determinism (pilot vs study 1 — 30 overlapping (method, seed) pairs):

```
30 overlapping (method, seed) pairs reproduced across the two independent
experiments with 0 mismatches   (exact to 6 decimal places)
```

Held-out outcomes:

| study | seeds | design | comparison | mean diff | 95% CI | p | verdict |
|---|---|---|---|---|---|---|---|
| 1 | 1–10 | independent | novelty − GA | −0.228 | [−1.427, +0.998] | 0.5423 | **inconclusive** |
| 1 | 1–10 | independent | QD − GA | −0.038 | [−0.972, +0.965] | 0.6219 | **inconclusive** |
| v2 | 11–20 | paired | novelty − GA | +0.331 | [−0.932, +1.549] | 0.5566 | **inconclusive** |
| v2 | 11–20 | paired | QD − GA | +0.790 | [−0.161, +1.645] | 0.2031 | **inconclusive** |
| v3 | 21–60 (n=40) | paired, power-sized | QD − GA | −0.221 | [−0.721, +0.262] | 0.5377 | **inconclusive — BOUNDED NULL** |

The pilot's +0.362 direction for novelty search **did not replicate** in study 1
(−0.228), swung positive in study v2 (+0.331), and the v2 MAP-Elites hint (+0.790)
did not replicate either — study v3 found −0.221 at n=40. The sign is unstable and
every registered 95% CI spans zero.

**Study v3 makes the null bounded.** It was power-sized *before* running (n=40, from
a study-v2 power analysis requiring 31.5) and scoped to the only comparison with
feasible power (the same analysis showed `novelty_search` needs n ≈ 321). At n=40 the
design could detect a paired effect of **≥ 0.708** at 80% power; the observed
difference was −0.221. The correct statement is therefore: **on this task any
MAP-Elites advantage is smaller than ≈0.71 reward units**, not "there is no effect".

This is a bounded null for the project's own primary hypothesis, reported as such.

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
* **Statistical power:** three pre-registered studies with interval analyses
  (independent in study 1; paired in studies v2 and v3 — paired is the efficient
  design because all methods share identical training environments). Study v3 was
  **sized from a power analysis before running**, and its inconclusive result is
  reported as a *bounded* null (effect < ≈0.71) rather than as "not proven".
* **Scoping decided on power grounds, stated in advance.** Study v3 dropped
  `novelty_search` because it needs n ≈ 321; that exclusion is declared in its
  protocol before the run, so it cannot be read as selective reporting.
* **A paired design was adopted for study v2 without touching study 1's data.**
  Study 1's registration stated that no other test would be run on it, so it was
  left alone rather than re-analysed to chase significance.
* **Two exploratory positive directions did not replicate** (novelty +0.362 at n=5
  → −0.228 at n=10; MAP-Elites +0.790 at n=10 → −0.221 at n=40). Reported
  prominently rather than quietly dropped.

## Honest limitations

* H1 is **not established**, and the null is **bounded**: across the pilot, study 1
  (unpaired), study v2 (paired) and study v3 (paired, n=40), point estimates change
  sign and study v3's design bounds any MAP-Elites advantage below ≈0.71.
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
