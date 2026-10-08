"""Milestone 4 (embodied): evaluator contract, budget accounting, transfer, leaks.

These use the real physics engine and the real optimizers. The optimizer interface
asserted here is the same one GA / novelty search / MAP-Elites / REINFORCE use, so a
pass means those algorithms genuinely run against articulated bodies.
"""

from __future__ import annotations

import numpy as np
import pytest

from origin.environments.embodied import (
    EmbodiedConfig,
    EmbodiedCreature,
    embodied_morphology_variants,
)
from origin.evaluation.embodied import (
    EmbodiedEpisode,
    EmbodiedEvaluator,
    EmbodiedTransferResult,
    evaluate_embodied,
    run_embodied_episode,
    transfer_embodied,
)
from origin.evolution.ga import fixed_objective_ga
from origin.organisms.morphology import Morphology
from origin.organisms.organism import Organism

pytestmark = pytest.mark.embodied


@pytest.fixture(scope="module")
def small_body():
    return EmbodiedConfig.preset("worm", n_links=5, episode_seconds=2.0)


@pytest.fixture(scope="module")
def organism(small_body):
    return Organism.random(Morphology(), small_body, np.random.default_rng(0))


def test_episode_result_is_well_formed(small_body, organism):
    ep = run_embodied_episode(small_body, organism, seed=3)
    assert isinstance(ep, EmbodiedEpisode)
    assert ep.steps > 0
    assert np.isfinite(ep.reward)
    assert len(ep.descriptor) == 5
    assert ep.seed == 3
    d = ep.to_dict()
    assert {"reward", "steps", "reached_target", "fell", "descriptor", "seed"} <= set(d)


def test_evaluator_counts_interactions_against_budget(small_body, organism):
    ev = EmbodiedEvaluator(base_env=small_body, train_seeds=[1, 2], budget=10_000)
    assert not ev.exhausted
    fit, desc, eps = ev.evaluate_organism(organism)
    assert ev.interactions == sum(e.steps for e in eps)
    assert ev.interactions > 0
    assert desc.shape == (5,)
    assert np.isfinite(fit)
    ev.interactions = 10_000
    assert ev.exhausted


def test_evaluator_rejects_empty_seeds(small_body):
    with pytest.raises(ValueError):
        EmbodiedEvaluator(base_env=small_body, train_seeds=[], budget=100)
    with pytest.raises(ValueError):
        EmbodiedEvaluator(base_env=small_body, train_seeds=[1], budget=-1)


def test_evaluation_is_deterministic(small_body, organism):
    a = evaluate_embodied(small_body, organism, [11, 22])
    b = evaluate_embodied(small_body, organism, [11, 22])
    assert a["mean_reward"] == b["mean_reward"]
    assert a["mean_distance_travelled"] == b["mean_distance_travelled"]


def test_evaluate_embodied_reports_failure_metrics(small_body, organism):
    m = evaluate_embodied(small_body, organism, [1, 2, 3])
    assert {"mean_reward", "fall_rate", "target_rate", "mean_distance_travelled"} <= set(m)
    assert 0.0 <= m["fall_rate"] <= 1.0
    assert 0.0 <= m["target_rate"] <= 1.0


def test_episodes_do_not_leak_physics_clients(small_body, organism):
    """Every episode must disconnect its client, or a campaign exhausts the host."""
    import pybullet as p

    def connected_ids():
        ids = []
        for i in range(64):
            try:
                if p.isConnected(i):
                    ids.append(i)
            except Exception:
                pass
        return ids

    before = len(connected_ids())
    for s in range(12):
        run_embodied_episode(small_body, organism, seed=s)
    after = len(connected_ids())
    assert after <= before, f"leaked physics clients: {before} -> {after}"


