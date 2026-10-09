"""Unit and integration tests for multi-niche grid world and transfer evaluation."""

from __future__ import annotations

import numpy as np
import pytest

from origin.environments.gridworld import (
    EMPTY,
    OBSTACLE,
    RESOURCE,
    RESOURCE_B,
    GridWorld,
    GridWorldConfig,
    Replay,
)
from origin.evaluation.harness import (
    Evaluator,
    evaluate_policy,
    multi_niche_variants,
)
from origin.evolution import fixed_objective_ga, map_elites
from origin.experiments.runner import run_trial
from origin.organisms.policies import HeuristicPolicy, RandomPolicy


def test_multi_niche_config_validation():
    # Valid configurations
    cfg = GridWorldConfig(
        height=8,
        width=8,
        n_resources=3,
        n_resources_b=3,
        obs_mode="multi_niche",
        niche_distribution="zones",
    )
    assert cfg.n_resources_b == 3
    assert cfg.obs_mode == "multi_niche"
    assert cfg.niche_distribution == "zones"

    # Rejection of negative resources
    with pytest.raises(ValueError, match="n_resources_b must be >= 0"):
        GridWorldConfig(n_resources_b=-1)

    # Rejection of invalid distribution
    with pytest.raises(ValueError, match="niche_distribution must be uniform\\|zones"):
        GridWorldConfig(niche_distribution="spiral")

    # Rejection of cell overflow
    with pytest.raises(ValueError, match="must leave at least one free cell"):
        GridWorldConfig(height=4, width=4, n_resources=10, n_resources_b=10)


def test_multi_niche_determinism_and_generation():
    cfg = GridWorldConfig(
        height=10,
        width=10,
        max_steps=50,
        n_resources=4,
        n_resources_b=4,
        n_hazards=2,
        obstacle_density=0.05,
        niche_distribution="zones",
        seed=42,
    )
    env1 = GridWorld(cfg)
    env2 = GridWorld(cfg)
    obs1, info1 = env1.reset(seed=42)
    obs2, info2 = env2.reset(seed=42)

    assert np.array_equal(env1._grid, env2._grid)
    assert np.allclose(obs1, obs2)
    assert np.count_nonzero(env1._grid == RESOURCE) == 4
    assert np.count_nonzero(env1._grid == RESOURCE_B) == 4

    # Zone distribution check: Resource A in top half, Resource B in bottom half
    res_a_rows = np.argwhere(env1._grid == RESOURCE)[:, 0]
    res_b_rows = np.argwhere(env1._grid == RESOURCE_B)[:, 0]
    assert np.all(res_a_rows < 5)
    assert np.all(res_b_rows >= 5)

    # Deterministic step trajectory
    for a in [0, 1, 3, 2, 4, 1, 0, 3]:
        r1 = env1.step(a)
        r2 = env2.step(a)
        assert r1[1] == r2[1]
        assert r1[2] == r2[2]
        assert np.allclose(r1[0], r2[0])


def test_multi_niche_observation_shape_and_bearings():
    cfg = GridWorldConfig(
        height=8,
        width=8,
        n_resources=2,
        n_resources_b=2,
        obs_mode="multi_niche",
        seed=10,
    )
    env = GridWorld(cfg)
    obs, info = env.reset(seed=10)

    assert obs.shape == (7,)
    assert env.observation_size == 7
    assert np.all(np.isfinite(obs))
    assert 0.0 <= obs[0] <= 1.0  # normalized energy
    # Bearings for Niche A and Niche B
    assert obs[1] in (-1.0, 0.0, 1.0)
    assert obs[2] in (-1.0, 0.0, 1.0)
    assert obs[4] in (-1.0, 0.0, 1.0)
    assert obs[5] in (-1.0, 0.0, 1.0)

    # Local mode
    cfg_local = GridWorldConfig(
        height=8,
        width=8,
        n_resources=2,
        n_resources_b=2,
        obs_mode="multi_niche_local",
        obs_radius=2,
        seed=10,
    )
    env_local = GridWorld(cfg_local)
    obs_local, _ = env_local.reset(seed=10)
    assert obs_local.shape == (7,)


def test_multi_niche_consumption_and_tracking():
    cfg = GridWorldConfig(
        height=4,
        width=4,
        max_steps=10,
        n_resources=0,
        n_resources_b=0,
        n_hazards=0,
        step_penalty=0.01,
        resource_reward=1.0,
        resource_energy=5.0,
        resource_b_reward=3.0,
        resource_b_energy=15.0,
        seed=0,
    )
    env = GridWorld(cfg)
    env.reset(seed=0)
    env._grid = np.full((4, 4), EMPTY, dtype=np.int8)
    env._agent = np.array([1, 1], dtype=np.int64)
    env._grid[1, 2] = RESOURCE      # Niche A to the right
    env._grid[2, 1] = RESOURCE_B    # Niche B down
    env._energy = 50.0

    # Step right onto Niche A
    _, r1, _, _, info1 = env.step(3)
    assert r1 == pytest.approx(1.0 - 0.01)
    assert info1["collected_a"] == 1
    assert info1["collected_b"] == 0
    assert info1["collected"] == 1
    assert env._energy == pytest.approx(50.0 + 5.0 - 0.1)

    # Step left back to start
    env.step(2)
    # Step down onto Niche B
    _, r2, _, _, info2 = env.step(1)
    assert r2 == pytest.approx(3.0 - 0.01)
    assert info2["collected_a"] == 1
    assert info2["collected_b"] == 1
    assert info2["collected"] == 2


