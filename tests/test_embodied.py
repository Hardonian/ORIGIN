"""Milestone 4 (embodied): articulated physics, determinism, transfer configs.

These exercise a real physics engine (PyBullet DIRECT), so they assert properties
that matter for a research platform: reproducibility, a fixed control interface
across body plans, and faithful state round-tripping.
"""

from __future__ import annotations

import numpy as np
import pytest

from origin.environments.embodied import (
    MORPHOLOGY_PRESETS,
    EmbodiedConfig,
    EmbodiedCreature,
    embodied_morphology_variants,
    embodied_perturbation_variants,
)

pytestmark = pytest.mark.embodied


@pytest.fixture(scope="module")
def tiny():
    # small/fast body plan for most tests
    return EmbodiedConfig.preset("worm", n_links=5, episode_seconds=2.0)


def _rollout(env, actions, seed=0):
    obs, info = env.reset(seed=seed)
    rewards, xs, terms = [], [], []
    for a in actions:
        obs, r, term, trunc, info = env.step(a)
        rewards.append(r)
        xs.append(info["position"][0])
        terms.append(term or trunc)
        if term or trunc:
            break
    return rewards, xs, terms


def test_every_preset_builds_and_steps():
    for name in MORPHOLOGY_PRESETS:
        env = EmbodiedCreature(EmbodiedConfig.preset(name, episode_seconds=1.0))
        obs, info = env.reset(seed=1)
        assert obs.shape == (7,)
        assert np.all(np.isfinite(obs)), f"{name} produced a non-finite observation"
        assert info["n_joints"] == MORPHOLOGY_PRESETS[name]["n_links"]
        obs, r, term, trunc, info = env.step(2)
        assert np.isfinite(r)
        env.close()


def test_fixed_control_interface_across_body_plans():
    """7-D observation and 5 actions regardless of link count (morphology transfer)."""
    for n_links in (3, 8, 14):
        env = EmbodiedCreature(EmbodiedConfig.preset("worm", n_links=n_links, episode_seconds=1.0))
        obs, _ = env.reset(seed=0)
        assert obs.shape == (7,), f"obs size changed with n_links={n_links}"
        assert env.action_space_n == 5
        assert env.observation_size == 7
        env.close()


def test_determinism_identical_trajectories(tiny):
    actions = [2, 3, 2, 3, 1, 0, 2, 3]

    def build():
        return EmbodiedCreature(EmbodiedConfig.from_dict(tiny.to_dict()))

    env_a, env_b = build(), build()
    ra, xa, _ = _rollout(env_a, actions, seed=7)
    rb, xb, _ = _rollout(env_b, actions, seed=7)
    assert ra == rb, "rewards diverged between identical runs"
    assert xa == xb, "positions diverged between identical runs"
    env_a.close()
    env_b.close()


def test_seeded_initial_jitter_is_reproducible_and_seed_dependent():
    cfg = EmbodiedConfig.preset("worm", n_links=4, episode_seconds=1.0, init_jitter=0.3)
    a = EmbodiedCreature(EmbodiedConfig.from_dict(cfg.to_dict()))
    b = EmbodiedCreature(EmbodiedConfig.from_dict(cfg.to_dict()))
    c = EmbodiedCreature(EmbodiedConfig.from_dict(cfg.to_dict()))
    ra, _, _ = _rollout(a, [2, 2, 2], seed=3)
    rb, _, _ = _rollout(b, [2, 2, 2], seed=3)
    rc, _, _ = _rollout(c, [2, 2, 2], seed=4)
    assert ra == rb, "same seed must reproduce"
    assert ra != rc, "a different seed must change the initial condition"
    for e in (a, b, c):
        e.close()


def test_action_validity(tiny):
    env = EmbodiedCreature(EmbodiedConfig.from_dict(tiny.to_dict()))
    env.reset(seed=0)
    with pytest.raises(ValueError):
        env.step(5)
    with pytest.raises(ValueError):
        env.step(-1)
    env.close()