def test_ga_optimises_a_physics_body(small_body):
    """The unmodified GA must run on the articulated body and consume the budget."""
    ev = EmbodiedEvaluator(base_env=small_body, train_seeds=[1, 2], budget=4_000)
    res = fixed_objective_ga(ev, small_body, seed=1, pop_size=6, max_generations=60)
    assert ev.interactions > 0
    assert res.best_organism is not None
    assert np.isfinite(res.best_fitness)
    # the evolved policy is evaluated on held-out seeds, not the training seeds
    held_out = evaluate_embodied(small_body, res.best_organism, [101, 202])
    assert np.isfinite(held_out["mean_reward"])


def test_transfer_reports_zero_shot_and_adaptation(small_body, organism):
    variants = embodied_morphology_variants(small_body)
    tr = transfer_embodied(
        organism,
        small_body,
        variants,
        seeds=[7, 8],
        train_seeds=[1, 2],
        adapt=True,
        adaptation_budget=1_500,
        seed=1,
    )
    assert isinstance(tr, EmbodiedTransferResult)
    assert set(tr.zero_shot) == set(variants)
    assert tr.adapted is not None and set(tr.adapted) == set(variants)
    assert tr.source["n_episodes"] == 2
    assert tr.zero_shot_mean is not None and np.isfinite(tr.zero_shot_mean)
    assert tr.adapted_mean is not None and np.isfinite(tr.adapted_mean)
    # adaptation must actually have spent interactions on the new body
    assert all(m["interactions"] > 0 for m in tr.adapted.values())
    assert tr.adaptation_budget == 1_500


def test_transfer_without_adaptation_leaves_adapted_none(small_body, organism):
    variants = embodied_morphology_variants(small_body)
    tr = transfer_embodied(organism, small_body, variants, seeds=[1], adapt=False)
    assert tr.adapted is None
    assert tr.adapted_mean is None
    assert tr.adaptation_budget == 0


def test_zero_shot_uses_the_unchanged_controller(small_body, organism):
    """Zero-shot must equal evaluating the same organism directly — no hidden training."""
    variants = embodied_morphology_variants(small_body)
    name = next(iter(variants))
    tr = transfer_embodied(organism, small_body, {name: variants[name]}, seeds=[5], adapt=False)
    direct = evaluate_embodied(variants[name], organism, [5])
    assert tr.zero_shot[name]["mean_reward"] == direct["mean_reward"]


def test_reward_requires_locomotion():
    """Regression guard: an idle policy must not collect reward for existing.

    A per-step 'existing' bonus once let a policy score ~+1.8 while travelling
    ~0 m. Now idling scores ~0 and covers no ground. That the task is *solvable*
    (a gait exists that nets forward displacement) is asserted separately in
    test_gait_primitive_produces_locomotion; that evolution finds a locomoting
    policy is measured in the embodied campaign, not here.
    """
    cfg = EmbodiedConfig.preset("centipede", n_links=10, episode_seconds=3.0)
    ev = EmbodiedEvaluator(base_env=cfg, train_seeds=[1], budget=0)
    idle_fit, _, eps = ev.evaluate_organism(_as_organism(_IdlePolicy(), cfg))
    assert idle_fit < 0.05, f"idling still collects reward: {idle_fit}"
    assert abs(eps[0].distance_travelled) < 1e-3, "idling should not travel"


class _IdlePolicy:
    def act(self, obs, env=None, deterministic=True, rng=None):
        return 4  # brake/hold


class _ProgramGait:
    """Cycles a fixed motor-primitive program."""

    def __init__(self, pattern):
        self.pattern = list(pattern)
        self.i = 0

    def act(self, obs, env=None, deterministic=True, rng=None):
        a = self.pattern[self.i % len(self.pattern)]
        self.i += 1
        return a


def _as_organism(policy, cfg):
    """Wrap an arbitrary policy in an Organism-shaped adapter for the evaluator."""
    org = Organism.random(Morphology(), cfg, np.random.default_rng(0))

    class _Adapter:
        def act(self, obs, env=None, deterministic=True, rng=None):
            return policy.act(obs, env, deterministic, rng)

    org.controller = _Adapter()  # type: ignore[assignment]
    return org


