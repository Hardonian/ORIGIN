"""Registration invariants for the corrected PPO study."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.analyze_actor_critic import analyze_actor_critic

from origin.experiments.runner import validate_config

ROOT = Path(__file__).resolve().parents[1]


def _config(name: str) -> dict:
    return json.loads((ROOT / "configs" / name).read_text())


def test_v1_grid_config_is_preserved_as_an_exploratory_artifact():
    """The audited v1 file must not be silently rewritten after its execution."""
    v1 = _config("actor_critic_grid_v1.json")
    assert v1["budget"] == 50_000
    assert (ROOT / "research" / "reports" / "ACTOR_CRITIC_V1_CONFIGURATION_AUDIT.md").is_file()
    with pytest.raises(ValueError, match="exploratory"):
        analyze_actor_critic(str(ROOT / "runs"), ROOT / "configs" / "actor_critic_grid_v1.json")


def test_v2_grid_registration_is_complete_and_strict_cap():
    cfg = _config("actor_critic_grid_v2.json")
    validate_config(cfg)

    assert cfg["protocol"] == "actor_critic_v2_grid"
    assert cfg["budget"] == 500_000
    assert cfg["train_seeds"] == [11, 22, 33, 44]
    assert cfg["test_seeds"] == [101, 202, 303, 404]
    assert cfg["seeds"] == list(range(400, 440))
    assert cfg["primary_comparison"] == {
        "method": "ppo",
        "baseline": "reinforce",
        "endpoint": "test_mean_reward",
        "bootstrap_seed": 20261019,
    }


def test_v2_embodied_registration_matches_the_registered_worm():
    cfg = _config("actor_critic_embodied_v2.json")
    validate_config(cfg)

    assert cfg["protocol"] == "actor_critic_v2_embodied"
    assert cfg["budget"] == 300_000
    assert cfg["seeds"] == list(range(500, 520))
    assert cfg["train_seeds"] == [11, 22, 33, 44]
    assert cfg["test_seeds"] == [101, 202, 303, 404]
    assert cfg["env"]["n_links"] == 8
    assert cfg["env"]["episode_seconds"] == 8.0
    assert cfg["env"]["joint_axis"] == "yaw"
    assert cfg["primary_comparison"] == {
        "method": "ppo",
        "baseline": "random",
        "endpoint": "test_mean_reward",
        "bootstrap_seed": 20261019,
    }
