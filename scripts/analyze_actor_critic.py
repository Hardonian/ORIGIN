"""Statistical analysis for the pre-registered Actor-Critic (PPO) benchmark.

Performs paired bootstrap and Wilcoxon tests per research/protocols/actor_critic_v1.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def analyze_actor_critic(store_root: str, exp_id: str | None = None) -> dict:
    from origin.experiments.store import Store

    store = Store(store_root)
    if exp_id is None:
        # Find experiment by name
        for exp in store.list_experiments():
            if exp["name"] == "actor_critic_grid_v1":
                exp_id = exp["id"]
                break
    if exp_id is None:
        raise FileNotFoundError("actor_critic_grid_v1 experiment not found in store")

    trials = store.trials(exp_id)
    done_trials = [t for t in trials if t["status"] == "done"]
    if not done_trials:
        raise ValueError(f"no completed trials in experiment {exp_id}")

    # Group by algorithm and seed
    results: dict[str, dict[int, float]] = {}
    for t in done_trials:
        algo = t["algorithm"]
        seed = int(t["seed"])
        metrics = json.loads(t["metrics_json"] or "{}")
        test_r = metrics.get("test_mean_reward")
        if test_r is not None:
            results.setdefault(algo, {})[seed] = float(test_r)

    ppo_scores = results.get("ppo", {})
    rf_scores = results.get("reinforce", {})
    rnd_scores = results.get("random", {})

    shared_seeds = sorted(set(ppo_scores.keys()) & set(rf_scores.keys()) & set(rnd_scores.keys()))
    if not shared_seeds:
        raise ValueError("no overlapping seeds across PPO, REINFORCE, and random")

    ppo_arr = np.array([ppo_scores[s] for s in shared_seeds])
    rf_arr = np.array([rf_scores[s] for s in shared_seeds])
    rnd_arr = np.array([rnd_scores[s] for s in shared_seeds])

    diff_ppo_rf = ppo_arr - rf_arr
    diff_ppo_rnd = ppo_arr - rnd_arr

    # Bootstrap 95% CI (10,000 resamples, seed 20261018)
    rng = np.random.default_rng(20261018)
    n = len(shared_seeds)
    boot_rf = [float(np.mean(rng.choice(diff_ppo_rf, size=n, replace=True))) for _ in range(10000)]
    ci_rf = [float(np.percentile(boot_rf, 2.5)), float(np.percentile(boot_rf, 97.5))]

    boot_rnd = [float(np.mean(rng.choice(diff_ppo_rnd, size=n, replace=True))) for _ in range(10000)]
    ci_rnd = [float(np.percentile(boot_rnd, 2.5)), float(np.percentile(boot_rnd, 97.5))]

    # Wilcoxon test if scipy is available
    try:
        from scipy.stats import wilcoxon

        stat_rf, p_rf = wilcoxon(diff_ppo_rf)
        p_val_rf = float(p_rf)
    except Exception:
        p_val_rf = None

    try:
        from scipy.stats import wilcoxon

        stat_rnd, p_rnd = wilcoxon(diff_ppo_rnd)
        p_val_rnd = float(p_rnd)
    except Exception:
        p_val_rnd = None

    h_ac1_supported = bool(ci_rf[0] > 0 and float(np.mean(diff_ppo_rf)) > 0)

    report = {
        "experiment_id": exp_id,
        "n_seeds": n,
        "shared_seeds": shared_seeds,
        "ppo_mean": float(np.mean(ppo_arr)),
        "reinforce_mean": float(np.mean(rf_arr)),
        "random_mean": float(np.mean(rnd_arr)),
        "ppo_vs_reinforce": {
            "mean_diff": float(np.mean(diff_ppo_rf)),
            "std_diff": float(np.std(diff_ppo_rf, ddof=1)),
            "bootstrap_ci_95": ci_rf,
            "wilcoxon_p": p_val_rf,
            "decision": "SUPPORTED" if h_ac1_supported else "INCONCLUSIVE",
        },
        "ppo_vs_random": {
            "mean_diff": float(np.mean(diff_ppo_rnd)),
            "std_diff": float(np.std(diff_ppo_rnd, ddof=1)),
            "bootstrap_ci_95": ci_rnd,
            "wilcoxon_p": p_val_rnd,
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Actor-Critic benchmark results.")
    parser.add_argument("--store", default="runs", help="Store directory")
    parser.add_argument("--experiment", default=None, help="Experiment ID (optional)")
    args = parser.parse_args()

    rep = analyze_actor_critic(args.store, args.experiment)
    print(json.dumps(rep, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