def test_creature_is_closed_even_when_the_policy_raises(small_body):
    class _Boom:
        def act(self, obs, env=None, deterministic=True, rng=None):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        run_embodied_episode(small_body, _Boom(), seed=1)
    # a subsequent episode must still work (no half-open client blocking us)
    env = EmbodiedCreature(EmbodiedConfig.from_dict(small_body.to_dict()))
    env.close()


def test_fallen_episodes_return_exactly_the_fall_penalty():
    """Every fallen episode returns exactly -fall_penalty regardless of how far
    the body travelled first: the "dash then crash" strategy is dominated.

    The redesigned yaw crawler is deliberately stable at rest, so a random
    eight-episode sample is no longer guaranteed to fall.  Forced-fall coverage
    lives in ``test_embodied.py``; this integration-level check verifies the
    invariant for any natural falls encountered here without making instability
    an accidental test requirement.
    """
    from origin.organisms.policies import RandomPolicy

    cfg = EmbodiedConfig.preset("worm", n_links=5, episode_seconds=3.0)
    for seed in range(1, 9):
        ep = run_embodied_episode(cfg, RandomPolicy(cfg.n_actions, seed=seed), seed=seed)
        assert not (ep.reached_target and ep.fell), "success and fall are mutually exclusive"
        if ep.fell:
            assert ep.reward == pytest.approx(-cfg.fall_penalty, abs=1e-9), (
                f"seed {seed}: fallen episode returned {ep.reward}, expected {-cfg.fall_penalty}"
            )


def test_transfer_refuses_adaptation_without_held_out_seeds(small_body, organism):
    """Adaptation must never train on the evaluation seeds (in-sample gains)."""
    variants = embodied_morphology_variants(small_body)
    with pytest.raises(ValueError, match="train_seeds"):
        transfer_embodied(
            organism, small_body, variants, seeds=[7, 8], adapt=True, adaptation_budget=100
        )
    with pytest.raises(ValueError, match="leakage"):
        transfer_embodied(
            organism, small_body, variants, seeds=[7, 8], train_seeds=[7, 11],
            adapt=True, adaptation_budget=100,
        )


def test_retention_is_source_body_performance_after_adaptation(small_body, organism):
    """Retention means: after adapting to a foreign body, how well does that
    controller still do on the *source* body — not its adapted foreign score."""
    variants = embodied_morphology_variants(small_body)
    name = next(iter(variants))
    tr = transfer_embodied(
        organism, small_body, {name: variants[name]}, seeds=[9, 10],
        train_seeds=[1, 2], adapt=True, adaptation_budget=800, seed=1,
    )
    assert tr.retention is not None and np.isfinite(tr.retention)
    assert tr.adapted_organisms, "adapted controllers must be kept for auditability"
    expected = float(np.mean([
        evaluate_embodied(small_body, org, [9, 10])["mean_reward"] for org in tr.adapted_organisms
    ]))
    assert tr.retention == pytest.approx(expected)


def test_baseline_evaluation_is_order_independent():
    """Per-episode reseeding: a stateful baseline's result on a given seed must
    not depend on which episodes ran before it (RNG/program counters must not
    carry over between episodes)."""
    from origin.organisms.policies import RandomPolicy

    cfg = EmbodiedConfig.preset("worm", n_links=5, episode_seconds=2.0)
    fresh = RandomPolicy(cfg.n_actions, seed=0)
    one = run_embodied_episode(cfg, fresh, seed=5)

    warmed = RandomPolicy(cfg.n_actions, seed=0)
    run_embodied_episode(cfg, warmed, seed=99)
    run_embodied_episode(cfg, warmed, seed=98)
    two = run_embodied_episode(cfg, warmed, seed=5)

    assert one.reward == pytest.approx(two.reward), "results depend on episode order"
    assert one.steps == two.steps
    assert one.descriptor == pytest.approx(two.descriptor)
