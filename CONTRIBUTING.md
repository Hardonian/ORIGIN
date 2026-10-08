# Contributing to ORIGIN

Thank you for helping make ORIGIN a trustworthy research instrument. Because the
platform's value is *reproducible evidence*, the bar for honesty is higher than
the bar for speed.

## Principles

1. **Never report an unverified metric.** If a number appears in a report, it
   must be traceable to a stored trial artifact.
2. **A check that did not run must never report as passed.** Distinguish
   "skipped" from "passed" explicitly.
3. **No fabricated results, capabilities or deployment state.**
4. **Keep the control interface stable.** The controller input dimension is fixed
   across morphologies; morphology changes sensor fidelity, actuation and body,
   not the interface. Changing this breaks transfer comparability.
5. **Fix root causes, not symptoms.**

## Development

```bash
uv venv --python 3.12 .venv
uv pip install -e ".[dev]" --python .venv/bin/python
.venv/bin/python -m pytest -q
.venv/bin/ruff check packages tests scripts
.venv/bin/mypy
```

## Adding an algorithm

* Implement it under `packages/origin/evolution` or `.../learning`.
* Return an `OptimizationResult` and consume a shared `Evaluator` so that
  interaction budgets remain comparable.
* Register it in `origin.experiments.runner.ALGORITHMS` and add default kwargs.
* Add tests proving (a) it runs, (b) it is deterministic given a seed, and
  (c) its budget accounting is correct.
* Document its hyperparameters and citation in `research/baselines/`.

## Pull requests

* Keep scientific benchmarks out of routine PR CI; add a small deterministic
  fixture instead.
* Never weaken a test to make CI green. Fix the defect.
* Include the exact commands you ran and their results in the PR description.

## Commit style

Short imperative subject; a body explaining *why*, the commands run, and the
rollback path when relevant.
