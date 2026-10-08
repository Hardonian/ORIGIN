"""Baseline policies: random and scripted-heuristic (Milestone 3 controls).

These are intentionally *not* learned. They anchor the bottom of the
performance scale so that learned/evolved methods can be judged against them.
"""

from __future__ import annotations

import numpy as np

from origin.environments.gridworld import ACTION_DELTAS, HAZARD, OBSTACLE, RESOURCE, GridWorld


class RandomPolicy:
    name = "random"

    def __init__(self, n_actions: int, seed: int = 0):
        self.n_actions = n_actions
        self.rng = np.random.default_rng(seed)

    def act(self, obs: np.ndarray, env: GridWorld | None = None, deterministic: bool = True) -> int:
        return int(self.rng.integers(0, self.n_actions))

    def reset(self, seed: int) -> None:
        self.rng = np.random.default_rng(seed)


class HeuristicPolicy:
    """Greedy resource-seeker that avoids adjacent hazards.

    A deterministic scripted baseline using privileged environment state.
    """

    name = "heuristic"

    def __init__(self, n_actions: int, seed: int = 0):
        self.n_actions = n_actions
        self.rng = np.random.default_rng(seed)

    def reset(self, seed: int) -> None:
        self.rng = np.random.default_rng(seed)

    def act(self, obs: np.ndarray, env: GridWorld | None = None, deterministic: bool = True) -> int:
        if env is None:
            return int(self.rng.integers(0, self.n_actions))
        grid = env._grid  # privileged access is intentional for a scripted control
        agent = env._agent
        h, w = grid.shape

        def blocked(r: int, c: int) -> bool:
            if not (0 <= r < h and 0 <= c < w):
                return True
            return int(grid[r, c]) in (HAZARD, OBSTACLE)

        # BFS from the agent over hazard/obstacle-free cells to the nearest resource.
        from collections import deque

        start = (int(agent[0]), int(agent[1]))
        q: deque[tuple[int, int]] = deque([start])
        prev: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        goal: tuple[int, int] | None = None
        while q:
            cur = q.popleft()
            if int(grid[cur[0], cur[1]]) == RESOURCE:
                goal = cur
                break
            for dr, dc in ACTION_DELTAS.values():
                if dr == 0 and dc == 0:
                    continue
                nb = (cur[0] + dr, cur[1] + dc)
                if nb not in prev and not blocked(*nb):
                    prev[nb] = cur
                    q.append(nb)
        if goal is None or goal == start:
            # nothing reachable: take any safe move, else stay
            for a, (dr, dc) in ACTION_DELTAS.items():
                if (dr or dc) and not blocked(start[0] + dr, start[1] + dc):
                    return a
            return 4
        # walk back to the first step of the path
        node = goal
        while prev[node] is not None and prev[node] != start:
            node = prev[node]  # type: ignore[assignment]
        step = (node[0] - start[0], node[1] - start[1])
        inv = {v: k for k, v in ACTION_DELTAS.items()}
        return inv.get(step, 4)


class GaitPolicy:
    """Scripted open-loop gait baseline for the articulated-physics task.

    Cycles a fixed motor-primitive program and ignores its observation. This is the
    embodied analogue of the grid heuristic: a hand-designed control that anchors the
    bottom of the scale for a locomotion task, so a *learned* policy must beat a fixed
    gait rather than merely beat noise.

    Note it is deliberately non-adaptive: with no feedback it cannot recover from a
    fall or compensate for an unfamiliar body, which is exactly the limitation the
    evolved controllers are meant to overcome.
    """

    name = "scripted_gait"

    def __init__(self, n_actions: int, seed: int = 0, program: tuple[int, ...] = (2,)):
        self.n_actions = n_actions
        self.rng = np.random.default_rng(seed)
        self.program = tuple(a % max(1, n_actions) for a in program) or (0,)
        self.i = 0

    def reset(self, seed: int) -> None:
        self.rng = np.random.default_rng(seed)
        self.i = 0

    def act(self, obs: np.ndarray, env: GridWorld | None = None, deterministic: bool = True) -> int:
        a = self.program[self.i % len(self.program)]
        self.i += 1
        return int(a)
