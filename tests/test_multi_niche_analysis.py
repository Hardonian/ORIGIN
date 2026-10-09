"""Regression guards for the fail-closed multi-niche transfer analysis."""

import pytest
from scripts.analyze_multi_niche import (
    NICHE_VARIANTS,
    aggregate_by_seed,
    transfer_values_by_seed,
)

from origin.experiments.store import Store


def _record_trial(
    store: Store,
    *,
    trial_id: str,
    algorithm: str,
    seed: int,
    complete: bool = True,
    interactions: int = 100,
) -> None:
    transfer = {
        variant: {
            "zero_shot_mean_reward": float(seed),
            "adapted_mean_reward": float(seed + index),
            "adaptation_gain": float(index),
        }
        for index, variant in enumerate(NICHE_VARIANTS)
    }
    if not complete:
        transfer.pop(NICHE_VARIANTS[-1])
    store.add_trial(trial_id, "mn", algorithm, seed, 100)
    store.complete_trial(trial_id, interactions, 0.0, 0.0, {}, transfer)


def _store(tmp_path):
    store = Store(tmp_path)
    cfg = {"seeds": [1, 2], "budget": 100}
    store.upsert_experiment("mn", "multi-niche", "test", "h", cfg, None)
    return store


def test_transfer_analysis_aggregates_shocks_within_each_seed(tmp_path):
    store = _store(tmp_path)
    for algorithm in ("map_elites", "fixed_objective_ga"):
        for seed in (1, 2):
            _record_trial(store, trial_id=f"{algorithm}-{seed}", algorithm=algorithm, seed=seed)

    values = transfer_values_by_seed(store, "mn", endpoint="adapted_mean_reward")
    aggregate = aggregate_by_seed(values["map_elites"])
    assert aggregate == {1: 3.0, 2: 4.0}


def test_transfer_analysis_rejects_missing_registered_shock(tmp_path):
    store = _store(tmp_path)
    for algorithm in ("map_elites", "fixed_objective_ga"):
        _record_trial(store, trial_id=f"{algorithm}-1", algorithm=algorithm, seed=1)
        _record_trial(store, trial_id=f"{algorithm}-2", algorithm=algorithm, seed=2, complete=algorithm == "map_elites")

    with pytest.raises(ValueError, match="missing transfer variant"):
        transfer_values_by_seed(store, "mn", endpoint="adapted_mean_reward")


def test_transfer_analysis_rejects_an_over_budget_trial(tmp_path):
    store = _store(tmp_path)
    for algorithm in ("map_elites", "fixed_objective_ga"):
        _record_trial(
            store,
            trial_id=f"{algorithm}-1",
            algorithm=algorithm,
            seed=1,
            interactions=101 if algorithm == "map_elites" else 100,
        )
        _record_trial(store, trial_id=f"{algorithm}-2", algorithm=algorithm, seed=2)

    with pytest.raises(ValueError, match="exceeded the registered training cap"):
        transfer_values_by_seed(store, "mn", endpoint="adapted_mean_reward")
