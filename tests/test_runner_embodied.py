"""Milestone 4 runner integration: embodied campaigns through the same pipeline.

These assert that the *existing* experiment machinery (config validation, store,
metrics, checkpoints, transfer reporting) handles the articulated-physics simulator,
so embodied results live in the same store and analysis path as grid results rather
than a parallel bespoke one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from origin.experiments.runner import (
    build_base_env,
    run_experiment,
    sim_kind,
    validate_config,
)
from origin.experiments.store import Store

pytestmark = [pytest.mark.embodied, pytest.mark.integration]

EMBODIED_TINY = {
    "name": "validate_embodied",
    "protocol": "test",
    "env_kind": "embodied",
    "env": {"morphology": "centipede", "n_links": 6, "episode_seconds": 1.5, "seed": 0},
    "train_seeds": [1, 2],
    "test_seeds": [101, 202],
    "budget": 1500,
    "seeds": [1],
    "include_baselines": ["random", "scripted_gait"],
    "transfer": {"adapt": True, "budget": 600},
    "algorithms": {
        "fixed_objective_ga": {"pop_size": 6, "max_generations": 30},
        "map_elites": {"batch": 4, "grid_shape": [4, 4], "max_iterations": 20},
        "novelty_search": {"pop_size": 6, "max_generations": 30},
    },
}


def test_sim_kind_and_env_build():
    assert sim_kind(EMBODIED_TINY) == "embodied"
    assert sim_kind({"env_kind": "gridworld", "env": {}}) == "gridworld"
    assert sim_kind({}) == "gridworld"
    base = build_base_env(EMBODIED_TINY["env"], "embodied")
    assert base.morphology == "centipede"
    assert base.n_actions == 5
    with pytest.raises(ValueError):
        sim_kind({"env_kind": "nope", "env": {}})


def test_config_validation_rejects_grid_only_baseline():
    bad = json.loads(json.dumps(EMBODIED_TINY))
    bad["include_baselines"] = ["heuristic"]
    with pytest.raises(ValueError, match="not available for env_kind"):
        validate_config(bad)


def test_config_validation_accepts_embodied():
    validate_config(EMBODIED_TINY)


def test_embodied_campaign_end_to_end(tmp_path):
    report = run_experiment(EMBODIED_TINY, store_root=tmp_path, jobs=1, resume=True)
    store = Store(tmp_path)
    exp = report["experiment_id"]
    trials = store.trials(exp)
    summary = store.summary(exp)
    assert summary["n_failed"] == 0, [t.get("error") for t in trials if t["status"] != "done"]
    assert summary["n_done"] == 5  # 3 algorithms + 2 baselines
    assert report["n_trials_run"] == 5

    by_algo = {t["algorithm"]: t for t in trials}
    for t in trials:
        assert t["metrics_json"], f"{t['algorithm']} has no metrics"
        assert json.loads(t["metrics_json"])["env_kind"] == "embodied"

    # A learned algorithm must persist a checkpoint and report held-out performance
    # plus a transfer table over genuinely distinct bodies.
    ga = by_algo["fixed_objective_ga"]
    gm = json.loads(ga["metrics_json"])
    assert gm["test_mean_reward"] is not None
    assert gm["test_fall_rate"] is not None
    assert gm["test_mean_distance_travelled"] is not None

    gt = json.loads(ga["transfer_json"])
    morphology = {k: v for k, v in gt.items() if v.get("kind") == "morphology"}
    assert len(morphology) >= 3, f"expected >=3 distinct bodies, got {sorted(gt)}"
    for name, entry in morphology.items():
        assert "zero_shot_mean_reward" in entry, name
        assert "zero_shot_fall_rate" in entry, name
        assert "adapted_mean_reward" in entry, name
        assert entry["adaptation_interactions"] > 0, name

    # checkpoints are real files on disk, keyed by trial id
    checkpoints = list(Path(tmp_path).rglob("*.organism.json"))
    assert checkpoints, "no organism checkpoint was written"
    for cp in checkpoints:
        json.loads(cp.read_text())


def test_embodied_organism_checkpoints_round_trip(tmp_path):
    """A persisted embodied-evolved organism must load and drive the physics body."""
    from origin.environments.embodied import EmbodiedConfig
    from origin.evaluation.embodied import evaluate_embodied
    from origin.organisms.organism import Organism

    run_experiment(EMBODIED_TINY, store_root=tmp_path, jobs=1, resume=True)
    cp = next(iter(Path(tmp_path).rglob("*.organism.json")))
    org = Organism.from_dict(json.loads(cp.read_text()))
    base = EmbodiedConfig.preset("centipede", n_links=6, episode_seconds=1.5)
    metrics = evaluate_embodied(base, org, [101])
    assert metrics["n_episodes"] == 1
    assert metrics["mean_reward"] is not None


def test_embodied_resume_skips_completed(tmp_path):
    run_experiment(EMBODIED_TINY, store_root=tmp_path, jobs=1, resume=True)
    r2 = run_experiment(EMBODIED_TINY, store_root=tmp_path, jobs=1, resume=True)
    assert r2["n_pending_before"] == 0


EMBODIED_SPY = {
    "name": "spy_embodied",
    "protocol": "test",
    "env_kind": "embodied",
    "env": {"morphology": "worm", "n_links": 5, "episode_seconds": 1.5, "seed": 0},
    "train_seeds": [1, 2],
    "test_seeds": [101, 202],
    "budget": 400,
    "seeds": [1],
    "include_baselines": ["random"],
    "transfer": {"adapt": True, "budget": 120},
    "algorithms": {"fixed_objective_ga": {"pop_size": 4, "max_generations": 5}},
}


def test_adaptation_never_trains_on_test_seeds(monkeypatch, tmp_path):
    """Regression guard: adapted transfer must be scored on unseen seeds.

    Fine-tuning on the evaluation seeds and then scoring on the same seeds made
    every "adaptation gain" in-sample. This asserts every adaptation run by the
    transfer report trains on the train seeds only.
    """
    import origin.experiments.runner as runner_mod

    seen: list[list[int]] = []
    real_fine_tune = runner_mod.fine_tune

    def spy(*args, **kwargs):
        seen.append(list(kwargs.get("seeds", [])))
        return real_fine_tune(*args, **kwargs)

    monkeypatch.setattr(runner_mod, "fine_tune", spy)
    run_experiment(EMBODIED_SPY, store_root=tmp_path, jobs=1, resume=True)
    assert seen, "transfer adaptation never ran; the guard would be vacuous"
    for s in seen:
        assert set(s) <= set(EMBODIED_SPY["train_seeds"]), f"adaptation trained on unexpected seeds {s}"
        assert not set(s) & set(EMBODIED_SPY["test_seeds"]), f"adaptation trained on test seeds {s}"
