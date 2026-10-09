#!/usr/bin/env python3
"""Fail-closed analysis for the registered PPO Actor-Critic v2 studies.

The v1 grid campaign is deliberately rejected: its executed configuration did
not match its registration and is retained only as an exploratory implementation
artifact.  Every v2 analysis must name the immutable configuration it verifies.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from origin.evaluation.stats import min_detectable_effect, paired_bootstrap_ci, wilcoxon_signed_rank
from origin.experiments.runner import experiment_id
from origin.experiments.store import Store

RESAMPLES = 10_000


def _load_config(path: str | Path) -> dict[str, Any]:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if config.get("name") in {"actor_critic_grid_v1", "actor_critic_embodied_v1"}:
        raise ValueError(
            "Actor-Critic v1 is exploratory because its executed configuration "
            "did not match its registration; see ACTOR_CRITIC_V1_CONFIGURATION_AUDIT.md"
        )
    primary = config.get("primary_comparison")
    if not isinstance(primary, dict):
        raise ValueError("registered config must contain primary_comparison")
    if primary.get("method") != "ppo":
        raise ValueError("Actor-Critic v2 primary method must be 'ppo'")
    if primary.get("baseline") not in {"reinforce", "random"}:
        raise ValueError("Actor-Critic v2 baseline must be 'reinforce' or 'random'")
    if primary.get("endpoint") != "test_mean_reward":
        raise ValueError("Actor-Critic v2 endpoint must be test_mean_reward")
    return config


def _held_out_by_seed(store: Store, exp_id: str) -> tuple[dict[str, dict[int, float]], list[dict[str, Any]]]:
    values: dict[str, dict[int, float]] = {}
    done: list[dict[str, Any]] = []
    for trial in store.trials(exp_id):
        if trial["status"] != "done":
            continue
        done.append(trial)
        metrics = json.loads(trial["metrics_json"]) if trial.get("metrics_json") else {}
        score = metrics.get("test_mean_reward")
        if score is not None:
            values.setdefault(trial["algorithm"], {})[int(trial["seed"])] = float(score)
    return values, done


def _require_registered_matrix(
    by_seed: dict[str, dict[int, float]],
    done: list[dict[str, Any]],
    config: dict[str, Any],
) -> tuple[list[int], str, str]:
    primary = config["primary_comparison"]
    method = str(primary["method"])
    baseline = str(primary["baseline"])
    expected = [int(seed) for seed in config["seeds"]]
    if len(expected) != len(set(expected)):
        raise ValueError("registered method seeds must be unique")

    problems: list[str] = []
    for algorithm in (method, baseline):
        observed = by_seed.get(algorithm, {})
        missing = sorted(set(expected) - set(observed))
        unexpected = sorted(set(observed) - set(expected))
        nonfinite = sorted(seed for seed, value in observed.items() if not math.isfinite(value))
        if missing:
            problems.append(f"{algorithm}: missing seeds {missing}")
        if unexpected:
            problems.append(f"{algorithm}: unexpected seeds {unexpected}")
        if nonfinite:
            problems.append(f"{algorithm}: non-finite held-out scores for {nonfinite}")

    cap = int(config["budget"])
    for algorithm in config["algorithms"]:
        over_cap = sorted(
            int(trial["seed"])
            for trial in done
            if trial["algorithm"] == algorithm and int(trial["interactions"]) > cap
        )
        if over_cap:
            problems.append(f"{algorithm}: training cap {cap} exceeded for seeds {over_cap}")
    if problems:
        raise ValueError("incomplete or invalid Actor-Critic analysis: " + "; ".join(problems))
    return sorted(expected), method, baseline


def analyze_actor_critic(store_root: str, config_path: str | Path, exp_id: str | None = None) -> dict[str, Any]:
    """Analyze one exact registered v2 campaign or fail before inference."""
    config = _load_config(config_path)
    expected_id = experiment_id(config)
    exp_id = exp_id or expected_id
    if exp_id != expected_id:
        raise ValueError(
            f"experiment {exp_id} does not match the registered configuration; expected {expected_id}"
        )

    store = Store(store_root)
    experiment = store.experiment(exp_id)
    if experiment is None:
        raise FileNotFoundError(f"registered experiment {exp_id} not found in store")
    stored_config = json.loads(experiment["config_json"])
    if stored_config != config:
        raise ValueError("stored experiment configuration differs from the registered JSON")

    by_seed, done = _held_out_by_seed(store, exp_id)
    seeds, method, baseline = _require_registered_matrix(by_seed, done, config)
    method_values = [by_seed[method][seed] for seed in seeds]
    baseline_values = [by_seed[baseline][seed] for seed in seeds]
    bootstrap_seed = int(config["primary_comparison"]["bootstrap_seed"])
    result = paired_bootstrap_ci(method_values, baseline_values, resamples=RESAMPLES, seed=bootstrap_seed)
    statistic, p_value = wilcoxon_signed_rank(method_values, baseline_values)
    diffs = [method_value - baseline_value for method_value, baseline_value in zip(method_values, baseline_values, strict=True)]
    mde = min_detectable_effect(diffs, n=len(diffs))

    return {
        "experiment_id": exp_id,
        "config": str(config_path),
        "n_seeds": len(seeds),
        "shared_seeds": seeds,
        "method": method,
        "baseline": baseline,
        "method_mean": float(sum(method_values) / len(method_values)),
        "baseline_mean": float(sum(baseline_values) / len(baseline_values)),
        "training_budget": int(config["budget"]),
        "comparison": {
            "mean_diff": result.point,
            "bootstrap_ci_95": [result.lo, result.hi],
            "wilcoxon": {"statistic": statistic, "p_value": p_value},
            "minimum_detectable_effect": mde,
            "decision": result.verdict,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze a registered Actor-Critic PPO v2 campaign.")
    parser.add_argument("--store", default="runs", help="Store directory")
    parser.add_argument("--config", required=True, help="Immutable v2 registration JSON")
    parser.add_argument("--experiment", default=None, help="Experiment ID; defaults to the config-derived ID")
    args = parser.parse_args()

    try:
        report = analyze_actor_critic(args.store, args.config, args.experiment)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
