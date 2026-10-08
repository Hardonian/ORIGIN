"""Quality-diversity search: MAP-Elites (Milestone 3 baseline). Cully & Mouret style."""

from __future__ import annotations

from typing import Any

import numpy as np

from origin.environments.gridworld import GridWorldConfig
from origin.evaluation.harness import Evaluator
from origin.evolution.base import OptimizationResult
from origin.organisms.morphology import Morphology
from origin.organisms.organism import Organism

VERSION = "1.0"


class Archive:
    """A MAP-Elites archive: a grid over behavioural descriptors."""

    def __init__(self, shape: tuple[int, int], dims: tuple[int, int], bounds: list[tuple[float, float]]):
        self.shape = shape
        self.dims = dims
        self.bounds = bounds
        self.cells: dict[tuple[int, int], tuple[Organism, float, list[float]]] = {}
        self.attempts = 0

    def _bin(self, desc: np.ndarray) -> tuple[int, int]:
        coords = []
        for axis, dim in enumerate(self.dims):
            lo, hi = self.bounds[axis]
            frac = (float(desc[dim]) - lo) / (hi - lo + 1e-12)
            coords.append(int(np.clip(frac * self.shape[axis], 0, self.shape[axis] - 1)))
        return coords[0], coords[1]

    def add(self, org: Organism, fitness: float, desc: np.ndarray) -> bool:
        self.attempts += 1
        key = self._bin(desc)
        cur = self.cells.get(key)
        if cur is None or fitness > cur[1]:
            self.cells[key] = (org, float(fitness), desc.tolist())
            return True
        return False

    def random_elite(self, rng: np.random.Generator) -> Organism:
        keys = list(self.cells.keys())
        org, _, _ = self.cells[keys[int(rng.integers(0, len(keys)))]]
        return org

    def best(self) -> tuple[Organism, float] | None:
        if not self.cells:
            return None
        k = max(self.cells, key=lambda k: self.cells[k][1])
        org, fit, _ = self.cells[k]
        return org, fit

    def coverage(self) -> float:
        return len(self.cells) / (self.shape[0] * self.shape[1])

    def qd_score(self) -> float:
        return float(sum(c[1] for c in self.cells.values()))


def map_elites(
    evaluator: Evaluator,
    base_env: GridWorldConfig,
    seed: int,
    grid_shape: tuple[int, int] = (12, 12),
    hidden: tuple[int, ...] = (16,),
    batch: int = 12,
    mutation_rate: float = 0.2,
    mutation_scale: float = 0.3,
    morph_strength: float = 0.4,
    max_iterations: int = 1000,
) -> OptimizationResult:
    rng = np.random.default_rng(seed)
    desc_dims = (0, 2)  # (resources collected, episode-length fraction)
    bounds = [(0.0, max(4.0, float(base_env.n_resources))), (0.0, 1.0)]
    archive = Archive(grid_shape, desc_dims, bounds)
    history: list[dict[str, Any]] = []
    all_desc: list[list[float]] = []

    it = 0
    while it < max_iterations and not evaluator.exhausted:
        new_orgs: list[Organism] = []
        for _ in range(batch):
            if archive.cells and rng.random() < 0.8:
                parent = archive.random_elite(rng)
                new_orgs.append(parent.mutate(rng, base_env, weight_rate=mutation_rate, weight_scale=mutation_scale, morph_strength=morph_strength))
            else:
                new_orgs.append(Organism.random(Morphology(), base_env, rng, hidden=hidden))
        added = 0
        for org in new_orgs:
            fit, desc, _ = evaluator.evaluate_organism(org)
            all_desc.append(desc.tolist())
            if archive.add(org, fit, desc):
                added += 1
        history.append({
            "iteration": it,
            "coverage": archive.coverage(),
            "qd_score": archive.qd_score(),
            "archive_size": len(archive.cells),
            "added": added,
            "interactions": evaluator.interactions,
        })
        it += 1

    best = archive.best()
    best_org = best[0] if best else None
    best_fit = best[1] if best else float("-inf")
    return OptimizationResult(
        algorithm="map_elites",
        version=VERSION,
        seed=seed,
        interactions=evaluator.interactions,
        budget=evaluator.budget,
        best_organism=best_org,
        best_fitness=best_fit,
        history=history,
        descriptors=all_desc,
        archive={f"{k[0]},{k[1]}": {"fitness": v[1], "descriptor": v[2]} for k, v in archive.cells.items()},
        extra={
            "coverage": archive.coverage(),
            "archive_size": len(archive.cells),
            "grid_shape": list(grid_shape),
            "descriptor_dims": list(desc_dims),
            "iterations": it,
        },
    )