def test_gait_primitive_produces_locomotion():
    """The embodied task must be solvable: some motor program produces net forward motion.

    Not tied to one hand-picked sequence — a different link count reverses the wave
    phase, so the test searches a small family of gaits and requires that at least
    one walks the creature forward.
    """
    env = EmbodiedCreature(EmbodiedConfig.preset("centipede", n_links=10, episode_seconds=3.0))
    programs = {
        "wave_23": [2, 3] * 40,
        "wave_32": [3, 2] * 40,
        "wave_223": [2, 2, 3] * 40,
        "extend": [1] * 80,
        "mixed": [2, 2, 3, 1, 0, 2, 3, 2, 1, 4] * 8,
    }
    gains = {}
    for name, actions in programs.items():
        fresh = EmbodiedCreature(EmbodiedConfig.preset("centipede", n_links=10, episode_seconds=3.0))
        _, xs, _ = _rollout(fresh, actions, seed=1)
        gains[name] = xs[-1] - xs[0]
        fresh.close()
    env.close()
    best, best_gain = max(gains.items(), key=lambda kv: kv[1])
    assert best_gain > 0.05, f"no gait moved the creature forward: {gains}"


def test_episode_termination_and_truncation(tiny):
    env = EmbodiedCreature(EmbodiedConfig.from_dict(tiny.to_dict()))
    env.reset(seed=0)
    steps = 0
    truncated = False
    for _ in range(env.config.max_steps + 5):
        _obs, _r, term, trunc, _info = env.step(4)
        steps += 1
        if term or trunc:
            truncated = trunc
            break
    assert steps <= env.config.max_steps + 1
    assert truncated or steps < env.config.max_steps + 1
    env.close()


def test_state_serialization_roundtrip(tiny):
    env = EmbodiedCreature(EmbodiedConfig.from_dict(tiny.to_dict()))
    env.reset(seed=2)
    for a in [1, 1, 2, 3]:
        env.step(a)
    state = env.get_state()
    clone = EmbodiedCreature(EmbodiedConfig.from_dict(tiny.to_dict()))
    clone.set_state(state)
    o1, r1, *_ = env.step(2)
    o2, r2, *_ = clone.step(2)
    assert abs(r1 - r2) < 1e-9, f"replay reward diverged: {r1} vs {r2}"
    assert np.allclose(o1, o2), "replay observation diverged"
    env.close()
    clone.close()


def test_state_rejects_wrong_version(tiny):
    env = EmbodiedCreature(EmbodiedConfig.from_dict(tiny.to_dict()))
    with pytest.raises(ValueError):
        env.set_state({"version": 99})
    env.close()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"morphology": "nope"},
        {"n_links": 0},
        {"link_length": 0.0},
        {"link_mass": -1.0},
        {"joint_max_torque": 0.0},
        {"joint_limit": 0.0},
        {"episode_seconds": 0.0},
        {"physics_dt": 0.0},
        {"physics_dt": 1.0, "control_dt": 0.1},
        {"target_tolerance": 0.0},
    ],
)
def test_invalid_configs_rejected(kwargs):
    with pytest.raises(ValueError):
        EmbodiedConfig(**kwargs)


def test_unknown_config_field_rejected():
    with pytest.raises(ValueError):
        EmbodiedConfig.from_dict({"morphology": "worm", "bogus": 1})


def test_morphology_and_perturbation_variants_are_distinct():
    base = EmbodiedConfig.preset("worm")
    morphs = embodied_morphology_variants(base)
    assert len(morphs) >= 3
    assert len({c.config_hash() for c in morphs.values()}) == len(morphs)
    # genuinely different bodies, not cosmetic
    assert {c.n_links for c in morphs.values()} != {base.n_links}
    assert len({c.link_mass for c in morphs.values()}) > 1
    perts = embodied_perturbation_variants(base)
    assert len(perts) >= 4
    assert len({c.config_hash() for c in perts.values()}) == len(perts)


def test_controller_transfers_to_a_different_body_without_shapes_breaking():
    """The whole point of a fixed interface: a policy can be driven on another body."""
    from origin.organisms.morphology import Morphology
    from origin.organisms.organism import Organism

    rng = np.random.default_rng(0)
    base = EmbodiedConfig.preset("worm")
    org = Organism.random(Morphology(), base, rng)  # input dim 7, 5 actions
    for cfg in embodied_morphology_variants(base).values():
        env = EmbodiedCreature(cfg)
        obs, _ = env.reset(seed=0)
        for _ in range(5):
            action = org.act(obs)  # no shape error across body plans
            obs, _r, term, trunc, _info = env.step(action)
            if term or trunc:
                break
        env.close()


