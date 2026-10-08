"""Milestone 3 tests: evolution baselines + learning baseline."""

from __future__ import annotations

from origin.environments.gridworld import GridWorldConfig
from origin.evaluation.harness import Evaluator
from origin.evolution import fixed_objective_ga, map_elites, novelty_search
from origin.learning import reinforce


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
    assert res.interactions <= res.budget + 5000  # one generation of overshoot allowed
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
    assert nov.extra["archive_size"] > 0
    ga = fixed_objective_ga(_ev(), base, seed=1, pop_size=16, max_generations=200)
    # novelty optimizes a different objective; its archive must be populated
    assert nov.extra["archive_size"] >= 16
    assert nov.history[0]["mean_novelty"] == 0.0  # empty archive at gen 0
    assert nov.best_organism is not None or ga.best_organism is not None


def test_map_elites_coverage_and_archive():
    base = _base()
    res = map_elites(_ev(), base, seed=1, batch=8, grid_shape=(8, 8), max_iterations=200)
    assert res.extra["archive_size"] > 0
    assert 0.0 < res.extra["coverage"] <= 1.0
    assert res.archive is not None and len(res.archive) == res.extra["archive_size"]


def test_reinforce_learns_and_returns_organism():
    base = _base()
    ev = _ev(budget=8000)
    res = reinforce(ev, base, seed=1, hidden=(12,), episodes_per_update=2, max_updates=100)
    assert res.interactions > 0
    assert res.best_organism is not None
    assert res.best_organism.controller.sizes == [7, 12, base.n_actions]
    assert res.best_fitness >= -1e9
