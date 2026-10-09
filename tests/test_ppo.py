"""Tests for Proximal Policy Optimization (PPO) Actor-Critic baseline."""

from __future__ import annotations

import numpy as np

from origin.environments.gridworld import GridWorldConfig
from origin.evaluation.harness import Evaluator
from origin.experiments.runner import ALGORITHMS
from origin.learning.ppo import _ActorNet, _CriticNet, ppo


def _base():
    return GridWorldConfig(
        height=8,
        width=8,
        max_steps=50,
        n_resources=3,
        n_hazards=1,
        obstacle_density=0.05,
        resource_regen=False,
        step_penalty=0.001,
        wall_penalty=0.0,
        hazard_penalty=0.5,
        seed=0,
    )


def _ev(budget=10000):
    return Evaluator(base_env=_base(), train_seeds=[1, 2], budget=budget)


def test_actor_forward_and_clipping():
    rng = np.random.default_rng(42)
    actor = _ActorNet([4, 8, 3], rng, lr=0.01)
    x = np.array([0.5, -0.2, 0.1, 0.8])
    acts, p = actor.forward(x)

    assert len(p) == 3
    assert np.isclose(float(np.sum(p)), 1.0)
    assert np.all(p > 0)

    # Test backward pass unclipped
    w_before = [w.copy() for w in actor.w]
    actor.backward(acts, p, action=1, old_prob=float(p[1]), advantage=0.5, clip_eps=0.2)
    # Weights should be updated by Adam
    assert not np.allclose(actor.w[0], w_before[0])


def test_critic_forward_and_backward():
    rng = np.random.default_rng(42)
    critic = _CriticNet([4, 8, 1], rng, lr=0.01)
    x = np.array([0.5, -0.2, 0.1, 0.8])
    acts, val = critic.forward(x)

    assert isinstance(val, float)

    w_before = [w.copy() for w in critic.w]
    critic.backward(acts, val, target=1.0)
    assert not np.allclose(critic.w[0], w_before[0])


def test_ppo_learns_and_respects_budget():
    base = _base()
    ev = _ev(budget=6000)
    res = ppo(
        ev,
        base,
        seed=1,
        hidden=(12,),
        episodes_per_update=2,
        epochs_per_update=2,
        max_updates=50,
    )

    assert res.algorithm == "ppo"
    assert res.interactions <= res.budget
    assert res.interactions > 0
    assert res.best_organism is not None
    assert res.best_organism.controller.sizes == [7, 12, base.n_actions]
    assert res.best_fitness >= -1e9
    assert len(res.history) > 0


def test_ppo_deterministic_given_seed():
    base = _base()
    r1 = ppo(_ev(budget=4000), base, seed=7, hidden=(8,), episodes_per_update=2, epochs_per_update=2, max_updates=20)
    r2 = ppo(_ev(budget=4000), base, seed=7, hidden=(8,), episodes_per_update=2, epochs_per_update=2, max_updates=20)

    assert r1.best_fitness == r2.best_fitness
    assert r1.interactions == r2.interactions
    assert r1.best_organism.controller.genome_hash() == r2.best_organism.controller.genome_hash()


def test_ppo_runner_registration():
    assert "ppo" in ALGORITHMS
    assert ALGORITHMS["ppo"] is ppo
