"""Fixed-objective evolutionary optimization (Milestone 3 baseline)."""

from __future__ import annotations

from typing import Any

import numpy as np

from origin.environments.gridworld import GridWorldConfig
from origin.evaluation.harness import Evaluator
from origin.evolution.base import OptimizationResult
from origin.organisms.morphology import Morphology
from origin.organisms.organism import Organism

VERSION = "1.0"


def _init_population(base_env: GridWorldConfig, rng: np.random.Generator, pop_size: int, hidden: tuple[int, ...]) -> list[Organism]:
    # Seed the population with the three canonical morphologies so evolution
    # explores a body-diverse starting set rather than a single body plan.
    morphs = [
        Morphology(obs_mode="vector", obs_radius=2, max_speed=1),
        Morphology(obs_mode="local", obs_radius=2, max_speed=1),
        Morphology(obs_mode="vector", obs_radius=2, max_speed=2),
    ]
    pop: list[Organism] = []
    for i in range(pop_size):
        pop.append(Organism.random(morphs[i % len(morphs)], base_env, rng, hidden=hidden))
    return pop


def _tournament(pop: list[Organism], fitness: np.ndarray, rng: np.random.Generator, size: int) -> Organism:
    idx = rng.integers(0, len(pop), size=size)
    best = idx[int(np.argmax(fitness[idx]))]
    return pop[best]


def fixed_objective_ga(
    evaluator: Evaluator,
    base_env: GridWorldConfig,
    seed: int,
    pop_size: int = 24,
    hidden: tuple[int, ...] = (16,),
    elite: int = 2,
    tournament_size: int = 3,
    mutation_rate: float = 0.15,
    mutation_scale: float = 0.25,
    morph_strength: float = 0.4,
    max_generations: int = 500,
    init_pop: list[Organism] | None = None,
) -> OptimizationResult:
    rng = np.random.default_rng(seed)
    pop = list(init_pop) if init_pop else _init_population(base_env, rng, pop_size, hidden)
    if len(pop) < pop_size:
        pop.extend(_init_population(base_env, rng, pop_size - len(pop), hidden))
    history: list[dict[str, Any]] = []
    all_desc: list[list[float]] = []
    best_org: Organism | None = None
    best_fit = float("-inf")
    gen = 0

    while gen < max_generations and not evaluator.exhausted:
        fitness = np.zeros(len(pop))
        descs: list[np.ndarray] = []
        for i, org in enumerate(pop):
            fit, desc, _ = evaluator.evaluate_organism(org)
            fitness[i] = fit
            descs.append(desc)
            all_desc.append(desc.tolist())
        order = np.argsort(-fitness)
        if fitness[order[0]] > best_fit:
            best_fit = float(fitness[order[0]])
            best_org = pop[int(order[0])]
        history.append({
            "generation": gen,
            "best": float(fitness[order[0]]),
            "mean": float(fitness.mean()),
            "std": float(fitness.std()),
            "median": float(np.median(fitness)),
            "interactions": evaluator.interactions,
        })

        # elitism + tournament + mutation
        new_pop = [pop[int(i)] for i in order[:elite]]
        while len(new_pop) < pop_size:
            if rng.random() < 0.25 and len(pop) > 1:
                p1 = _tournament(pop, fitness, rng, tournament_size)
                p2 = _tournament(pop, fitness, rng, tournament_size)
                child = p1.crossover(p2, rng, base_env)
            else:
                parent = _tournament(pop, fitness, rng, tournament_size)
                child = parent.mutate(rng, base_env, weight_rate=mutation_rate, weight_scale=mutation_scale, morph_strength=morph_strength)
            new_pop.append(child)
        pop = new_pop
        gen += 1

    return OptimizationResult(
        algorithm="fixed_objective_ga",
        version=VERSION,
        seed=seed,
        interactions=evaluator.interactions,
        budget=evaluator.budget,
        best_organism=best_org,
        best_fitness=best_fit,
        history=history,
        descriptors=all_desc,
        extra={"generations": gen, "pop_size": pop_size},
    )
