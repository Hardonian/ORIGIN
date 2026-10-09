"""Proximal Policy Optimization (PPO) Actor-Critic baseline.

Pure-NumPy implementation of clipped PPO (Schulman et al., 2017) with Generalized
Advantage Estimation (GAE; Schulman et al., 2015) and Adam optimization.

Like the REINFORCE baseline, PPO requires zero heavy framework dependencies (no
torch/tensorflow), operates under the exact interaction currency of the ORIGIN
evaluator, and exports its trained Actor weights directly to an :class:`Organism`.
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


class _ActorNet:
    """MLP with tanh hidden layers and a softmax categorical action head."""

    def __init__(self, sizes: list[int], rng: np.random.Generator, lr: float = 0.005):
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
        z = logits - np.max(logits)
        exp_z = np.exp(z)
        p = exp_z / np.sum(exp_z)
        return acts, p

    def backward(
        self,
        acts: list[np.ndarray],
        p: np.ndarray,
        action: int,
        old_prob: float,
        advantage: float,
        clip_eps: float = 0.2,
        entropy_coef: float = 0.01,
    ) -> None:
        """PPO clipped policy gradient update."""
        n = len(self.sizes) - 1
        prob_a = float(p[action])
        ratio = prob_a / max(1e-12, old_prob)

        # Check clipping condition
        clipped_ratio = np.clip(ratio, 1.0 - clip_eps, 1.0 + clip_eps)
        surr1 = ratio * advantage
        surr2 = clipped_ratio * advantage

        # Gradient flow: only non-zero if unclipped or if clipping bound is not active
        if surr1 <= surr2 or (advantage >= 0 and ratio < 1.0 + clip_eps) or (advantage < 0 and ratio > 1.0 - clip_eps):
            # Objective J is to be maximized; loss L = -J to be minimized
            # d(-ratio * adv)/dz = adv * ratio * (p - e_a)
            d = ratio * advantage * p.copy()
            d[action] -= ratio * advantage
        else:
            d = np.zeros_like(p)

        if entropy_coef > 0.0:
            # Entropy bonus: d(-c_e * H)/dz = c_e * p * (log p + H)
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
                d = dh * (1.0 - acts[i] ** 2)

        self._adam(grads_w, grads_b)

    def _adam(
        self,
        grads_w: list[np.ndarray],
        grads_b: list[np.ndarray],
        beta1: float = 0.9,
        beta2: float = 0.999,
        eps: float = 1e-8,
    ) -> None:
        self._t += 1
        params = self.w + self.b
        grads = grads_w + grads_b
        for idx, (param, g) in enumerate(zip(params, grads, strict=False)):
            self._m[idx] = beta1 * self._m[idx] + (1.0 - beta1) * g
            self._v[idx] = beta2 * self._v[idx] + (1.0 - beta2) * (g * g)
            mhat = self._m[idx] / (1.0 - beta1**self._t)
            vhat = self._v[idx] / (1.0 - beta2**self._t)
            param -= self.lr * mhat / (np.sqrt(vhat) + eps)

    def to_controller(self, hidden: tuple[int, ...]) -> MLPController:
        weights: list[np.ndarray] = []
        for w, b in zip(self.w, self.b, strict=True):
            weights.extend([w.copy(), b.copy()])
        return MLPController(sizes=list(self.sizes), weights=weights)


class _CriticNet:
    """MLP estimating scalar state value V(s)."""

    def __init__(self, sizes: list[int], rng: np.random.Generator, lr: float = 0.01):
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

    def forward(self, x: np.ndarray) -> tuple[list[np.ndarray], float]:
        acts = [x]
        h = x
        n = len(self.sizes) - 1
        for i in range(n):
            z = h @ self.w[i] + self.b[i]
            h = np.tanh(z) if i < n - 1 else z
            acts.append(h)
        val = float(acts[-1][0])
        return acts, val

    def backward(self, acts: list[np.ndarray], val: float, target: float) -> None:
        """Mean squared error value gradient: d(1/2 (V - target)^2)/dz = (V - target)."""
        n = len(self.sizes) - 1
        d = np.array([val - target], dtype=np.float64)

        grads_w: list[np.ndarray] = [None] * n  # type: ignore
        grads_b: list[np.ndarray] = [None] * n  # type: ignore
        for i in reversed(range(n)):
            a_prev = acts[i]
            grads_w[i] = np.outer(a_prev, d)
            grads_b[i] = d
            if i > 0:
                dh = self.w[i] @ d
                d = dh * (1.0 - acts[i] ** 2)

        self._adam(grads_w, grads_b)

    def _adam(
        self,
        grads_w: list[np.ndarray],
        grads_b: list[np.ndarray],
        beta1: float = 0.9,
        beta2: float = 0.999,
        eps: float = 1e-8,
    ) -> None:
        self._t += 1
        params = self.w + self.b
        grads = grads_w + grads_b
        for idx, (param, g) in enumerate(zip(params, grads, strict=False)):
            self._m[idx] = beta1 * self._m[idx] + (1.0 - beta1) * g
            self._v[idx] = beta2 * self._v[idx] + (1.0 - beta2) * (g * g)
            mhat = self._m[idx] / (1.0 - beta1**self._t)
            vhat = self._v[idx] / (1.0 - beta2**self._t)
            param -= self.lr * mhat / (np.sqrt(vhat) + eps)


def ppo(
    evaluator: Evaluator,
    base_env: Any,
    seed: int,
    hidden: tuple[int, ...] = (24,),
    actor_lr: float = 0.008,
    critic_lr: float = 0.012,
    gamma: float = 0.99,
    lam: float = 0.95,
    clip_eps: float = 0.2,
    epochs_per_update: int = 4,
    episodes_per_update: int = 4,
    entropy_coef: float = 0.015,
    max_updates: int = 5000,
    env_factory: Any | None = None,
) -> OptimizationResult:
    """Optimize a policy with Actor-Critic PPO under a strict interaction budget."""
    rng = np.random.default_rng(seed)

    factory = env_factory
    if factory is None:
        morph = Morphology(
            obs_mode=base_env.obs_mode,
            obs_radius=base_env.obs_radius,
            max_speed=base_env.max_speed,
            energy_capacity=base_env.energy_capacity,
        )
        _cfg = morph.apply(base_env)

        def _grid_factory() -> Any:
            return GridWorld(_cfg)

        factory = _grid_factory
    else:
        morph = Morphology()

    probe = factory()
    in_dim = int(probe.observation_size)
    n_actions = int(probe.n_actions)
    probe.close()

    actor = _ActorNet([in_dim, *hidden, n_actions], rng, lr=actor_lr)
    critic = _CriticNet([in_dim, *hidden, 1], rng, lr=critic_lr)

    history: list[dict[str, Any]] = []
    update = 0
    best_fit = float("-inf")
    best_controller: MLPController | None = None
    train_seeds = list(evaluator.train_seeds)

    max_steps_per_ep = getattr(base_env, "max_steps", None)
    if max_steps_per_ep is None:
        # Embodied envs use episode_seconds / control_dt
        max_steps_per_ep = int(getattr(base_env, "episode_seconds", 8.0) / getattr(base_env, "control_dt", 1.0 / 30.0))

    while update < max_updates and not evaluator.exhausted:
        eval_seeds = train_seeds[: min(2, len(train_seeds))]
        max_train_steps = episodes_per_update * int(max_steps_per_ep)
        max_update_steps = max_train_steps + len(eval_seeds) * int(max_steps_per_ep)
        if not evaluator.can_consume(max_update_steps):
            break

        # Rollout collection
        rollout_obs: list[np.ndarray] = []
        rollout_actions: list[int] = []
        rollout_old_probs: list[float] = []
        rollout_rewards: list[float] = []
        rollout_values: list[float] = []
        rollout_dones: list[bool] = []
        ep_rewards: list[float] = []

        for _ in range(episodes_per_update):
            s = int(rng.choice(train_seeds))
            env = factory()
            try:
                obs, _ = env.reset(seed=s)
                ep_r = 0.0
                done = False
                steps = 0
                while not done:
                    x = np.asarray(obs, dtype=np.float64)
                    _, p = actor.forward(x)
                    _, v = critic.forward(x)
                    a = int(rng.choice(len(p), p=p))

                    rollout_obs.append(x)
                    rollout_actions.append(a)
                    rollout_old_probs.append(float(p[a]))
                    rollout_values.append(v)

                    obs, r, term, trunc, _info = env.step(a)
                    rollout_rewards.append(float(r))
                    ep_r += float(r)
                    steps += 1
                    done = term or trunc
                    rollout_dones.append(done)

                evaluator.interactions += steps
                ep_rewards.append(ep_r)
            finally:
                env.close()

        # Compute Generalized Advantage Estimation (GAE)
        n_transitions = len(rollout_rewards)
        advantages = np.zeros(n_transitions, dtype=np.float64)
        targets = np.zeros(n_transitions, dtype=np.float64)

        gae = 0.0
        for t in reversed(range(n_transitions)):
            if t == n_transitions - 1 or rollout_dones[t]:
                next_val = 0.0
            else:
                next_val = rollout_values[t + 1]
            delta = rollout_rewards[t] + gamma * next_val - rollout_values[t]
            gae = delta + gamma * lam * (0.0 if rollout_dones[t] else gae)
            advantages[t] = gae
            targets[t] = gae + rollout_values[t]

        # Normalize advantages
        std_adv = float(advantages.std()) + 1e-8
        norm_advantages = (advantages - float(advantages.mean())) / std_adv

        # Multi-epoch PPO parameter updates
        for _epoch in range(epochs_per_update):
            indices = list(range(n_transitions))
            rng.shuffle(indices)
            for idx in indices:
                x = rollout_obs[idx]
                a = rollout_actions[idx]
                old_p = rollout_old_probs[idx]
                adv = float(norm_advantages[idx])
                target_val = float(targets[idx])

                # Update Actor
                acts_a, p_new = actor.forward(x)
                actor.backward(
                    acts_a,
                    p_new,
                    action=a,
                    old_prob=old_p,
                    advantage=adv,
                    clip_eps=clip_eps,
                    entropy_coef=entropy_coef,
                )

                # Update Critic
                acts_c, cur_v = critic.forward(x)
                critic.backward(acts_c, cur_v, target=target_val)

        # Periodic held-in evaluation
        ctrl = actor.to_controller(hidden)
        org = Organism(
            morph=morph,
            controller=ctrl,
            lineage=Lineage(id="", generation=update, mutations={"algo": "ppo"}),
            hidden=hidden,
        )
        org.refresh_id()
        fit, desc, _ = evaluator.evaluate_organism(org, seeds=eval_seeds)
        history.append({
            "update": update,
            "mean_episode_reward": float(np.mean(ep_rewards)) if ep_rewards else 0.0,
            "eval_fitness": fit,
            "interactions": evaluator.interactions,
        })
        if fit > best_fit:
            best_fit = fit
            best_controller = ctrl
        update += 1

    if best_controller is None:  # pragma: no cover
        best_controller = actor.to_controller(hidden)

    best_org = Organism(
        morph=morph,
        controller=best_controller,
        lineage=Lineage(id="", generation=update, mutations={"algo": "ppo", "best": True}),
        hidden=hidden,
    )
    best_org.refresh_id()

    return OptimizationResult(
        algorithm="ppo",
        version=VERSION,
        seed=seed,
        interactions=evaluator.interactions,
        budget=evaluator.budget,
        best_organism=best_org,
        best_fitness=best_fit,
        history=history,
        extra={
            "updates": update,
            "hidden": list(hidden),
            "actor_lr": actor_lr,
            "critic_lr": critic_lr,
            "gamma": gamma,
            "lam": lam,
            "clip_eps": clip_eps,
            "epochs_per_update": epochs_per_update,
            "entropy_coef": entropy_coef,
        },
    )
