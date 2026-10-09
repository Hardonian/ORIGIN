"""Milestone 1 acceptance tests: determinism, validity, replay, serialization."""

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


def test_seed_determinism_identical_trajectories():
    cfg = GridWorldConfig(height=8, width=8, max_steps=50, seed=123, terrain="random")
    a, b = GridWorld(cfg), GridWorld(cfg)
    oa, _ = a.reset(seed=123)
    ob, _ = b.reset(seed=123)
    assert np.array_equal(a._grid, b._grid)
    assert np.allclose(oa, ob)
    for act in [0, 1, 2, 3, 4, 0, 1, 3, 2, 4]:
        ra = a.step(act)
        rb = b.step(act)
        assert ra[1] == rb[1]
        assert ra[2] == rb[2]
        assert np.allclose(ra[0], rb[0])


def test_different_seed_procedural_variation():
    a = GridWorld(GridWorldConfig(seed=1, terrain="random"))
    b = GridWorld(GridWorldConfig(seed=2, terrain="random"))
    a.reset(seed=1)
    b.reset(seed=2)
    assert not np.array_equal(a._grid, b._grid)


def test_observation_validity_and_shape():
    env = GridWorld(GridWorldConfig(height=6, width=6, seed=5))
    obs, info = env.reset(seed=5)
    assert obs.shape == (7,)
    assert env.observation_size == 7
    assert np.all(np.isfinite(obs))
    assert 0.0 <= obs[0] <= 1.0  # normalised energy
    assert obs[1] in (-1.0, 0.0, 1.0) and obs[2] in (-1.0, 0.0, 1.0)  # resource bearings


@pytest.mark.parametrize("obs_mode", ["multi_niche", "multi_niche_local"])
def test_multi_niche_resources_are_distinct_and_observable(obs_mode):
    cfg = GridWorldConfig(
        height=10,
        width=10,
        terrain="empty",
        n_resources=2,
        n_resources_b=2,
        n_hazards=1,
        resource_regen=False,
        obs_mode=obs_mode,
        seed=19,
    )
    env = GridWorld(cfg)
    obs, info = env.reset(seed=19)
    assert int(np.count_nonzero(env._grid == RESOURCE)) == 2
    assert int(np.count_nonzero(env._grid == RESOURCE_B)) == 2
    assert obs.shape == (7,)
    assert env.observation_size == 7
    assert np.all(np.isfinite(obs))
    assert info["collected_a"] == 0 and info["collected_b"] == 0


def test_multi_niche_resource_b_reward_and_state_roundtrip():
    env = GridWorld(
        GridWorldConfig(
            height=3,
            width=3,
            terrain="empty",
            n_resources=0,
            n_resources_b=0,
            n_hazards=0,
            resource_regen=False,
            resource_b_reward=2.5,
            step_penalty=0.1,
            obs_mode="multi_niche",
        )
    )
    env.reset(seed=0)
    env._grid = np.full((3, 3), EMPTY, dtype=np.int8)
    env._grid[1, 1] = RESOURCE_B
    env._agent = np.array([1, 0])
    _, reward, _, _, info = env.step(3)
    assert reward == pytest.approx(2.5 - 0.1)
    assert info["collected"] == 1 and info["collected_b"] == 1
    clone = GridWorld()
    clone.set_state(env.get_state())
    assert clone.get_state()["collected_b"] == 1
    assert np.allclose(clone._observation(), env._observation())


def test_action_validity():
    env = GridWorld(GridWorldConfig(seed=0))
    env.reset(seed=0)
    with pytest.raises(ValueError):
        env.step(5)
    with pytest.raises(ValueError):
        env.step(-1)


def test_reward_calculation_on_known_grid():
    env = GridWorld(GridWorldConfig(height=3, width=3, max_steps=10, n_resources=0, n_hazards=0,
                                    step_penalty=0.1, resource_reward=5.0, wall_penalty=0.5, seed=0))
    env.reset(seed=0)
    env._grid = np.full((3, 3), EMPTY, dtype=np.int8)
    env._grid[1, 1] = RESOURCE
    env._agent = np.array([1, 0])
    env._energy = 50.0
    _, r, _, _, info = env.step(3)  # move right onto resource
    assert r == pytest.approx(5.0 - 0.1)
    assert info["collected"] == 1

    env._grid[2, 2] = OBSTACLE
    env._agent = np.array([2, 1])
    _, r2, _, _, _ = env.step(3)  # bump into obstacle
    assert r2 < 0  # step penalty + wall penalty


def test_episode_termination_energy():
    env = GridWorld(GridWorldConfig(height=4, width=4, max_steps=100, energy_start=0.05, energy_step=0.1, seed=0))
    env.reset(seed=0)
    _, _, terminated, truncated, _ = env.step(4)
    assert terminated and not truncated


def test_truncation_at_max_steps():
    env = GridWorld(GridWorldConfig(height=4, width=4, max_steps=3, seed=0))
    env.reset(seed=0)
    last = None
    for _ in range(3):
        last = env.step(4)
    assert last is not None and last[3] is True


def test_state_serialization_roundtrip():
    env = GridWorld(GridWorldConfig(seed=7))
    env.reset(seed=7)
    for a in [0, 3, 1, 2]:
        env.step(a)
    state = env.get_state()
    clone = GridWorld()
    clone.set_state(state)
    assert np.array_equal(clone._grid, env._grid)
    assert np.array_equal(clone._agent, env._agent)
    assert clone._energy == env._energy
    # continuing both must agree
    r1 = env.step(1)
    r2 = clone.step(1)
    assert r1[1] == r2[1]


def test_replay_consistency():
    env = GridWorld(GridWorldConfig(seed=99))
    env.reset(seed=99)
    s0 = env.get_state()
    actions, rewards = [], []
    for a in [1, 1, 3, 0, 2, 4, 1, 3]:
        _, r, term, trunc, _ = env.step(a)
        actions.append(a)
        rewards.append(r)
        if term or trunc:
            break
    positions, ok = Replay(s0, actions, rewards).re_run()
    assert ok, "replayed rewards diverged from the original run"
    assert len(positions) == len(actions) + 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"height": 1},
        {"width": 1},
        {"max_steps": 0},
        {"terrain": "nope"},
        {"obstacle_density": 1.5},
        {"obs_mode": "bogus"},
        {"n_resources": 100, "n_hazards": 100, "height": 2, "width": 2},
        {"obs_radius": 0},
        {"energy_capacity": 0},
        {"noise": 2.0},
    ],
)
def test_invalid_configs_rejected(kwargs):
    with pytest.raises(ValueError):
        GridWorldConfig(**kwargs)


def test_config_hash_stable():
    a = GridWorldConfig(seed=1)
    b = GridWorldConfig(seed=1)
    assert a.config_hash() == b.config_hash()
    assert GridWorldConfig(seed=2).config_hash() != a.config_hash()


def test_unknown_config_field_rejected():
    with pytest.raises(ValueError):
        GridWorldConfig.from_dict({"height": 4, "width": 4, "bogus": 1})
