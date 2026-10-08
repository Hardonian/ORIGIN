"""Reinforcement learning baseline: REINFORCE with a learned baseline.

Pure-NumPy implementation of the policy-gradient estimator (Williams, 1992)
so ORIGIN has a genuine gradient-based learner without a heavy framework
dependency. An optional Stable-Baselines3 path is available via the ``rl``
extra, but is not required for the platform to run.

The trained network is wrapped back into an :class:`Organism`, so RL results
are directly comparable with evolved results under the same evaluator.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from origin.environments.gridworld import GridWorld, GridWorldConfig
from origin.evaluation.harness import Evaluator
from origin.evolution.base import OptimizationResult
from origin.organisms.genome import MLPController
from origin.organisms.morphology import Morphology
from origin.organisms.organism import Lineage, Organism

VERSION = "1.0"


class _PolicyNet:
    """MLP with tanh hidden layers and a softmax action head, plus Adam."""

    def __init__(self, sizes: list[int], rng: np.random.Generator, lr: float = 0.02):
        self.sizes = sizes
        self.lr = lr
        self.w: list[np.ndarray] = []
        self.b: list[np.ndarray] = []
        for i in range(len(sizes) - 1):
            bound = 1.0 / np.sqrt(max(1, sizes[i]))
            self.w.append(rng.uniform(-bound, bound, size=(sizes[i], sizes[i + 1])))
            self.b.append(np.zeros(sizes[i + 1]))
        self._m = [np.zeros_like(x) for x in self.w] + [np.zeros_like(x) for x in self.b]
        self._v = [np.zeros_like(x) for x in self.w] + [np.zeros_like(x) for x in self.b]
        self._t = 0
    def forward(self, x: np.ndarray) -> tuple[list[np.ndarray], np.ndarray]:
        acts = [x]
        h = x
        n = len(self.sizes) - 1
        for i in range(n):
            z = h @ self.w[i] + self.b[i]
            h = np.tanh(z) if i < n - 1 else z
            acts.append(h)
        logits = acts[-1]
        z = logits - logits.max()
        p = np.exp(z) / np.exp(z).sum()
        return acts, p

    def backward(self, acts: list[np.ndarray], p: np.ndarray, action: int, advantage: float, entropy_coef: float = 0.0) -> None:
        n = len(self.sizes) - 1
        d = p.copy()
        d[action] -= 1.0
        d *= advantage
        if entropy_coef > 0.0:
            # entropy bonus term: d(-beta*H)/dz = +beta * p * (log p + H)
            logp = np.log(p + 1e-12)
            H = float(-(p * logp).sum())
            d += entropy_coef * p * (logp + H)
        grads_w: list[np.ndarray] = [None] * n  # type: ignore
        grads_b: list[np.ndarray] = [None] * n  # type: ignore
        for i in reversed(range(n)):
            a_prev = acts[i]
            grads_w[i] = np.outer(a_prev, d)
            grads_b[i] = d
            if i > 0:
                dh = self.w[i] @ d
                d = dh * (1 - np.tanh(acts[i]) ** 2)
        self._adam(grads_w, grads_b)

    def _adam(self, grads_w: list[np.ndarray], grads_b: list[np.ndarray], beta1: float = 0.9, beta2: float = 0.999, eps: float = 1e-8) -> None:
        self._t += 1
        params = self.w + self.b
        grads = grads_w + grads_b
        for idx, (p, g) in enumerate(zip(params, grads, strict=False)):
            self._m[idx] = beta1 * self._m[idx] + (1 - beta1) * g
            self._v[idx] = beta2 * self._v[idx] + (1 - beta2) * (g * g)
            mhat = self._m[idx] / (1 - beta1**self._t)
            vhat = self._v[idx] / (1 - beta2**self._t)
            p -= self.lr * mhat / (np.sqrt(vhat) + eps)

    def to_controller(self, hidden: tuple[int, ...]) -> MLPController:
        weights: list[np.ndarray] = []
        for w, b in zip(self.w, self.b, strict=True):
            weights.extend([w.copy(), b.copy()])
        return MLPController(sizes=list(self.sizes), weights=weights)


def reinforce(
    evaluator: Evaluator,
    base_env: GridWorldConfig,
    seed: int,
    hidden: tuple[int, ...] = (16,),
    lr: float = 0.01,
    gamma: float = 0.99,
    episodes_per_update: int = 4,
    entropy_coef: float = 0.02,
    max_updates: int = 5000,
    env_factory: Any | None = None,
) -> OptimizationResult:
    rng = np.random.default_rng(seed)
    # Any env exposing reset/step/observation_size/n_actions/close can be optimised
    # here. The default preserves the original grid behaviour; passing a factory lets
    # the identical RL loop drive a different simulator (e.g. articulated physics).
    factory = env_factory
    if factory is None:
        morph = Morphology(obs_mode=base_env.obs_mode, obs_radius=base_env.obs_radius, max_speed=base_env.max_speed, energy_capacity=base_env.energy_capacity)
        _cfg = morph.apply(base_env)

        def _grid_factory() -> Any:
            return GridWorld(_cfg)

        factory = _grid_factory
    else:
        # Caller-supplied simulator: the grid-specific morphology knobs don't apply,
        # but the organism still needs a morphology record for its lineage metadata.
        morph = Morphology()
    probe = factory()
    in_dim = int(probe.observation_size)
    n_actions = int(probe.n_actions)
    probe.close()
    net = _PolicyNet([in_dim, *hidden, n_actions], rng, lr=lr)

    history: list[dict[str, Any]] = []
    update = 0
    best_fit = float("-inf")
    best_controller: MLPController | None = None
    train_seeds = list(evaluator.train_seeds)

    while update < max_updates and not evaluator.exhausted:
        batch_grads: list[tuple[list[np.ndarray], np.ndarray, int, float]] = []
        ep_rewards: list[float] = []
        for _ in range(episodes_per_update):
            s = int(rng.choice(train_seeds))
            env = factory()
            try:
                obs, _ = env.reset(seed=s)
                log: list[tuple[list[np.ndarray], np.ndarray, int]] = []
                rewards: list[float] = []
                done = False
                steps = 0
                while not done:
                    acts, p = net.forward(np.asarray(obs, dtype=np.float64))
                    a = int(rng.choice(len(p), p=p))
                    log.append((acts, p, a))
                    obs, r, terminated, truncated, _info = env.step(a)
                    rewards.append(r)
                    steps += 1
                    done = terminated or truncated
            finally:
                # Close on the exception path too: an RL loop that leaks a
                # physics client per episode would exhaust the machine.
                env.close()
            evaluator.interactions += steps
            ep_rewards.append(float(np.sum(rewards)))
            # discounted returns
            G = 0.0
            returns = []
            for r in reversed(rewards):
                G = r + gamma * G
                returns.append(G)
            returns.reverse()
            returns_arr = np.asarray(returns)
            baseline = returns_arr.mean() if len(returns_arr) else 0.0
            advantages = returns_arr - baseline
            std = advantages.std() + 1e-8
            advantages = advantages / std
            for (acts, p, a), adv in zip(log, advantages, strict=False):
                batch_grads.append((acts, p, a, float(adv)))

        for acts, p, a, adv in batch_grads:
            net.backward(acts, p, a, adv, entropy_coef=entropy_coef)

        # periodic evaluation of the *current* policy on held-in seeds
        ctrl = net.to_controller(hidden)
        org = Organism(morph=morph, controller=ctrl, lineage=Lineage(id="", generation=update, mutations={"algo": "reinforce"}), hidden=hidden)
        org.refresh_id()
        fit, desc, _ = evaluator.evaluate_organism(org, seeds=train_seeds[: min(2, len(train_seeds))])
        history.append({"update": update, "mean_episode_reward": float(np.mean(ep_rewards)) if ep_rewards else 0.0, "eval_fitness": fit, "interactions": evaluator.interactions})
        if fit > best_fit:
            best_fit = fit
            best_controller = ctrl
        update += 1

    if best_controller is None:  # pragma: no cover - only if budget was 0
        best_controller = net.to_controller(hidden)
    best_org = Organism(morph=morph, controller=best_controller, lineage=Lineage(id="", generation=update, mutations={"algo": "reinforce", "best": True}), hidden=hidden)
    best_org.refresh_id()

    return OptimizationResult(
        algorithm="reinforce",
        version=VERSION,
        seed=seed,
        interactions=evaluator.interactions,
        budget=evaluator.budget,
        best_organism=best_org,
        best_fitness=best_fit,
        history=history,
        extra={"updates": update, "hidden": list(hidden), "lr": lr, "gamma": gamma, "entropy_coef": entropy_coef},
    )