# ---------------------------------------------------------------------- #
# Task semantics: "reach the target while upright"
# ---------------------------------------------------------------------- #
def _tip_over(env):
    """Force a fall through the public state API: pitch the base ~2.4 rad about y."""
    state = env.get_state()
    state["base_orientation"] = [0.0, 0.93204, 0.0, 0.36236]  # (x, y, z, w)
    state["base_linear_velocity"] = [0.0, 0.0, 0.0]
    state["base_angular_velocity"] = [0.0, 0.0, 0.0]
    env.set_state(state)


def _place_at_target(env):
    """Move the base onto the target, keeping it upright, via the public state API."""
    state = env.get_state()
    state["base_position"] = [float(env.config.target_distance), 0.0, float(env._rest_z)]
    state["base_orientation"] = [0.0, 0.0, 0.0, 1.0]
    state["base_linear_velocity"] = [0.0, 0.0, 0.0]
    state["base_angular_velocity"] = [0.0, 0.0, 0.0]
    env.set_state(state)


def test_fall_cancels_banked_shaping(tiny):
    """A fallen episode returns exactly -fall_penalty.

    Regression guard for the "dash toward the target then face-plant" exploit:
    progress shaping banked before a fall must be cancelled, so a controller can
    never outscore upright locomotion by travelling far and falling over.
    """
    cfg = EmbodiedConfig.from_dict(tiny.to_dict())
    env = EmbodiedCreature(cfg)
    env.reset(seed=0)
    total = 0.0
    for _ in range(3):
        _obs, r, term, trunc, info = env.step(2)  # travelling wave: banks shaping
        assert not (term or trunc), "warm-up terminated unexpectedly"
        assert info["upright"], "warm-up fell unexpectedly"
        total += r
    assert env._banked != 0.0, "warm-up banked no shaping; the forfeit would be vacuous"
    banked = env._banked

    _tip_over(env)
    _obs, r, term, trunc, info = env.step(2)
    assert term and not trunc, "a fall must terminate the episode"
    assert not info["upright"] and not info["success"]
    total += r
    assert total == pytest.approx(-cfg.fall_penalty, abs=1e-9), (
        f"fallen episode returned {total}, expected exactly {-cfg.fall_penalty} "
        f"(banked shaping of {banked} must be forfeited)"
    )
    env.close()


def test_success_requires_arriving_upright(tiny):
    """The task is solved only by reaching the target *while upright*."""
    cfg = EmbodiedConfig.from_dict(tiny.to_dict())

    env = EmbodiedCreature(cfg)
    env.reset(seed=0)
    _place_at_target(env)
    _obs, r, term, trunc, info = env.step(4)
    assert info["success"], "upright arrival at the target must count as success"
    assert term
    assert r >= cfg.target_reward - 1.0, f"success reward missing: {r}"
    env.close()

    env = EmbodiedCreature(cfg)
    env.reset(seed=0)
    _place_at_target(env)
    _tip_over(env)
    _obs, r, term, trunc, info = env.step(4)
    assert not info["success"], "falling onto the target must not count as success"
    assert term, "the fall must terminate the episode"
    assert r == pytest.approx(-cfg.fall_penalty, abs=1e-9), f"fallen episode returned {r}"
    env.close()


def test_state_round_trip_preserves_the_fall_forfeit(tiny):
    """get_state/set_state must carry the banked shaping, or a replayed fall
    would return a different reward than the original rollout."""
    cfg = EmbodiedConfig.from_dict(tiny.to_dict())
    env = EmbodiedCreature(cfg)
    env.reset(seed=0)
    for _ in range(2):
        env.step(2)

    clone = EmbodiedCreature(EmbodiedConfig.from_dict(tiny.to_dict()))
    clone.set_state(env.get_state())
    _tip_over(env)
    _tip_over(clone)
    _o1, r1, *_ = env.step(2)
    _o2, r2, *_ = clone.step(2)
    assert abs(r1 - r2) < 1e-9, f"replayed fall diverged: {r1} vs {r2}"
    env.close()
    clone.close()


def test_reset_does_not_mutate_the_callers_config(tiny):
    """The env owns its config: reset(seed=...) must not write into a shared one
    (a mutated shared config makes unrelated runs depend on each other)."""
    cfg = EmbodiedConfig.from_dict(tiny.to_dict())
    before = cfg.seed
    env = EmbodiedCreature(cfg)
    env.reset(seed=12345)
    assert cfg.seed == before, "shared config was mutated by reset"
    assert env.config.seed == 12345, "env did not record the active seed"
    env.close()
