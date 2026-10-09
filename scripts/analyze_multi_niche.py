#!/usr/bin/env python3
"""Fail-closed registered analysis for multi-niche transfer campaigns.

The unit of inference is one independently seeded training run.  Transfer
variants are averaged *within* that run before algorithms are compared, so the
five shocks cannot accidentally be treated as five independent observations.

Usage:
    python scripts/analyze_multi_niche.py --store runs --experiment <id> \
        --protocol-doc research/protocols/multi_niche_replication_v2.md \
        --bootstrap-seed 20261014 --out research/reports/H1_multi_niche_v2_analysis.md
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np

from origin.evaluation.stats import min_detectable_effect, paired_bootstrap_ci, wilcoxon_signed_rank
from origin.experiments.store import Store

BOOTSTRAP_RESAMPLES = 10_000
PRIMARY_METHOD = "map_elites"
COMPARATOR = "fixed_objective_ga"
NICHE_VARIANTS = (
    "niche_payoff_swap",
    "niche_toxic_hazard",
    "niche_scarcity_shock",
    "niche_a_only",
    "niche_b_only",
)
ENDPOINTS = ("zero_shot_mean_reward", "adapted_mean_reward", "adaptation_gain")


def transfer_values_by_seed(
    store: Store,
    experiment_id: str,
    *,
    endpoint: str,
    methods: tuple[str, ...] = (PRIMARY_METHOD, COMPARATOR),
    variants: tuple[str, ...] = NICHE_VARIANTS,
) -> dict[str, dict[int, dict[str, float]]]:
    """Return required per-variant endpoint values, rejecting incomplete data.

    A report must never silently omit a seed, shock, failed trial, or non-finite
    endpoint.  Those cases are a data-quality problem, not a smaller sample.
    """
    if endpoint not in ENDPOINTS:
        raise ValueError(f"unknown endpoint {endpoint!r}; expected one of {ENDPOINTS}")

    experiment = next((e for e in store.list_experiments() if e["id"] == experiment_id), None)
    if experiment is None:
        raise ValueError(f"unknown experiment {experiment_id}")
    cfg = json.loads(experiment["config_json"])
    expected_seeds = {int(seed) for seed in cfg.get("seeds", [])}
    if not expected_seeds:
        raise ValueError("experiment config has no registered method seeds")

    out: dict[str, dict[int, dict[str, float]]] = {method: {} for method in methods}
    for trial in store.trials(experiment_id):
        method = str(trial["algorithm"])
        if method not in out:
            continue
        seed = int(trial["seed"])
        if trial["status"] != "done":
            raise ValueError(f"{method} seed {seed} is {trial['status']}, not done")
        raw = trial.get("transfer_json")
        if not raw:
            raise ValueError(f"{method} seed {seed} has no transfer record")
        transfer = json.loads(raw)
        per_variant: dict[str, float] = {}
        for variant in variants:
            entry = transfer.get(variant)
            if not isinstance(entry, dict):
                raise ValueError(f"{method} seed {seed} is missing transfer variant {variant!r}")
            if "error" in entry:
                raise ValueError(f"{method} seed {seed} {variant} failed: {entry['error']}")
            value = entry.get(endpoint)
            if value is None:
                raise ValueError(f"{method} seed {seed} {variant} has no {endpoint}")
            value = float(value)
            if not math.isfinite(value):
                raise ValueError(f"{method} seed {seed} {variant} has non-finite {endpoint}")
            per_variant[variant] = value
        if seed in out[method]:
            raise ValueError(f"duplicate result for {method} seed {seed}")
        out[method][seed] = per_variant

    for method, by_seed in out.items():
        observed = set(by_seed)
        if observed != expected_seeds:
            missing = sorted(expected_seeds - observed)
            extra = sorted(observed - expected_seeds)
            raise ValueError(f"{method} registered seeds incomplete (missing={missing}, extra={extra})")
    return out


def aggregate_by_seed(values: dict[int, dict[str, float]], variants: tuple[str, ...] = NICHE_VARIANTS) -> dict[int, float]:
    """Mean the fixed shock set within each independent method seed."""
    return {seed: float(np.mean([per_variant[variant] for variant in variants])) for seed, per_variant in values.items()}


def _format_table_row(values: list[float]) -> str:
    arr = np.asarray(values, dtype=float)
    sd = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
    return f"{len(arr)} | {arr.mean():+.3f} | {sd:.3f} | {arr.min():+.3f} | {arr.max():+.3f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", default="runs")
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--endpoint", choices=ENDPOINTS, default="adapted_mean_reward")
    parser.add_argument("--bootstrap-seed", type=int, required=True)
    parser.add_argument("--protocol-doc", required=True)
    parser.add_argument("--out", required=True, help="explicit Markdown destination; existing files are not overwritten")
    args = parser.parse_args()

    out_path = Path(args.out)
    if out_path.exists():
        raise SystemExit(f"refusing to overwrite existing analysis: {out_path}")

    store = Store(args.store)
    experiment = next((e for e in store.list_experiments() if e["id"] == args.experiment), None)
    if experiment is None:
        raise SystemExit(f"unknown experiment {args.experiment}")
    cfg: dict[str, Any] = json.loads(experiment["config_json"])
    raw = transfer_values_by_seed(store, args.experiment, endpoint=args.endpoint)
    primary = aggregate_by_seed(raw[PRIMARY_METHOD])
    comparator = aggregate_by_seed(raw[COMPARATOR])
    seeds = sorted(primary)
    primary_values = [primary[seed] for seed in seeds]
    comparator_values = [comparator[seed] for seed in seeds]
    differences = [a - b for a, b in zip(primary_values, comparator_values, strict=True)]
    result = paired_bootstrap_ci(
        primary_values, comparator_values, resamples=BOOTSTRAP_RESAMPLES, seed=args.bootstrap_seed
    )
    statistic, p_value = wilcoxon_signed_rank(primary_values, comparator_values)
    mde = min_detectable_effect(differences, n=len(differences))

    lines: list[str] = []
    add = lines.append
    add("# H1.MN — Pre-registered multi-niche transfer analysis")
    add("")
    add(
        f"Experiment `{args.experiment}` · protocol `{cfg.get('protocol')}` · "
        f"{len(seeds)} paired method seeds · budget {int(cfg['budget']):,} interactions/method/seed."
    )
    add("")
    add(
        f"Analysis fixed in advance at `{args.protocol_doc}`. The endpoint is each seed's arithmetic "
        f"mean of `{args.endpoint}` over the five registered niche shocks; shocks are **not** independent samples."
    )
    add("")
    add("## Endpoint completeness")
    add("")
    add(f"All {len(seeds)} registered seeds were present and finite for both methods and all five shocks: "
        + ", ".join(f"`{variant}`" for variant in NICHE_VARIANTS)
        + ".")
    add("")
    add("## Descriptive primary endpoint")
    add("")
    add("| method | n | mean | sd | min | max |")
    add("| --- | --- | --- | --- | --- | --- |")
    add(f"| `{PRIMARY_METHOD}` | {_format_table_row(primary_values)} |")
    add(f"| `{COMPARATOR}` | {_format_table_row(comparator_values)} |")
    add("")
    add("## Registered primary comparison")
    add("")
    add("| comparison | mean paired diff | 95% paired bootstrap CI | CI excludes 0? | Wilcoxon p | verdict |")
    add("| --- | --- | --- | --- | --- | --- |")
    add(
        f"| `{PRIMARY_METHOD}` − `{COMPARATOR}` | {result.point:+.3f} | "
        f"[{result.lo:+.3f}, {result.hi:+.3f}] | {'yes' if result.excludes_zero else 'no'} | "
        f"{p_value:.4f} (W={statistic:.1f}) | **{result.verdict}** |"
    )
    add("")
    add(
        f"Paired bootstrap: {BOOTSTRAP_RESAMPLES:,} resamples, fixed RNG seed `{args.bootstrap_seed}`. "
        "The confidence interval is the registered decision rule; Wilcoxon is reported as a concordance check."
    )
    add("")
    add("## Per-shock descriptive values")
    add("")
    add("| shock | MAP-Elites mean | fixed-objective GA mean | paired diff |")
    add("| --- | --- | --- | --- |")
    for variant in NICHE_VARIANTS:
        map_values = [raw[PRIMARY_METHOD][seed][variant] for seed in seeds]
        ga_values = [raw[COMPARATOR][seed][variant] for seed in seeds]
        add(
            f"| `{variant}` | {np.mean(map_values):+.3f} | {np.mean(ga_values):+.3f} | "
            f"{np.mean(np.asarray(map_values) - np.asarray(ga_values)):+.3f} |"
        )
    add("")
    add("## Bounded-null context")
    add("")
    add(
        f"At n={len(seeds)}, the normal-approximation minimum detectable paired effect at 80% power "
        f"and α=0.05 (two-sided) is {mde:.3f}; observed |mean difference| is {abs(result.point):.3f}."
    )
    add("")
    add("A confidence interval spanning zero is reported as inconclusive, not as evidence for equivalence.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n[analyze-multi-niche] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
