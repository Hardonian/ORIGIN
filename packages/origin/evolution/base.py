"""Base types shared by all ORIGIN optimizers (Milestone 3).

Every algorithm family returns an :class:`OptimizationResult` and consumes a
shared :class:`Evaluator`, guaranteeing that (a) interaction budgets are
comparable and (b) metrics are produced identically regardless of algorithm.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from origin.organisms.organism import Organism


@dataclass
class OptimizationResult:
    algorithm: str
    version: str
    seed: int
    interactions: int
    budget: int
    best_organism: Organism | None
    best_fitness: float
    history: list[dict[str, Any]] = field(default_factory=list)
    descriptors: list[list[float]] = field(default_factory=list)
    archive: dict[str, Any] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "version": self.version,
            "seed": self.seed,
            "interactions": self.interactions,
            "budget": self.budget,
            "best_fitness": self.best_fitness,
            "history": self.history,
            "n_descriptors": len(self.descriptors),
            "archive_size": (len(self.archive) if isinstance(self.archive, dict) else 0),
            "extra": self.extra,
            "best_genome_hash": (self.best_organism.controller.genome_hash() if self.best_organism else None),
        }


def descriptor_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)))


def novelty_of(desc: np.ndarray, archive: list[np.ndarray], k: int = 10) -> float:
    if not archive:
        return float("inf")
    ds = sorted(descriptor_distance(desc, other) for other in archive)
    kk = min(k, len(ds))
    return float(np.mean(ds[:kk]))
