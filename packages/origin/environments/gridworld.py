"""Deterministic 2D agent environment (Milestone 1).

The GridWorld is a fully deterministic, seed-controlled, Gymnasium-compatible
environment. Two runs with identical configuration and seed produce identical
terrain and, given identical action sequences, identical trajectories down to
floating point. This is the acceptance criterion for Milestone 1 and is
verified by ``tests/test_environment.py``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

try:  # gymnasium is a hard dependency; guard keeps tooling importable without it
    import gymnasium as gym
    from gymnasium import spaces
except Exception:  # pragma: no cover - only when gymnasium missing
    gym = None  # type: ignore
    spaces = None  # type: ignore

# Cell types
EMPTY = 0
OBSTACLE = 1
RESOURCE = 2
HAZARD = 3
# Keep cell ids disjoint from the viewer's transient agent overlay (4).
RESOURCE_B = 5

CELL_NAMES = {
    EMPTY: "empty",
    OBSTACLE: "obstacle",
    RESOURCE: "resource",
    HAZARD: "hazard",
    RESOURCE_B: "resource_b",
}

# Actions
ACTION_NAMES = {0: "up", 1: "down", 2: "left", 3: "right", 4: "stay"}
ACTION_DELTAS = {0: (-1, 0), 1: (1, 0), 2: (0, -1), 3: (0, 1), 4: (0, 0)}


@dataclass
class GridWorldConfig:
    """Configuration schema for the ORIGIN GridWorld environment.

    All fields are validated in :meth:`validate`. Invalid configurations raise
    ``ValueError`` with an actionable message.
    """

    height: int = 16
    width: int = 16
    max_steps: int = 200

    # World generation
    terrain: str = "random"  # one of: empty, random, rooms
    obstacle_density: float = 0.10
    n_resources: int = 6
    n_hazards: int = 6
    resource_regen: bool = True  # resources reappear at new cells when consumed

    # Multi-niche support (when n_resources_b > 0, introduces distinct Niche B resources)
    n_resources_b: int = 0
    resource_b_energy: float = 15.0
    resource_b_reward: float = 2.5
    niche_distribution: str = "uniform"  # uniform | zones

    # Agent
    energy_start: float = 100.0
    energy_step: float = 0.1
    energy_capacity: float = 100.0
    resource_energy: float = 5.0
    hazard_energy_drain: float = 25.0
    max_speed: int = 1  # cells per step (actuator effectiveness)
    noise: float = 0.0  # probability an action is replaced by a random action

    # Observation
    obs_mode: str = "vector"  # vector | local | full | nonspatial | multi_niche | multi_niche_local
    obs_radius: int = 2

    # Reward
    resource_reward: float = 1.0
    hazard_penalty: float = 1.0
    wall_penalty: float = 0.05
    step_penalty: float = 0.01
    death_penalty: float = 0.0
    move_diagonals: bool = False

    seed: int = 0

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.height < 2 or self.width < 2:
            raise ValueError("height and width must be >= 2")
        if self.max_steps < 1:
            raise ValueError("max_steps must be >= 1")
        if self.terrain not in ("empty", "random", "rooms"):
            raise ValueError(f"terrain must be one of empty|random|rooms, got {self.terrain!r}")
        if not 0.0 <= self.obstacle_density < 1.0:
            raise ValueError("obstacle_density must be in [0, 1)")
        if self.n_resources < 0 or self.n_hazards < 0 or self.n_resources_b < 0:
            raise ValueError("n_resources, n_resources_b and n_hazards must be >= 0")
        free = self.height * self.width
        if self.n_resources + self.n_resources_b + self.n_hazards >= free:
            raise ValueError("n_resources + n_resources_b + n_hazards must leave at least one free cell")
        if self.obs_mode not in ("vector", "local", "full", "nonspatial", "multi_niche", "multi_niche_local"):
            raise ValueError(f"obs_mode must be vector|local|full|nonspatial|multi_niche|multi_niche_local, got {self.obs_mode!r}")
        if self.niche_distribution not in ("uniform", "zones"):
            raise ValueError(f"niche_distribution must be uniform|zones, got {self.niche_distribution!r}")
        if self.obs_radius < 1:
            raise ValueError("obs_radius must be >= 1")
        if self.energy_capacity <= 0:
            raise ValueError("energy_capacity must be > 0")
        if not 0.0 <= self.noise <= 1.0:
            raise ValueError("noise must be in [0, 1]")
        if self.max_speed < 1:
            raise ValueError("max_speed must be >= 1")

    @property
    def n_actions(self) -> int:
        return 9 if self.move_diagonals else 5

    @property
    def action_space_n(self) -> int:
        """Alias of ``n_actions`` so any ORIGIN env presents one action-space name."""
        return self.n_actions

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GridWorldConfig:
        known = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
        unknown = set(d) - known
        if unknown:
            raise ValueError(f"unknown config fields: {sorted(unknown)}")
        return cls(**d)

    def config_hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()[:16]


class GridWorld(gym.Env if gym is not None else object):  # type: ignore[misc]
    """Deterministic, seed-controlled 2D grid environment."""

    metadata = {"render_modes": ["ansi", "rgb_array"], "render_fps": 8}

    def __init__(self, config: GridWorldConfig | None = None, render_mode: str | None = None):
        super().__init__()
        self.config = config or GridWorldConfig()
        self.render_mode = render_mode
        self._grid = np.zeros((self.config.height, self.config.width), dtype=np.int8)
        self._agent = np.array([0, 0], dtype=np.int64)
        self._energy = float(self.config.energy_start)
        self._steps = 0
        self._collected = 0
        self._collected_a = 0
        self._collected_b = 0
        self._hazard_hits = 0
        self._rng: np.random.Generator = np.random.default_rng(self.config.seed)
        self._episode_seed = self.config.seed
        if spaces is not None:
            self.action_space = spaces.Discrete(self.config.n_actions)
        else:  # pragma: no cover
            self.action_space = None

    # ------------------------------------------------------------------ #
    # Generation
    # ------------------------------------------------------------------ #
    def _make_rng(self, *parts: object) -> np.random.Generator:
        h = hashlib.sha256(
            ("|".join(str(p) for p in (self.config.seed, *parts))).encode()
        ).digest()
        seed = int.from_bytes(h[:8], "little", signed=False)
        return np.random.default_rng(seed)

    def _generate_terrain(self) -> None:
        cfg = self.config
        rng = self._make_rng("terrain")
        self._grid = np.full((cfg.height, cfg.width), EMPTY, dtype=np.int8)

        if cfg.terrain == "random":
            n_cells = cfg.height * cfg.width
            n_obstacles = int(round(cfg.obstacle_density * n_cells))
            idx = rng.choice(n_cells, size=min(n_obstacles, n_cells), replace=False)
            rows, cols = np.unravel_index(idx, (cfg.height, cfg.width))
            self._grid[rows, cols] = OBSTACLE
        elif cfg.terrain == "rooms":
            # Simple room partitions: alternating full rows/cols become walls
            for r in range(0, cfg.height, 4):
                self._grid[r, :] = OBSTACLE
            for c in range(0, cfg.width, 5):
                self._grid[:, c] = OBSTACLE

        # Carve free cells for agent + resources A/B + hazards
        free_mask = self._grid == EMPTY
        free_idx = np.flatnonzero(free_mask.ravel())
        total_needed = cfg.n_resources + cfg.n_resources_b + cfg.n_hazards + 1
        if free_idx.size < total_needed:
            raise ValueError("config leaves too few free cells after obstacle generation")

        rng.shuffle(free_idx)
        self._agent = np.array(np.unravel_index(free_idx[0], (cfg.height, cfg.width)), dtype=np.int64)

        if cfg.n_resources_b > 0 and cfg.niche_distribution == "zones":
            # Zone partition: Zone A in upper half, Zone B in lower half
            rem_idx = free_idx[1:]
            rem_rows, _ = np.unravel_index(rem_idx, (cfg.height, cfg.width))
            zone_a_mask = rem_rows < (cfg.height // 2)

            zone_a_idx = rem_idx[zone_a_mask]
            zone_b_idx = rem_idx[~zone_a_mask]

            res_a_cells = list(zone_a_idx[: cfg.n_resources])
            res_b_cells = list(zone_b_idx[: cfg.n_resources_b])
            used = set(res_a_cells).union(set(res_b_cells))
            unused = [i for i in rem_idx if i not in used]

            # If either zone is short of free cells, draw from remaining
            if len(res_a_cells) < cfg.n_resources:
                needed = cfg.n_resources - len(res_a_cells)
                extra = unused[:needed]
                unused = unused[needed:]
                res_a_cells.extend(extra)
            if len(res_b_cells) < cfg.n_resources_b:
                needed = cfg.n_resources_b - len(res_b_cells)
                extra = unused[:needed]
                unused = unused[needed:]
                res_b_cells.extend(extra)
            haz_cells = unused[: cfg.n_hazards]
        else:
            res_a_cells = list(free_idx[1 : 1 + cfg.n_resources])
            res_b_cells = list(free_idx[1 + cfg.n_resources : 1 + cfg.n_resources + cfg.n_resources_b])
            haz_cells = list(free_idx[1 + cfg.n_resources + cfg.n_resources_b : 1 + cfg.n_resources + cfg.n_resources_b + cfg.n_hazards])

        for i in res_a_cells:
            r, c = np.unravel_index(i, (cfg.height, cfg.width))
            self._grid[r, c] = RESOURCE
        for i in res_b_cells:
            r, c = np.unravel_index(i, (cfg.height, cfg.width))
            self._grid[r, c] = RESOURCE_B
        for i in haz_cells:
            r, c = np.unravel_index(i, (cfg.height, cfg.width))
            self._grid[r, c] = HAZARD

    # ------------------------------------------------------------------ #
    # Gymnasium API
    # ------------------------------------------------------------------ #
    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        if seed is not None:
            self.config.seed = int(seed)
        self._episode_seed = int(self.config.seed)
        self._rng = self._make_rng("episode")
        self._generate_terrain()
        self._energy = float(min(self.config.energy_start, self.config.energy_capacity))
        self._steps = 0
        self._collected = 0
        self._collected_a = 0
        self._collected_b = 0
        self._hazard_hits = 0
        return self._observation(), self._info()

    def step(self, action: int):
        cfg = self.config
        if not 0 <= int(action) < cfg.n_actions:
            raise ValueError(f"invalid action {action!r}; expected 0..{cfg.n_actions - 1}")
        action = int(action)

        # Actuator noise (deterministic given episode rng + call order)
        if cfg.noise > 0 and self._rng.random() < cfg.noise:
            action = int(self._rng.integers(0, cfg.n_actions))

        reward = -cfg.step_penalty
        dr, dc = self._delta(action)
        moved = False
        for _ in range(cfg.max_speed if (dr or dc) else 1):
            nr = int(np.clip(self._agent[0] + dr, 0, cfg.height - 1))
            nc = int(np.clip(self._agent[1] + dc, 0, cfg.width - 1))
            cell = int(self._grid[nr, nc])
            if cell == OBSTACLE:
                reward -= cfg.wall_penalty
                break
            if nr == self._agent[0] and nc == self._agent[1] and (dr or dc):
                reward -= cfg.wall_penalty  # bumped a boundary
                break
            self._agent = np.array([nr, nc], dtype=np.int64)
            moved = True
            cell = int(self._grid[nr, nc])
            if cell == RESOURCE:
                reward += cfg.resource_reward
                self._collected += 1
                self._collected_a += 1
                self._energy = min(cfg.energy_capacity, self._energy + cfg.resource_energy)
                self._consume_resource(nr, nc, RESOURCE)
            elif cell == RESOURCE_B:
                reward += cfg.resource_b_reward
                self._collected += 1
                self._collected_b += 1
                self._energy = min(cfg.energy_capacity, self._energy + cfg.resource_b_energy)
                self._consume_resource(nr, nc, RESOURCE_B)
            elif cell == HAZARD:
                reward -= cfg.hazard_penalty
                self._hazard_hits += 1
                self._energy -= cfg.hazard_energy_drain
            if not (dr and dc):
                break  # cardinal move = single step regardless of max_speed
            if not cfg.move_diagonals:
                break

        self._energy -= cfg.energy_step * (1 if moved else 1)
        self._steps += 1

        terminated = False
        if self._energy <= 0:
            terminated = True
            reward -= cfg.death_penalty
        if (cfg.n_resources + cfg.n_resources_b) > 0 and not cfg.resource_regen and self._resources_remaining() == 0:
            terminated = True
        truncated = self._steps >= cfg.max_steps
        return self._observation(), float(reward), bool(terminated), bool(truncated), self._info()

    def render(self):  # pragma: no cover - visual, exercised manually
        rows = []
        for r in range(self.config.height):
            row = []
            for c in range(self.config.width):
                if self._agent[0] == r and self._agent[1] == c:
                    row.append("@")
                else:
                    row.append({EMPTY: ".", OBSTACLE: "#", RESOURCE: "*", HAZARD: "x", RESOURCE_B: "$"}[int(self._grid[r, c])])
            rows.append("".join(row))
        out = "\n".join(rows)
        if self.render_mode == "ansi":
            return out
        print(out)
        return None

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _delta(self, action: int) -> tuple[int, int]:
        if self.config.move_diagonals:
            diag = {5: (-1, -1), 6: (-1, 1), 7: (1, -1), 8: (1, 1)}
            if action in diag:
                return diag[action]
        return ACTION_DELTAS[action]

    def _consume_resource(self, r: int, c: int, cell_type: int = RESOURCE) -> None:
        if self.config.resource_regen:
            free = np.argwhere(self._grid == EMPTY)
            if len(free):
                idx = int(self._rng.integers(0, len(free)))
                fr, fc = free[idx]
                self._grid[fr, fc] = cell_type
        self._grid[r, c] = EMPTY

    def _resources_remaining(self) -> int:
        return int(np.count_nonzero((self._grid == RESOURCE) | (self._grid == RESOURCE_B)))

    def _nearest_cells(self, cells: np.ndarray) -> tuple[float, float, float]:
        if len(cells) == 0:
            return 0.0, 0.0, 0.0
        d = cells - self._agent
        dist = np.sqrt((d**2).sum(axis=1))
        i = int(np.argmin(dist))
        dr, dc = d[i]
        return float(np.sign(dr)), float(np.sign(dc)), float(dist[i])

    def _nearest(self, cell_type: int) -> tuple[float, float, float]:
        cells = np.argwhere(self._grid == cell_type)
        return self._nearest_cells(cells)

    def _nearest_within(self, cell_type: int, radius: int) -> tuple[float, float, float]:
        """Nearest target only if within sensor radius (limited-range sensor)."""
        cells = np.argwhere(self._grid == cell_type)
        if len(cells) == 0:
            return 0.0, 0.0, 0.0
        d = cells - self._agent
        dist = np.sqrt((d**2).sum(axis=1))
        i = int(np.argmin(dist))
        if dist[i] > radius:
            return 0.0, 0.0, 0.0
        dr, dc = d[i]
        return float(np.sign(dr)), float(np.sign(dc)), float(dist[i])

    def _local_patch(self) -> np.ndarray:
        r = self.config.obs_radius
        padded = np.pad(self._grid, r, constant_values=OBSTACLE)
        ar, ac = self._agent
        patch = padded[ar : ar + 2 * r + 1, ac : ac + 2 * r + 1]
        return patch.astype(np.float32).ravel()

    def _observation(self) -> np.ndarray:
        """Canonical 7-D **egocentric** observation:
        [energy, res_dr, res_dc, res_dist, haz_dr, haz_dc, haz_dist].

        Absolute position is deliberately *excluded* so that a control policy
        cannot memorise a specific maze layout; it must react to relative
        bearings, which is what makes held-out generalisation measurable. The
        control interface is fixed across morphologies; ``obs_mode`` only changes
        sensor fidelity:
          * ``vector``             — full global bearings (best sensor)
          * ``local``              — bearings only within ``obs_radius`` (limited range)
          * ``nonspatial``         — no resource/hazard bearings at all (poor sensor)
          * ``multi_niche``        — egocentric bearings to both Niche A and Niche B
          * ``multi_niche_local``  — limited-range bearings to both Niche A and Niche B
        """
        cfg = self.config
        en = float(self._energy) / cfg.energy_capacity
        scale = float(max(cfg.height, cfg.width))
        if cfg.obs_mode == "multi_niche":
            res_a = self._nearest(RESOURCE)
            res_b = self._nearest(RESOURCE_B)
            return np.array([en, res_a[0], res_a[1], res_a[2] / scale, res_b[0], res_b[1], res_b[2] / scale], dtype=np.float32)
        elif cfg.obs_mode == "multi_niche_local":
            res_a = self._nearest_within(RESOURCE, cfg.obs_radius)
            res_b = self._nearest_within(RESOURCE_B, cfg.obs_radius)
            return np.array([en, res_a[0], res_a[1], res_a[2] / scale, res_b[0], res_b[1], res_b[2] / scale], dtype=np.float32)
        elif cfg.obs_mode == "vector":
            if cfg.n_resources_b > 0:
                cells = np.argwhere((self._grid == RESOURCE) | (self._grid == RESOURCE_B))
                res = self._nearest_cells(cells)
            else:
                res = self._nearest(RESOURCE)
            haz = self._nearest(HAZARD)
            return np.array([en, res[0], res[1], res[2] / scale, haz[0], haz[1], haz[2] / scale], dtype=np.float32)
        elif cfg.obs_mode == "local":
            res = self._nearest_within(RESOURCE, cfg.obs_radius)
            haz = self._nearest_within(HAZARD, cfg.obs_radius)
            return np.array([en, res[0], res[1], res[2] / scale, haz[0], haz[1], haz[2] / scale], dtype=np.float32)
        else:  # nonspatial
            return np.array([en, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)

    @property
    def observation_size(self) -> int:
        return 7

    @property
    def n_actions(self) -> int:
        return self.config.n_actions

    @property
    def action_space_n(self) -> int:
        return self.config.n_actions

    def close(self) -> None:
        """No-op: GridWorld holds no external resources.

        Present so every ORIGIN environment is uniformly closable — callers that
        release a simulated body (e.g. a PyBullet client) can treat them alike.
        """

    def _descriptor(self) -> np.ndarray:
        """Behavioural descriptor for novelty search / quality-diversity."""
        if self.config.n_resources_b > 0:
            hazard_rate = float(self._hazard_hits) / max(1, self._steps)
            return np.array(
                [
                    float(self._collected_a),
                    float(self._collected_b),
                    hazard_rate,
                    float(self._steps) / self.config.max_steps,
                    self._energy / self.config.energy_capacity,
                ],
                dtype=np.float32,
            )
        traversable = max(1, int(np.count_nonzero(self._grid != OBSTACLE)))
        resources_collected = float(self._collected)
        hazard_rate = float(self._hazard_hits) / max(1, self._steps)
        return np.array(
            [resources_collected, hazard_rate, float(self._steps) / self.config.max_steps, self._energy / self.config.energy_capacity, traversable / (self.config.height * self.config.width)],
            dtype=np.float32,
        )

    def _info(self) -> dict[str, Any]:
        return {
            "agent": self._agent.tolist(),
            "energy": float(self._energy),
            "steps": int(self._steps),
            "collected": int(self._collected),
            "collected_a": int(self._collected_a),
            "collected_b": int(self._collected_b),
            "hazard_hits": int(self._hazard_hits),
            "descriptor": self._descriptor().tolist(),
            "config_hash": self.config.config_hash(),
            "seed": int(self._episode_seed),
        }

    # ------------------------------------------------------------------ #
    # State serialization & replay
    # ------------------------------------------------------------------ #
    def get_state(self) -> dict[str, Any]:
        return {
            "version": 2,
            "config": self.config.to_dict(),
            "grid": self._grid.tolist(),
            "agent": self._agent.tolist(),
            "energy": float(self._energy),
            "steps": int(self._steps),
            "collected": int(self._collected),
            "collected_a": int(self._collected_a),
            "collected_b": int(self._collected_b),
            "hazard_hits": int(self._hazard_hits),
            "episode_seed": int(self._episode_seed),
            "rng_state": _rng_to_list(self._rng),
        }

    def set_state(self, state: dict[str, Any]) -> None:
        if state.get("version") != 2:
            raise ValueError("unsupported state version")
        self.config = GridWorldConfig.from_dict(state["config"])
        self._grid = np.array(state["grid"], dtype=np.int8)
        self._agent = np.array(state["agent"], dtype=np.int64)
        self._energy = float(state["energy"])
        self._steps = int(state["steps"])
        self._collected = int(state["collected"])
        self._collected_a = int(state.get("collected_a", self._collected))
        self._collected_b = int(state.get("collected_b", 0))
        self._hazard_hits = int(state["hazard_hits"])
        self._episode_seed = int(state["episode_seed"])
        self._rng = _rng_from_list(state["rng_state"])

    def clone(self) -> GridWorld:
        other = GridWorld(self.config, render_mode=self.render_mode)
        other.set_state(self.get_state())
        return other


def _rng_to_list(rng: np.random.Generator) -> list[Any]:
    return [rng.bit_generator.state["bit_generator"], json.dumps(rng.bit_generator.state, sort_keys=True)]


def _rng_from_list(blob: list[Any]) -> np.random.Generator:
    rng = np.random.default_rng(0)
    rng.bit_generator.state = json.loads(blob[1])
    return rng


class Replay:
    """Deterministic replay of a recorded action sequence from initial state."""

    def __init__(self, initial_state: dict[str, Any], actions: list[int], rewards: list[float]):
        self.initial_state = initial_state
        self.actions = list(actions)
        self.rewards = list(rewards)

    def re_run(self, tolerance: float = 1e-9) -> tuple[list[list[int]], bool]:
        env = GridWorld()
        env.set_state(json.loads(json.dumps(self.initial_state)))
        positions = [list(env.get_state()["agent"])]
        ok = True
        for a, expected in zip(self.actions, self.rewards, strict=False):
            _, r, terminated, truncated, _ = env.step(a)
            positions.append(list(env.get_state()["agent"]))
            if abs(r - expected) > tolerance:
                ok = False
            if terminated or truncated:
                break
        return positions, ok


def make(config: GridWorldConfig | dict[str, Any] | None = None, **kwargs: Any) -> GridWorld:
    if config is None:
        return GridWorld(GridWorldConfig(**kwargs))
    if isinstance(config, dict):
        cfg = GridWorldConfig.from_dict(config)
        for k, v in kwargs.items():
            setattr(cfg, k, v)
        return GridWorld(cfg)
    return GridWorld(config)


if gym is not None:  # pragma: no cover - registration side effect
    import contextlib

    with contextlib.suppress(Exception):
        gym.register(id="OriginGridWorld-v0", entry_point="origin.environments.gridworld:GridWorld")
