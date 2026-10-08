"""Organisms: genome + morphology + lineage, acting in an environment.

Design constraints:
* No arbitrary externally submitted code is executed inside organisms. A
  controller is a data-only MLP genome; behaviour is produced solely by
  ``MLPController.forward``.
* Lineage is tracked for every offspring and is fully serializable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from origin.environments.gridworld import GridWorld, GridWorldConfig
from origin.organisms.genome import MLPController
from origin.organisms.morphology import Morphology


def _new_id(payload: str, length: int = 12) -> str:
    return hashlib.sha256(payload.encode()).hexdigest()[:length]


@dataclass
class Lineage:
    id: str
    parents: list[str] = field(default_factory=list)
    generation: int = 0
    mutations: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "parents": list(self.parents), "generation": self.generation, "mutations": dict(self.mutations)}


@dataclass
class Organism:
    morph: Morphology
    controller: MLPController
    lineage: Lineage
    hidden: tuple[int, ...] = (16,)

    # ------------------------------------------------------------------ #
    @classmethod
    def random(
        cls,
        morph: Morphology,
        base_env: GridWorldConfig,
        rng: np.random.Generator,
        hidden: tuple[int, ...] = (16,),
        scale: float = 1.0,
    ) -> Organism:
        in_dim = _input_dim(morph, base_env)
        sizes = [in_dim, *hidden, base_env.n_actions]
        controller = MLPController.random(sizes, rng, scale=scale)
        line = Lineage(id="", generation=0, mutations={"origin": "random"})
        org = cls(morph=morph, controller=controller, lineage=line, hidden=hidden)
        org.refresh_id()
        return org

    @property
    def id(self) -> str:
        return self.lineage.id

    def refresh_id(self) -> None:
        self.lineage.id = _new_id(self.controller.genome_hash() + self.morph.morphology_hash())

    # ------------------------------------------------------------------ #
    def act(self, obs: np.ndarray, env: Any = None, deterministic: bool = True, rng: np.random.Generator | None = None) -> int:
        return self.controller.act(obs, deterministic=deterministic, rng=rng)

    def env_config(self, base_env: GridWorldConfig) -> GridWorldConfig:
        return self.morph.apply(base_env)

    def make_env(self, base_env: GridWorldConfig, seed: int | None = None) -> GridWorld:
        cfg = self.env_config(base_env)
        if seed is not None:
            cfg.seed = seed
        return GridWorld(cfg)

    # ------------------------------------------------------------------ #
    def mutate(
        self,
        rng: np.random.Generator,
        base_env: GridWorldConfig | None = None,
        weight_rate: float = 0.1,
        weight_scale: float = 0.2,
        morph_strength: float = 0.5,
        mutate_morphology: bool = True,
    ) -> Organism:
        new_ctrl = self.controller.mutate(rng, rate=weight_rate, scale=weight_scale)
        new_morph = self.morph.mutate(rng, strength=morph_strength) if mutate_morphology else Morphology.from_dict(self.morph.to_dict())
        if base_env is not None:
            new_ctrl = new_ctrl.resize_input(_input_dim(new_morph, base_env), rng)
        line = Lineage(
            id="",
            parents=[self.lineage.id],
            generation=self.lineage.generation + 1,
            mutations={"weight_rate": weight_rate, "weight_scale": weight_scale, "morphology": mutate_morphology},
        )
        org = Organism(morph=new_morph, controller=new_ctrl, lineage=line, hidden=self.hidden)
        org.refresh_id()
        return org

    def crossover(self, other: Organism, rng: np.random.Generator, base_env: GridWorldConfig) -> Organism:
        morph = self.morph if rng.random() < 0.5 else Morphology.from_dict(other.morph.to_dict())
        target_in = _input_dim(morph, base_env)
        a = self.controller.resize_input(target_in, rng)
        b = other.controller.resize_input(target_in, rng)
        new_ctrl = a.crossover(b, rng)
        morph = morph.mutate(rng, strength=0.25)
        new_ctrl = new_ctrl.resize_input(_input_dim(morph, base_env), rng)
        line = Lineage(
            id="",
            parents=[self.lineage.id, other.lineage.id],
            generation=max(self.lineage.generation, other.lineage.generation) + 1,
            mutations={"kind": "crossover"},
        )
        org = Organism(morph=morph, controller=new_ctrl, lineage=line, hidden=self.hidden)
        org.refresh_id()
        return org

    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "morphology": self.morph.to_dict(),
            "controller": self.controller.to_dict(),
            "lineage": self.lineage.to_dict(),
            "hidden": list(self.hidden),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Organism:
        if d.get("version") != 1:
            raise ValueError("unsupported organism version")
        return cls(
            morph=Morphology.from_dict(d["morphology"]),
            controller=MLPController.from_dict(d["controller"]),
            lineage=Lineage(**d["lineage"]),
            hidden=tuple(d.get("hidden", [16])),
        )

    def content_hash(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()[:16]


def _input_dim(morph: Morphology, base_env: GridWorldConfig) -> int:
    """The control interface is fixed at 7 dimensions across all morphologies."""
    return 7
