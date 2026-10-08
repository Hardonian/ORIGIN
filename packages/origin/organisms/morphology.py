"""Organism morphology: the separable body/sensor/actuator description.

Morphology is deliberately decoupled from the controller genome so that
cross-morphology transfer can be studied by holding a controller fixed while
mutating the body.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from origin.environments.gridworld import GridWorldConfig

VALID_OBS_MODES = ("vector", "local", "nonspatial")


@dataclass
class Morphology:
    obs_mode: str = "vector"
    obs_radius: int = 2
    max_speed: int = 1
    energy_capacity: float = 100.0
    move_diagonals: bool = False

    def validate(self) -> None:
        if self.obs_mode not in VALID_OBS_MODES:
            raise ValueError(f"obs_mode must be one of {VALID_OBS_MODES}")
        if self.obs_radius < 1:
            raise ValueError("obs_radius must be >= 1")
        if self.max_speed < 1:
            raise ValueError("max_speed must be >= 1")
        if self.energy_capacity <= 0:
            raise ValueError("energy_capacity must be > 0")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Morphology:
        m = cls(**d)
        m.validate()
        return m

    def apply(self, base: GridWorldConfig) -> GridWorldConfig:
        """Produce an environment config reflecting this body."""
        cfg = GridWorldConfig.from_dict(base.to_dict())
        cfg.obs_mode = self.obs_mode
        cfg.obs_radius = self.obs_radius
        cfg.max_speed = self.max_speed
        cfg.energy_capacity = self.energy_capacity
        cfg.move_diagonals = self.move_diagonals
        return cfg

    def mutate(self, rng: np.random.Generator, strength: float = 1.0) -> Morphology:
        m = Morphology.from_dict(self.to_dict())
        if rng.random() < 0.25 * strength:
            m.obs_mode = VALID_OBS_MODES[int(rng.integers(0, len(VALID_OBS_MODES)))]
        if rng.random() < 0.4 * strength:
            m.obs_radius = int(np.clip(m.obs_radius + int(rng.integers(-1, 2)), 1, 5))
        if rng.random() < 0.4 * strength:
            m.max_speed = int(np.clip(m.max_speed + int(rng.integers(-1, 2)), 1, 3))
        if rng.random() < 0.4 * strength:
            m.energy_capacity = float(np.clip(m.energy_capacity * (1 + rng.normal(0, 0.15)), 25, 300))
        m.validate()
        return m

    def morphology_hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()[:12]
