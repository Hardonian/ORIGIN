"""Milestone 5 tests: config validation, ids, store, runner, resume, cancel."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from origin.experiments.api import _morphology_plan
from origin.experiments.runner import (
    environment_manifest,
    experiment_id,
    run_experiment,
    trial_id_for,
    validate_config,
)
from origin.experiments.store import Store

TINY = {
    "name": "tiny",
    "protocol": "test",
    "env": {"height": 6, "width": 6, "max_steps": 20, "n_resources": 2, "n_hazards": 0,
            "obstacle_density": 0.05, "resource_regen": False, "step_penalty": 0.001,
            "wall_penalty": 0.0, "seed": 0},
    "train_seeds": [1, 2],
    "test_seeds": [7, 8],
    "budget": 3000,
    "seeds": [1],
    "include_baselines": ["random", "heuristic"],
    "transfer": {"adapt": False},
    "algorithms": {
        "fixed_objective_ga": {"pop_size": 8, "max_generations": 50},
        "novelty_search": {"pop_size": 8, "max_generations": 50},
        "map_elites": {"batch": 4, "grid_shape": [5, 5], "max_iterations": 50},
        "reinforce": {"hidden": [8], "episodes_per_update": 2, "max_updates": 20},
    },
}


def test_validate_config_ok():
    validate_config(TINY)


def test_registered_multi_niche_transfer_config_validates():
    path = Path(__file__).parents[1] / "configs" / "multi_niche_transfer.json"
    cfg = json.loads(path.read_text(encoding="utf-8"))
    validate_config(cfg)
    assert cfg["env"]["obs_mode"] == "multi_niche"
    assert cfg["env"]["n_resources_b"] > 0
    assert set(cfg["train_seeds"]).isdisjoint(cfg["test_seeds"])


def test_validate_config_rejects_seed_leakage():
    bad = json.loads(json.dumps(TINY))
    bad["test_seeds"] = [1, 99]
    with pytest.raises(ValueError, match="leakage"):
        validate_config(bad)


def test_validate_config_rejects_unknown_algorithm():
    bad = json.loads(json.dumps(TINY))
    bad["algorithms"]["nope"] = {}
    with pytest.raises(ValueError, match="unknown algorithm"):
        validate_config(bad)


def test_validate_config_rejects_missing_keys():
    with pytest.raises(ValueError):
        validate_config({"name": "x"})


def test_experiment_and_trial_ids_deterministic():
    assert experiment_id(TINY) == experiment_id(json.loads(json.dumps(TINY)))
    assert trial_id_for("e", "ga", 1) == trial_id_for("e", "ga", 1)
    assert trial_id_for("e", "ga", 1) != trial_id_for("e", "ga", 2)


def test_store_roundtrip(tmp_path):
    store = Store(tmp_path)
    store.upsert_experiment("e1", "n", "p", "h", {"a": 1}, "sha")
    store.add_trial("t1", "e1", "ga", 1, 100)
    assert store.trial_status("t1") == "running"
    store.complete_trial("t1", 50, 1.0, 0.9, {"test_mean_reward": 1.0}, {"sensor_local": {"zero_shot_mean_reward": 0.5}})
    assert store.trial_status("t1") == "done"
    trials = store.trials("e1")
    assert len(trials) == 1 and trials[0]["best_fitness"] == 1.0
    exports = store.export_trials("e1")
    assert Path(exports["csv"]).exists()


def test_store_failure_recorded(tmp_path):
    store = Store(tmp_path)
    store.upsert_experiment("e1", "n", "p", "h", {}, None)
    store.add_trial("t1", "e1", "ga", 1, 100)
    store.fail_trial("t1", "boom")
    assert store.trial_status("t1") == "failed"
    assert store.summary("e1")["n_failed"] == 1


def test_embodied_morphology_plan_comes_from_persisted_config(tmp_path):
    """The lab may inspect a declared body before a PyBullet host is available.

    It must return the configured contact/actuation plan, not claim to have
    replayed an unverified physics trajectory.
    """
    cfg = {
        "name": "embodied-viewer-fixture",
        "protocol": "test",
        "env_kind": "embodied",
        "env": {
            "morphology": "centipede",
            "n_links": 6,
            "link_length": 0.12,
            "joint_axis": "yaw",
            "lateral_friction": 1.2,
            "longitudinal_friction": 0.2,
        },
    }
    store = Store(tmp_path)
    store.upsert_experiment("embodied", cfg["name"], cfg["protocol"], "hash", cfg, None)
    store.add_trial("trial-1", "embodied", "fixed_objective_ga", 1, 100)

    plan = _morphology_plan(store, "embodied", "trial-1")
    assert plan["viewer_kind"] == "morphology_plan"
    assert plan["physics_replay"] is False
    assert len(plan["body"]["segments"]) == 7  # base + six links
    assert len(plan["body"]["joints"]) == 6
    assert plan["body"]["joint_axis"] == "yaw"
    assert plan["body"]["lateral_friction"] > plan["body"]["longitudinal_friction"]
    assert plan["calibration"]["status"] == "required"


def test_runner_end_to_end(tmp_path):
    report = run_experiment(TINY, store_root=tmp_path, jobs=1, resume=True)
    assert report["n_trials_run"] == 6  # 4 algorithms + 2 baselines
    store = Store(tmp_path)
    exp = report["experiment_id"]
    summary = store.summary(exp)
    assert summary["n_done"] == 6
    assert summary["n_failed"] == 0
    # metrics must be traceable to real runs
    for t in store.trials(exp):
        if t["status"] == "done":
            assert t["interactions"] >= 0
            assert t["metrics_json"]


def test_runner_resume_skips_completed(tmp_path):
    run_experiment(TINY, store_root=tmp_path, jobs=1, resume=True)
    r2 = run_experiment(TINY, store_root=tmp_path, jobs=1, resume=True)
    assert r2["n_pending_before"] == 0  # everything already done


def test_runner_cancellation(tmp_path):
    cancel_file = tmp_path / "cancel"
    cancel_file.write_text("stop")
    report = run_experiment(TINY, store_root=tmp_path, jobs=1, resume=False, cancel_file=cancel_file)
    assert report["n_trials_run"] == 0


def test_environment_manifest_has_git_and_hardware():
    m = environment_manifest()
    for key in ("python", "cpu_count", "packages", "git_sha", "platform"):
        assert key in m
    assert m["cpu_count"] >= 1


def test_grid_adaptation_never_trains_on_test_seeds(monkeypatch):
    """Same seed-isolation guard for the grid-world transfer report.

    The adapted score must be a held-out evaluation, not ``fine_tune``'s
    in-sample best fitness on its own adaptation seeds.
    """
    import numpy as np

    from origin.environments.gridworld import GridWorldConfig
    from origin.experiments import runner as runner_mod
    from origin.organisms.morphology import Morphology
    from origin.organisms.organism import Organism

    base = GridWorldConfig.from_dict(TINY["env"])
    org = Organism.random(Morphology(), base, np.random.default_rng(0))
    seen: list[list[int]] = []
    real_fine_tune = runner_mod.fine_tune

    def spy(*args, **kwargs):
        seen.append(list(kwargs.get("seeds", [])))
        return real_fine_tune(*args, **kwargs)

    monkeypatch.setattr(runner_mod, "fine_tune", spy)
    cfg = {"budget": 500, "transfer": {"adapt": True, "budget": 40}}
    report = runner_mod._transfer_report(org, base, [1, 2], [7, 8], cfg)
    assert seen, "grid adaptation never ran; the guard would be vacuous"
    for s in seen:
        assert set(s) <= {1, 2}, f"adaptation trained on unexpected seeds {s}"
        assert not set(s) & {7, 8}, f"adaptation trained on test seeds {s}"
    adapted = [e for e in report.values() if "adapted_mean_reward" in e]
    assert adapted, "no adapted entry was produced"
    for e in adapted:
        assert "adaptation_gain" in e
