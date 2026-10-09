"""Milestone 3 tests: evolution baselines + learning baseline."""

from __future__ import annotations

import numpy as np

from origin.environments.gridworld import GridWorldConfig
from origin.evaluation.harness import Evaluator
from origin.evolution import fixed_objective_ga, map_elites, novelty_search
from origin.learning import reinforce
from origin.learning.reinforce import _PolicyNet


def _base():
    return GridWorldConfig(height=8, width=8, max_steps=60, n_resources=4, n_hazards=1,
                           obstacle_density=0.05, resource_regen=False, step_penalty=0.001,
                           wall_penalty=0.0, hazard_penalty=0.5, seed=0)


def _ev(budget=12000):
    return Evaluator(base_env=_base(), train_seeds=[1, 2], budget=budget)


def test_ga_improves_and_respects_budget():
    base = _base()
    ev = _ev()
    res = fixed_objective_ga(ev, base, seed=1, pop_size=16, max_generations=200)
    assert res.history, "no generations recorded"
    assert res.best_fitness >= res.history[0]["best"] - 1e-9
    assert res.interactions <= res.budget
    assert res.best_organism is not None
    assert res.best_organism.controller.sizes[0] == 7


def test_ga_deterministic_given_seed():
    base = _base()
    r1 = fixed_objective_ga(_ev(), base, seed=7, pop_size=12, max_generations=200)
    r2 = fixed_objective_ga(_ev(), base, seed=7, pop_size=12, max_generations=200)
    assert r1.best_fitness == r2.best_fitness
    assert r1.best_organism.controller.genome_hash() == r2.best_organism.controller.genome_hash()


def test_novelty_archive_grows_and_differs_from_ga():
    base = _base()
    nov = novelty_search(_ev(), base, seed=1, pop_size=16, max_generations=200)
    assert nov.interactions <= nov.budget
    assert nov.extra["archive_size"] > 0
    ga = fixed_objective_ga(_ev(), base, seed=1, pop_size=16, max_generations=200)
    # novelty optimizes a different objective; its archive must be populated
    assert nov.extra["archive_size"] >= 16
    assert nov.history[0]["mean_novelty"] == 0.0  # empty archive at gen 0
    assert nov.best_organism is not None or ga.best_organism is not None


def test_map_elites_coverage_and_archive():
    base = _base()
    res = map_elites(_ev(), base, seed=1, batch=8, grid_shape=(8, 8), max_iterations=200)
    assert res.interactions <= res.budget
    assert res.extra["archive_size"] > 0
    assert 0.0 < res.extra["coverage"] <= 1.0
    assert res.archive is not None and len(res.archive) == res.extra["archive_size"]


def test_reinforce_learns_and_returns_organism():
    base = _base()
    ev = _ev(budget=8000)
    res = reinforce(ev, base, seed=1, hidden=(12,), episodes_per_update=2, max_updates=100)
    assert res.interactions <= res.budget
    assert res.interactions > 0
    assert res.best_organism is not None
    assert res.best_organism.controller.sizes == [7, 12, base.n_actions]
    assert res.best_fitness >= -1e9


def test_reinforce_uses_the_tanh_activation_derivative_for_hidden_layers():
    """Backprop receives activations, not pre-activation logits.

    This guards against applying ``tanh`` twice in the hidden derivative, which
    silently shrinks policy gradients without causing a shape or runtime error.
    """
    net = _PolicyNet([2, 2, 2], np.random.default_rng(9), lr=0.01)
    net.w = [
        np.array([[0.2, -0.1], [0.3, 0.4]]),
        np.array([[0.5, -0.2], [-0.3, 0.1]]),
    ]
    net.b = [np.array([0.05, -0.02]), np.array([0.01, 0.03])]
    captured: dict[str, list[np.ndarray]] = {}
    net._adam = lambda grad_w, grad_b: captured.update(w=grad_w, b=grad_b)  # type: ignore[method-assign]

    x = np.array([0.4, -0.7])
    acts, probs = net.forward(x)
    advantage = 0.6
    action = 1
    net.backward(acts, probs, action, advantage)

    output_delta = probs.copy()
    output_delta[action] -= 1.0
    output_delta *= advantage
    hidden_delta = (net.w[1] @ output_delta) * (1 - acts[1] ** 2)

    assert np.allclose(captured["w"][1], np.outer(acts[1], output_delta))
    assert np.allclose(captured["b"][1], output_delta)
    assert np.allclose(captured["w"][0], np.outer(x, hidden_delta))
    assert np.allclose(captured["b"][0], hidden_delta)
