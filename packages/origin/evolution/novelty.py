"""Novelty search (Milestone 3 baseline) — Lehman & Stanley (2011)."""

from __future__ import annotations

from typing import Any

import numpy as np

from origin.environments.gridworld import GridWorldConfig
from origin.evaluation.harness import Evaluator
from origin.evolution.base import OptimizationResult, novelty_of
from origin.evolution.ga import _init_population, _tournament
from origin.organisms.organism import Organism

VERSION = "1.0"


def novelty_search(
    evaluator: Evaluator,
    base_env: GridWorldConfig,
    seed: int,
    pop_size: int = 24,
    hidden: tuple[int, ...] = (16,),
    elite: int = 2,
    k: int = 10,
    novelty_threshold: float = float("inf"),
    mutation_rate: float = 0.15,
    mutation_scale: float = 0.3,
    max_generations: int = 500,
) -> OptimizationResult:
    """Optimize for behavioural novelty; task fitness is tracked but not selected on."""
    rng = np.random.default_rng(seed)
    pop = _init_population(base_env, rng, pop_size, hidden)
    novelty_archive: list[np.ndarray] = []
    history: list[dict[str, Any]] = []
    all_desc: list[list[float]] = []
    best_org: Organism | None = None
    best_task_fit = float("-inf")
    gen = 0

    while gen < max_generations and not evaluator.exhausted:
        if not evaluator.can_evaluate(count=len(pop)):
            break
        nov = np.zeros(len(pop))
        task = np.zeros(len(pop))
        raw_nov = np.zeros(len(pop))
        descs: list[np.ndarray] = []
        for i, org in enumerate(pop):
            fit, desc, _ = evaluator.evaluate_organism(org)
            task[i] = fit
            descs.append(desc)
            all_desc.append(desc.tolist())
            raw_nov[i] = novelty_of(desc, novelty_archive, k=k)
        # First generation has an empty archive -> novelty is +inf; fall back to task fitness
        nov = np.where(np.isfinite(raw_nov), raw_nov, task)
        best_idx = int(np.argmax(task))
        if task[best_idx] > best_task_fit:
            best_task_fit = float(task[best_idx])
            best_org = pop[best_idx]
        history.append({
            "generation": gen,
            "mean_novelty": float(raw_nov[np.isfinite(raw_nov)].mean()) if np.isfinite(raw_nov).any() else 0.0,
            "max_novelty": float(raw_nov[np.isfinite(raw_nov)].max()) if np.isfinite(raw_nov).any() else 0.0,
            "mean_task": float(task.mean()),
            "best_task": float(task.max()),
            "archive_size": len(novelty_archive),
            "interactions": evaluator.interactions,
        })
        # add sufficiently novel individuals to the archive (raw, un-substituted novelty)
        for desc, n in zip(descs, raw_nov, strict=False):
            if not np.isfinite(n) or n >= novelty_threshold:
                novelty_archive.append(desc)

        order = np.argsort(-nov)
        new_pop = [pop[int(i)] for i in order[:elite]]
        while len(new_pop) < pop_size:
            parent = _tournament(pop, nov, rng, 3)
            new_pop.append(parent.mutate(rng, base_env, weight_rate=mutation_rate, weight_scale=mutation_scale))
        pop = new_pop
        gen += 1

    return OptimizationResult(
        algorithm="novelty_search",
        version=VERSION,
        seed=seed,
        interactions=evaluator.interactions,
        budget=evaluator.budget,
        best_organism=best_org,
        best_fitness=best_task_fit,
        history=history,
        descriptors=all_desc,
        extra={"archive_size": len(novelty_archive), "generations": gen, "pop_size": pop_size},
    )
