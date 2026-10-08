# Experiment Protocol

This document defines how ORIGIN experiments are designed, executed and reported,
so that results are comparable and falsifiable.

## 1. Hypothesis first

Every experiment names a falsifiable hypothesis (see `research/hypotheses/`). A
protocol that cannot be refuted is not run.

## 2. Controls

Each comparison includes, at minimum:

* a **random** policy control,
* a **scripted heuristic** control (privileged, so it is an upper reference, not
  a competitor to be beaten blindly).

## 3. Equal budgets

All learning/evolutionary methods run under the same **interaction budget**
(environment `step` calls), recorded exactly. Compute differences (wall time) are
reported explicitly but are not the optimisation target.

## 4. Seeds

* Training uses `train_seeds`; evaluation uses disjoint `test_seeds`.
* Each method is run across multiple **independent** `seeds` (RNG seeds).
* Reported metrics are means across seeds with dispersion reported; confidence
  intervals are given when the number of seeds supports them.

## 5. Held-out evaluation

Test environments are generated from held-out seeds and never used for tuning.
Transfer is measured on:

* **morphology variants** — sensor fidelity, actuation and body changes;
* **perturbation variants** — obstacles, resource scarcity, hazard density,
  terrain structure, actuarial cost.

For morphology variants we distinguish:

* **zero-shot** transfer (no further training),
* **adapted** performance after a fixed adaptation budget,
* **adaptation gain** = adapted − zero-shot.

## 6. Failure handling

* A failed trial is stored with status `failed` and its error. Benchmark
  summaries report failures; they are never silently dropped.
* A crashed worker leaves a `running` row that `--resume` re-attempts.

## 7. Reporting rules

* Raw metrics, baseline comparison tables, training curves, transfer plots,
  compute-cost summaries and reproduction commands are produced together.
* No metric is reported unless it comes from stored trial artifacts.
* Negative and null results are reported with the same prominence as positive
  ones. Do not force a positive outcome.
* If sample size or compute prevents reliable inference, the experiment is
  explicitly labelled **preliminary**.

## 8. Artifacts per experiment

| Artifact | Path |
|---|---|
| Config manifest | `runs/<id>/manifest.json` |
| Trial metrics | SQLite `trials` table |
| Training history | `runs/<id>/<trial>.jsonl` |
| Winning genomes | `runs/<id>/<trial>.organism.json` |
| Tables | `runs/<id>/trials.csv`, `trials.parquet` |
| Plots | `runs/<id>/plots/*.png` |
| Summary | `runs/<id>/summary.json` |
