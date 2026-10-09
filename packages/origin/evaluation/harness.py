"""Evaluation harness: episode execution, aggregation, and interaction budgets.

Every algorithm and every reported metric flows through this module so that
"interactions" is a single, consistent unit (environment ``step`` calls).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from origin.environments.gridworld import GridWorld, GridWorldConfig
from origin.organisms.organism import Organism


class Policy(Protocol):
    def act(self, obs: np.ndarray, env: GridWorld | None = ..., deterministic: bool = ...) -> int: ...


@dataclass
class EpisodeResult:
    reward: float
    steps: int
    collected: int
    hazard_hits: int
    terminated: bool
    truncated: bool
    descriptor: list[float]
    seed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "reward": self.reward,
            "steps": self.steps,
            "collected": self.collected,
            "hazard_hits": self.hazard_hits,
            "terminated": self.terminated,
            "truncated": self.truncated,
            "descriptor": list(self.descriptor),
            "seed": self.seed,
        }


def _call(policy: Any, obs: np.ndarray, env: GridWorld, rng: np.random.Generator | None) -> int:
    """Invoke a policy that is either an Organism or an ``act(obs, env=...)`` object."""
    try:
        return int(policy.act(obs, env=env))
    except TypeError:
        return int(policy.act(obs))


def run_episode(env: GridWorld, policy: Any, seed: int | None = None, record_trace: bool = False) -> EpisodeResult | tuple[EpisodeResult, dict[str, Any]]:
    obs, info = env.reset(seed=seed)
    # Per-episode reseeding keeps baseline results independent of episode order
    # (a stateful policy's RNG/program counter must not carry over).
    reset_policy = getattr(policy, "reset", None)
    if callable(reset_policy):
        reset_policy(seed if seed is not None else 0)
    total = 0.0
    steps = 0
    done = False
    terminated = truncated = False
    trace: dict[str, Any] = {"actions": [], "rewards": [], "initial_state": env.get_state()}
    rng = np.random.default_rng(seed if seed is not None else 0)
    while not done:
        a = _call(policy, obs, env, rng)
        if record_trace:
            trace["actions"].append(a)
        obs, r, terminated, truncated, info = env.step(a)
        if record_trace:
            trace["rewards"].append(r)
        total += r
        steps += 1
        done = terminated or truncated
    res = EpisodeResult(
        reward=float(total),
        steps=steps,
        collected=int(info["collected"]),
        hazard_hits=int(info["hazard_hits"]),
        terminated=bool(terminated),
        truncated=bool(truncated),
        descriptor=list(info["descriptor"]),
        seed=seed if seed is not None else 0,
    )
    return (res, trace) if record_trace else res


@dataclass
class Evaluator:
    """Counts environment interactions and evaluates organisms on seed sets."""

    base_env: GridWorldConfig
    train_seeds: list[int]
    interactions: int = 0
    budget: int = 0

    def __post_init__(self) -> None:
        if not self.train_seeds:
            raise ValueError("train_seeds must be non-empty")

    @property
    def exhausted(self) -> bool:
        return self.budget > 0 and self.interactions >= self.budget

    def evaluate_organism(self, org: Organism, seeds: list[int] | None = None) -> tuple[float, np.ndarray, list[EpisodeResult]]:
        seeds = seeds if seeds is not None else self.train_seeds
        rewards: list[float] = []
        descs: list[np.ndarray] = []
        results: list[EpisodeResult] = []
        for s in seeds:
            env = org.make_env(self.base_env, seed=s)
            ep = run_episode(env, org, seed=s)
            assert isinstance(ep, EpisodeResult)
            self.interactions += ep.steps
            rewards.append(ep.reward)
            descs.append(np.asarray(ep.descriptor, dtype=np.float64))
            results.append(ep)
        return float(np.mean(rewards)), np.mean(descs, axis=0), results


def evaluate_policy(env_config: GridWorldConfig, policy: Any, seeds: list[int]) -> dict[str, Any]:
    """Evaluate any policy (organism, heuristic, random) on a set of seeds."""
    rewards, descs, steps, collected, haz = [], [], [], [], []
    for s in seeds:
        env = GridWorld(env_config)
        ep = run_episode(env, policy, seed=s)
        assert isinstance(ep, EpisodeResult)
        rewards.append(ep.reward)
        descs.append(np.asarray(ep.descriptor))
        steps.append(ep.steps)
        collected.append(ep.collected)
        haz.append(ep.hazard_hits)
    return {
        "n_episodes": len(seeds),
        "mean_reward": float(np.mean(rewards)),
        "std_reward": float(np.std(rewards)),
        "mean_steps": float(np.mean(steps)),
        "mean_collected": float(np.mean(collected)),
        "mean_hazard_hits": float(np.mean(haz)),
        "mean_descriptor": np.mean(descs, axis=0).tolist(),
        "interactions": int(np.sum(steps)),
    }


# ---------------------------------------------------------------------- #
# Morphology transfer (Milestone 4)
# ---------------------------------------------------------------------- #
@dataclass
class TransferResult:
    source: dict[str, Any]
    zero_shot: dict[str, Any]
    adapted: dict[str, Any] | None = None
    retention: float | None = None
    morphology_hash: str = ""


def morphology_variants(base: GridWorldConfig) -> dict[str, GridWorldConfig]:
    """Genuinely distinct sensor/actuator/body configurations.

    The control interface stays 7-D in every case; what changes is sensor
    fidelity (``obs_mode``), actuation (``max_speed``) and body (``energy_capacity``).
    """
    variants: dict[str, GridWorldConfig] = {}

    c = GridWorldConfig.from_dict(base.to_dict())
    c.obs_mode, c.obs_radius = "local", 2
    variants["sensor_local"] = c

    c = GridWorldConfig.from_dict(base.to_dict())
    c.obs_mode = "nonspatial"
    variants["sensor_nonspatial"] = c

    c = GridWorldConfig.from_dict(base.to_dict())
    c.max_speed, c.energy_capacity = 2, 150.0
    variants["body_fast"] = c

    c = GridWorldConfig.from_dict(base.to_dict())
    c.max_speed, c.energy_capacity = 1, 60.0
    variants["body_small"] = c

    return variants


def perturbation_variants(base: GridWorldConfig) -> dict[str, GridWorldConfig]:
    """Environmental perturbations used in transfer tests."""
    variants: dict[str, GridWorldConfig] = {}
    mutations: dict[str, dict[str, object]] = {
        "obs_sparse": {"obstacle_density": 0.25},
        "resource_scarce": {"n_resources": 2},
        "hazard_dense": {"n_hazards": 16, "hazard_penalty": 2.0},
        "rooms": {"terrain": "rooms"},
        "slow_actuator": {"max_speed": 1, "energy_step": 0.3},
    }
    for name, mut in mutations.items():
        c = GridWorldConfig.from_dict(base.to_dict())
        for k, v in mut.items():
            setattr(c, k, v)
        variants[name] = c
    return variants


def multi_niche_variants(base: GridWorldConfig) -> dict[str, GridWorldConfig]:
    """Ecological niche shifts and trade-off variations for multi-niche transfer evaluation.

    Every returned configuration is revalidated after mutation; callers can
    safely use the variants with small test worlds as well as campaign-sized
    worlds.
    """
    variants: dict[str, GridWorldConfig] = {}
    tot_res = base.n_resources + base.n_resources_b
    capacity = max(1, base.height * base.width - base.n_hazards - 1)

    # Variant 1: Niche B only (Niche A resources completely depleted)
    c1 = GridWorldConfig.from_dict(base.to_dict())
    c1.n_resources = 0
    c1.n_resources_b = min(max(2, tot_res), capacity)
    variants["niche_b_only"] = c1

    # Variant 2: Niche A only (Niche B resources completely depleted)
    c2 = GridWorldConfig.from_dict(base.to_dict())
    c2.n_resources = min(max(2, tot_res), capacity)
    c2.n_resources_b = 0
    variants["niche_a_only"] = c2

    # Variant 3: Payoff inversion (Niche A becomes lucrative, Niche B becomes marginal)
    c3 = GridWorldConfig.from_dict(base.to_dict())
    c3.resource_reward, c3.resource_b_reward = base.resource_b_reward, base.resource_reward
    c3.resource_energy, c3.resource_b_energy = base.resource_b_energy, base.resource_energy
    variants["niche_payoff_swap"] = c3

    # Variant 4: Toxic Niche B (Hazard dense terrain surrounding high-yield resources)
    c4 = GridWorldConfig.from_dict(base.to_dict())
    max_h = max(0, c4.height * c4.width - c4.n_resources - c4.n_resources_b - 1)
    c4.n_hazards = min(max_h, max(base.n_hazards * 2, 12))
    c4.hazard_penalty = base.hazard_penalty * 2.0
    variants["niche_toxic_hazard"] = c4

    # Variant 5: Scarcity shock (resource availability slashed by 50%)
    c5 = GridWorldConfig.from_dict(base.to_dict())
    c5.n_resources = max(1, base.n_resources // 2)
    c5.n_resources_b = max(1, base.n_resources_b // 2)
    variants["niche_scarcity_shock"] = c5

    for variant in variants.values():
        variant.validate()
    return variants
