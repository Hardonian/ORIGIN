"""Evaluation harness tests: episodes, budgets, train/test isolation, transfer."""

from __future__ import annotations

import numpy as np

from origin.environments.gridworld import GridWorldConfig
from origin.evaluation.harness import (
    Evaluator,
    evaluate_policy,
    morphology_variants,
    multi_niche_variants,
    perturbation_variants,
    run_episode,
)
from origin.organisms import HeuristicPolicy, RandomPolicy
from origin.organisms.morphology import Morphology
from origin.organisms.organism import Organism


def test_episode_result_fields():
    base = GridWorldConfig(height=8, width=8, max_steps=30, seed=0)
    env = __import__("origin.environments", fromlist=["GridWorld"]).GridWorld(base)
    pol = RandomPolicy(base.n_actions, 0)
    ep = run_episode(env, pol, seed=3)
    assert ep.steps >= 1
    assert isinstance(ep.reward, float)
    assert len(ep.descriptor) == 5


def test_evaluator_counts_interactions():
    base = GridWorldConfig(height=6, width=6, max_steps=20, seed=0)
    ev = Evaluator(base_env=base, train_seeds=[1, 2, 3])
    rng = np.random.default_rng(0)
    org = Organism.random(Morphology(), base, rng)
    fit, desc, results = ev.evaluate_organism(org)
    assert ev.interactions == sum(r.steps for r in results)
    assert ev.interactions > 0


def test_budget_exhaustion():
    base = GridWorldConfig(height=6, width=6, max_steps=20, n_resources=1, n_hazards=0, seed=0)
    ev = Evaluator(base_env=base, train_seeds=[1], budget=15)
    rng = np.random.default_rng(0)
    org = Organism.random(Morphology(), base, rng)
    ev.evaluate_organism(org)
    assert ev.exhausted


def test_heuristic_beats_random_on_task():
    base = GridWorldConfig(height=8, width=8, max_steps=60, n_resources=4, n_hazards=1,
                           obstacle_density=0.05, resource_regen=False, step_penalty=0.001,
                           wall_penalty=0.0, seed=0)
    r = evaluate_policy(base, RandomPolicy(base.n_actions, 0), [1, 2, 3])
    h = evaluate_policy(base, HeuristicPolicy(base.n_actions, 0), [1, 2, 3])
    assert h["mean_reward"] > r["mean_reward"]


def test_morphology_and_perturbation_variants_are_distinct():
    base = GridWorldConfig(height=8, width=8, seed=0)
    morphs = morphology_variants(base)
    assert {"sensor_local", "sensor_nonspatial", "body_fast", "body_small"} <= set(morphs)
    hashes = {c.config_hash() for c in morphs.values()}
    assert len(hashes) == len(morphs)
    perts = perturbation_variants(base)
    assert len(perts) >= 4


def test_transfer_to_different_morphology_executes():
    base = GridWorldConfig(height=8, width=8, max_steps=40, seed=0)
    rng = np.random.default_rng(0)
    org = Organism.random(Morphology(), base, rng)
    for name, vcfg in morphology_variants(base).items():
        res = evaluate_policy(vcfg, org, [1, 2])
        assert "mean_reward" in res, name


def test_multi_niche_transfer_variants_are_valid_and_distinct():
    base = GridWorldConfig(
        height=8,
        width=8,
        max_steps=20,
        n_resources=2,
        n_resources_b=2,
        n_hazards=1,
        resource_regen=False,
        obs_mode="multi_niche",
        seed=0,
    )
    variants = multi_niche_variants(base)
    assert {
        "niche_a_only",
        "niche_b_only",
        "niche_payoff_swap",
        "niche_toxic_hazard",
        "niche_scarcity_shock",
    } <= set(variants)
    assert len({cfg.config_hash() for cfg in variants.values()}) == len(variants)
    for cfg in variants.values():
        cfg.validate()
