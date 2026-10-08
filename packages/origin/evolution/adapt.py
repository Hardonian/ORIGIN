"""Adaptation helper: fine-tune an existing organism on a new target task.

Used by the morphology-transfer benchmark to measure *adaptation* (performance
after a fixed interaction budget on the new morphology) as distinct from
*zero-shot* transfer (performance with no further training).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from origin.evaluation.harness import Evaluator
from origin.evolution.base import OptimizationResult
from origin.evolution.ga import fixed_objective_ga
from origin.organisms.organism import Organism


def fine_tune(
    organism: Organism,
    target_env: Any,
    seed: int,
    budget: int,
    seeds: list[int],
    pop_size: int = 16,
    mutation_rate: float = 0.25,
    mutation_scale: float = 0.4,
    evaluator_factory: Any = None,
) -> OptimizationResult:
    """Fine-tune an organism on a target task.

    ``evaluator_factory`` lets a different simulator supply the evaluator (e.g. the
    articulated-physics bodies). The default builds the grid evaluator, preserving
    the original behaviour exactly.
    """
    rng = np.random.default_rng(seed)
    init = [organism]
    init.extend(organism.mutate(rng, target_env, weight_rate=mutation_rate, weight_scale=mutation_scale) for _ in range(pop_size - 1))
    ev = evaluator_factory() if evaluator_factory is not None else Evaluator(base_env=target_env, train_seeds=seeds, budget=budget)
    return fixed_objective_ga(
        ev,
        target_env,
        seed=seed,
        pop_size=pop_size,
        mutation_rate=mutation_rate,
        mutation_scale=mutation_scale,
        max_generations=10000,
        init_pop=init,
    )