def test_multi_niche_descriptor():
    cfg = GridWorldConfig(
        height=6,
        width=6,
        max_steps=50,
        n_resources=2,
        n_resources_b=2,
        seed=3,
    )
    env = GridWorld(cfg)
    env.reset(seed=3)
    env._collected_a = 3
    env._collected_b = 5
    env._hazard_hits = 1
    env._steps = 10

    desc = env._descriptor()
    assert desc.shape == (5,)
    assert desc[0] == pytest.approx(3.0)  # collected_a
    assert desc[1] == pytest.approx(5.0)  # collected_b
    assert desc[2] == pytest.approx(0.1)  # hazard_rate (1 / 10)


def test_multi_niche_state_serialization_and_replay():
    cfg = GridWorldConfig(
        height=8,
        width=8,
        n_resources=3,
        n_resources_b=3,
        seed=77,
    )
    env = GridWorld(cfg)
    env.reset(seed=77)
    for a in [0, 3, 1, 2, 4]:
        env.step(a)

    state = env.get_state()
    assert "collected_a" in state
    assert "collected_b" in state

    clone = GridWorld()
    clone.set_state(state)
    assert np.array_equal(clone._grid, env._grid)
    assert np.array_equal(clone._agent, env._agent)
    assert clone._collected_a == env._collected_a
    assert clone._collected_b == env._collected_b
    assert clone._energy == env._energy

    # Replay consistency
    s0 = env.get_state()
    actions, rewards = [], []
    for a in [1, 3, 0, 2]:
        _, r, term, trunc, _ = env.step(a)
        actions.append(a)
        rewards.append(r)
        if term or trunc:
            break
    positions, ok = Replay(s0, actions, rewards).re_run()
    assert ok


def test_multi_niche_variants():
    base = GridWorldConfig(
        height=10,
        width=10,
        n_resources=4,
        n_resources_b=4,
        resource_reward=1.0,
        resource_b_reward=2.5,
    )
    vars = multi_niche_variants(base)
    assert "niche_b_only" in vars
    assert "niche_a_only" in vars
    assert "niche_payoff_swap" in vars
    assert "niche_toxic_hazard" in vars
    assert "niche_scarcity_shock" in vars

    assert vars["niche_b_only"].n_resources == 0
    assert vars["niche_b_only"].n_resources_b == 8

    assert vars["niche_a_only"].n_resources == 8
    assert vars["niche_a_only"].n_resources_b == 0

    assert vars["niche_payoff_swap"].resource_reward == 2.5
    assert vars["niche_payoff_swap"].resource_b_reward == 1.0


def test_multi_niche_heuristic_policy():
    cfg = GridWorldConfig(
        height=6,
        width=6,
        max_steps=20,
        n_resources=2,
        n_resources_b=2,
        n_hazards=1,
        seed=12,
    )
    env = GridWorld(cfg)
    pol = HeuristicPolicy(cfg.n_actions, seed=12)
    res = evaluate_policy(cfg, pol, seeds=[12, 13])
    assert res["mean_collected"] > 0
    assert res["mean_reward"] > 0


def test_multi_niche_map_elites_archive_and_ga():
    base = GridWorldConfig(
        height=8,
        width=8,
        max_steps=40,
        n_resources=3,
        n_resources_b=3,
        obs_mode="multi_niche",
        seed=1,
    )
    ev = Evaluator(base_env=base, train_seeds=[101], budget=4000)

    # MAP-Elites with 2D (collected_a, collected_b) archive
    res_qd = map_elites(
        ev,
        base,
        seed=1,
        grid_shape=(6, 6),
        batch=6,
        desc_dims=(0, 1),
        bounds=[(0.0, 6.0), (0.0, 6.0)],
        max_iterations=100,
    )
    assert res_qd.archive is not None
    assert len(res_qd.archive) > 0
    assert res_qd.extra["archive_size"] > 0
    assert res_qd.best_organism is not None

    # GA on multi-niche
    ev_ga = Evaluator(base_env=base, train_seeds=[101], budget=4000)
    res_ga = fixed_objective_ga(ev_ga, base, seed=1, pop_size=8, max_generations=50)
    assert res_ga.best_organism is not None


def test_multi_niche_trial_execution_and_transfer_report():
    cfg = {
        "name": "test_multi_niche",
        "env_kind": "gridworld",
        "env": {
            "height": 8,
            "width": 8,
            "max_steps": 30,
            "n_resources": 2,
            "n_resources_b": 2,
            "obs_mode": "multi_niche",
            "seed": 1,
        },
        "algorithms": {
            "fixed_objective_ga": {"pop_size": 8},
            "map_elites": {"batch": 6},
        },
        "train_seeds": [101],
        "test_seeds": [201],
        "budget": 2000,
        "seeds": [1],
        "transfer": {
            "adapt": True,
            "budget": 500,
        },
    }

    trial = run_trial("map_elites", 1, cfg)
    assert trial["status"] == "done"
    assert "transfer" in trial
    # Multi-niche variants must be present in the transfer report
    transfer = trial["transfer"]
    assert "niche_b_only" in transfer
    assert "niche_a_only" in transfer
    assert "niche_payoff_swap" in transfer
    assert "zero_shot_mean_reward" in transfer["niche_b_only"]
    assert "adaptation_gain" in transfer["niche_b_only"]
