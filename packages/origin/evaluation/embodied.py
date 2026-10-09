"""Milestone 4 (embodied): evaluate and transfer controllers across physical bodies.

The optimizers are simulator-agnostic: they need an object exposing
``exhausted`` / ``interactions`` / ``budget`` / ``train_seeds`` and an
``evaluate_organism(org) -> (fitness, descriptor, results)`` method. This module
supplies exactly that for the articulated-physics environment, so GA, novelty
search and MAP-Elites run against a real physics engine unchanged.

Two distinct questions are kept separate, because conflating them is the classic
way morphology-transfer results get overstated:

* **zero-shot transfer** — performance on a new body with *no* further training
* **adaptation**       — performance after a fixed interaction budget on the new body
* **retention**        — performance back on the original body afterwards
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from origin.environments.embodied import EmbodiedConfig, EmbodiedCreature
from origin.evolution.adapt import fine_tune
from origin.organisms.organism import Organism


@dataclass
class EmbodiedEpisode:
    reward: float
    steps: int
    reached_target: bool
    fell: bool
    distance_travelled: float
    energy: float
    descriptor: list[float]
    seed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "reward": self.reward,
            "steps": self.steps,
            "reached_target": self.reached_target,
            "fell": self.fell,
            "distance_travelled": self.distance_travelled,
            "energy": self.energy,
            "descriptor": list(self.descriptor),
            "seed": self.seed,
        }


def run_embodied_episode(
    config: EmbodiedConfig,
    policy: Any,
    seed: int | None = None,
    record_trace: bool = False,
) -> EmbodiedEpisode | tuple[EmbodiedEpisode, dict[str, Any]]:
    """One episode of the articulated body driven by ``policy``.

    The creature is always closed, including on failure — a leaked PyBullet client
    per episode would otherwise exhaust the machine over a campaign.
    """
    env = EmbodiedCreature(config)
    try:
        obs, info = env.reset(seed=seed)
        # The effective seed is whatever the env recorded (reset(None) keeps the
        # config seed); the result must report the seed the episode actually ran.
        used_seed = int(seed if seed is not None else env.config.seed)
        # Per-episode reseeding keeps baseline results independent of episode
        # order (a stateful policy's RNG/program counter must not carry over).
        reset_policy = getattr(policy, "reset", None)
        if callable(reset_policy):
            reset_policy(used_seed)
        total = 0.0
        steps = 0
        done = False
        terminated = truncated = False
        trace: dict[str, Any] = {"actions": [], "rewards": [], "initial_state": env.get_state()}
        while not done:
            try:
                action = int(policy.act(obs, env=env))
            except TypeError:
                action = int(policy.act(obs))
            if record_trace:
                trace["actions"].append(action)
            obs, r, terminated, truncated, info = env.step(action)
            if record_trace:
                trace["rewards"].append(r)
            total += r
            steps += 1
            done = terminated or truncated
        reached = bool(info["success"])  # reached the target *while upright*
        fell = not bool(info["upright"])
        res = EmbodiedEpisode(
            reward=float(total),
            steps=int(steps),
            reached_target=bool(reached),
            fell=bool(fell),
            distance_travelled=float(info["distance_travelled"]),
            energy=float(info["energy"]),
            descriptor=list(info["descriptor"]),
            seed=used_seed,
        )
        return (res, trace) if record_trace else res
    finally:
        env.close()


@dataclass
class EmbodiedEvaluator:
    """Simulator-agnostic evaluator over articulated bodies (see module docstring)."""

    base_env: EmbodiedConfig
    train_seeds: list[int]
    interactions: int = 0
    budget: int = 0

    def __post_init__(self) -> None:
        if not self.train_seeds:
            raise ValueError("train_seeds must be non-empty")
        if self.budget < 0:
            raise ValueError("budget must be >= 0")

    @property
    def exhausted(self) -> bool:
        return self.budget > 0 and self.interactions >= self.budget

    def can_consume(self, steps: int) -> bool:
        """Whether an algorithm may reserve ``steps`` more control steps."""
        if steps < 0:
            raise ValueError("steps must be >= 0")
        return self.budget <= 0 or self.interactions + steps <= self.budget

    def can_evaluate(self, seeds: list[int] | None = None, *, count: int = 1) -> bool:
        """Whether ``count`` complete physics evaluations fit without overshoot."""
        if count < 1:
            raise ValueError("count must be >= 1")
        episode_seeds = self.train_seeds if seeds is None else seeds
        if not episode_seeds:
            raise ValueError("seeds must be non-empty")
        return self.can_consume(count * len(episode_seeds) * int(self.base_env.max_steps))

    def evaluate_organism(
        self,
        org: Organism,
        seeds: list[int] | None = None,
    ) -> tuple[float, np.ndarray, list[EmbodiedEpisode]]:
        seeds = seeds if seeds is not None else self.train_seeds
        if not self.can_evaluate(seeds):
            raise RuntimeError(
                f"full evaluation of {len(seeds)} episode(s) does not fit remaining budget "
                f"({self.budget - self.interactions} steps)"
            )
        rewards: list[float] = []
        descs: list[np.ndarray] = []
        episodes: list[EmbodiedEpisode] = []
        for s in seeds:
            ep = run_embodied_episode(self.base_env, org, seed=s)
            assert isinstance(ep, EmbodiedEpisode)
            self.interactions += ep.steps
            rewards.append(ep.reward)
            descs.append(np.asarray(ep.descriptor, dtype=np.float64))
            episodes.append(ep)
        return float(np.mean(rewards)), np.mean(descs, axis=0), episodes


def evaluate_embodied(
    config: EmbodiedConfig,
    policy: Any,
    seeds: list[int],
) -> dict[str, Any]:
    """Evaluate any policy (organism, scripted gait, random) on body ``config``."""
    rewards, descs, steps, fell, reached, travelled = [], [], [], [], [], []
    for s in seeds:
        ep = run_embodied_episode(config, policy, seed=s)
        assert isinstance(ep, EmbodiedEpisode)
        rewards.append(ep.reward)
        descs.append(np.asarray(ep.descriptor))
        steps.append(ep.steps)
        fell.append(float(ep.fell))
        reached.append(float(ep.reached_target))
        travelled.append(ep.distance_travelled)
    n = len(seeds)
    return {
        "n_episodes": n,
        "mean_reward": float(np.mean(rewards)),
        "std_reward": float(np.std(rewards)),
        "mean_steps": float(np.mean(steps)),
        "fall_rate": float(np.mean(fell)),
        # Fraction of episodes that reached the target *while upright*: the task
        # success rate (an episode can also time out upright without success).
        "target_rate": float(np.mean(reached)),
        "mean_distance_travelled": float(np.mean(travelled)),
        "mean_descriptor": np.mean(descs, axis=0).tolist(),
        "interactions": int(np.sum(steps)),
    }


@dataclass
class EmbodiedTransferResult:
    """Source performance, zero-shot transfer, optional adaptation and retention."""

    source: dict[str, Any]
    zero_shot: dict[str, dict[str, Any]]
    adapted: dict[str, dict[str, Any]] | None = None
    # Kept so retention is auditable: the controllers adapted to each foreign
    # body, re-scored on the source body below.
    adapted_organisms: list[Organism] | None = None
    retention: float | None = None
    zero_shot_mean: float | None = None
    adapted_mean: float | None = None
    adaptation_budget: int = 0


def transfer_embodied(
    organism: Organism,
    base_config: EmbodiedConfig,
    variants: dict[str, EmbodiedConfig],
    seeds: list[int],
    train_seeds: list[int] | None = None,
    adapt: bool = False,
    adaptation_budget: int = 0,
    adapt_seeds: list[int] | None = None,
    seed: int = 0,
) -> EmbodiedTransferResult:
    """Measure transfer of one controller across a set of distinct bodies.

    ``seeds`` are held-out evaluation seeds; ``train_seeds`` drive any adaptation
    (they must be disjoint from ``seeds``), so evaluation stays on unseen seeds.
    Adaptation without explicit held-out ``train_seeds`` is refused rather than
    quietly trained on the evaluation seeds.
    """
    if adapt and adaptation_budget > 0:
        if train_seeds is None:
            raise ValueError(
                "adaptation requires train_seeds: adapting on the held-out eval "
                "seeds would make the adapted score in-sample"
            )
        leakage = set(train_seeds) & set(seeds)
        if leakage:
            raise ValueError(f"train/test seed leakage: {sorted(leakage)}")
    adapt_seeds = adapt_seeds if adapt_seeds is not None else (train_seeds or seeds)

    source = evaluate_embodied(base_config, organism, seeds)
    zero_shot = {name: evaluate_embodied(cfg, organism, seeds) for name, cfg in variants.items()}

    adapted: dict[str, dict[str, Any]] | None = None
    adapted_organisms: list[Organism] = []
    retention: float | None = None
    adapted_mean: float | None = None

    if adapt and adaptation_budget > 0:
        adapted = {}
        for name, cfg in variants.items():
            ev = EmbodiedEvaluator(base_env=cfg, train_seeds=adapt_seeds, budget=adaptation_budget)
            result = fine_tune(
                organism,
                cfg,  # type: ignore[arg-type]
                seed=seed,
                budget=adaptation_budget,
                seeds=adapt_seeds,
                pop_size=8,
                mutation_rate=0.3,
                mutation_scale=0.35,
                evaluator_factory=lambda cfg=cfg, ev=ev: ev,
            )
            assert result.best_organism is not None
            adapted_organisms.append(result.best_organism)
            adapted[name] = evaluate_embodied(cfg, result.best_organism, seeds)
            adapted[name]["interactions"] = int(ev.interactions)
        adapted_mean = float(np.mean([m["mean_reward"] for m in adapted.values()]))
        # Retention: after adapting to each foreign body, how well does that
        # adapted controller still perform on the *source* body (held-out seeds)?
        retention = float(np.mean([
            evaluate_embodied(base_config, org, seeds)["mean_reward"] for org in adapted_organisms
        ]))

    return EmbodiedTransferResult(
        source=source,
        zero_shot=zero_shot,
        adapted=adapted,
        adapted_organisms=adapted_organisms if adapted else None,
        retention=retention,
        zero_shot_mean=float(np.mean([m["mean_reward"] for m in zero_shot.values()])),
        adapted_mean=adapted_mean,
        adaptation_budget=adaptation_budget if adapt else 0,
    )
