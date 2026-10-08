"""Neural controller genomes with safe (JSON) serialization.

Genomes are plain lists of float arrays. Serialization never uses ``pickle``,
so untrusted checkpoint restore cannot execute code. This satisfies the
hardening requirement "no unsafe checkpoint deserialization".
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class MLPController:
    """A small feed-forward network mapping observations to action logits."""

    sizes: list[int]
    weights: list[np.ndarray] = field(default_factory=list)
    activation: str = "tanh"

    def __post_init__(self) -> None:
        if len(self.sizes) < 2:
            raise ValueError("sizes must have at least input and output dims")
        if not self.weights:
            self.weights = []

    @classmethod
    def random(cls, sizes: list[int], rng: np.random.Generator, scale: float = 1.0) -> MLPController:
        weights: list[np.ndarray] = []
        for i in range(len(sizes) - 1):
            fan_in = sizes[i]
            bound = scale * (1.0 / np.sqrt(max(1, fan_in)))
            w = rng.uniform(-bound, bound, size=(sizes[i], sizes[i + 1])).astype(np.float64)
            b = rng.uniform(-bound, bound, size=(sizes[i + 1],)).astype(np.float64)
            weights.extend([w, b])
        return cls(sizes=sizes, weights=weights)

    # ------------------------------------------------------------------ #
    def _act(self, x: np.ndarray) -> np.ndarray:
        return np.tanh(x) if self.activation == "tanh" else np.maximum(0.0, x)

    def forward(self, x: np.ndarray) -> np.ndarray:
        h = np.asarray(x, dtype=np.float64).reshape(-1)
        if h.shape[0] != self.sizes[0]:
            raise ValueError(f"expected input dim {self.sizes[0]}, got {h.shape[0]}")
        n_layers = len(self.sizes) - 1
        for i in range(n_layers):
            w, b = self.weights[2 * i], self.weights[2 * i + 1]
            h = w.T @ h + b
            if i < n_layers - 1:
                h = self._act(h)
        return h

    def act(self, x: np.ndarray, deterministic: bool = True, rng: np.random.Generator | None = None) -> int:
        logits = self.forward(x)
        if deterministic:
            return int(np.argmax(logits))
        # numerically-stable softmax sample
        z = logits - logits.max()
        p = np.exp(z) / np.exp(z).sum()
        rng = rng or np.random.default_rng()
        return int(rng.choice(len(p), p=p))

    # ------------------------------------------------------------------ #
    def mutate(self, rng: np.random.Generator, rate: float = 0.1, scale: float = 0.2) -> MLPController:
        new: list[np.ndarray] = []
        for arr in self.weights:
            mask = rng.random(arr.shape) < rate
            noise = rng.normal(0.0, scale, size=arr.shape)
            new.append((arr + mask * noise).astype(np.float64))
        return MLPController(sizes=list(self.sizes), weights=new, activation=self.activation)

    def crossover(self, other: MLPController, rng: np.random.Generator) -> MLPController:
        if other.sizes != self.sizes:
            raise ValueError("cannot crossover controllers with different shapes")
        child: list[np.ndarray] = []
        for a, b in zip(self.weights, other.weights, strict=False):
            mask = rng.random(a.shape) < 0.5
            child.append(np.where(mask, a, b).astype(np.float64))
        return MLPController(sizes=list(self.sizes), weights=child, activation=self.activation)

    def resize_input(self, new_in: int, rng: np.random.Generator) -> MLPController:
        """Return a controller whose first layer accepts ``new_in`` inputs.

        Required when morphology mutation changes the sensor dimension: the
        hidden/output layers are preserved and only the sensor projection is
        re-initialised (mirrors a developmental change in body plan).
        """
        if new_in == self.sizes[0]:
            return self
        new_sizes = [int(new_in), *self.sizes[1:]]
        weights = list(self.weights)
        bound = 1.0 / np.sqrt(max(1, new_in))
        weights[0] = rng.uniform(-bound, bound, size=(new_in, self.sizes[1])).astype(np.float64)
        weights[1] = rng.uniform(-bound, bound, size=(self.sizes[1],)).astype(np.float64)
        return MLPController(sizes=new_sizes, weights=weights, activation=self.activation)

    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict[str, Any]:
        return {
            "sizes": list(self.sizes),
            "activation": self.activation,
            "weights": [w.tolist() for w in self.weights],
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MLPController:
        if not {"sizes", "weights"} <= set(d):
            raise ValueError("genome dict missing required keys")
        if len(d["weights"]) != 2 * (len(d["sizes"]) - 1):
            raise ValueError("weights length is inconsistent with sizes")
        weights = [np.asarray(w, dtype=np.float64) for w in d["weights"]]
        c = cls(sizes=list(d["sizes"]), weights=weights, activation=d.get("activation", "tanh"))
        # shape validation
        for i in range(len(c.sizes) - 1):
            w, b = c.weights[2 * i], c.weights[2 * i + 1]
            if w.shape != (c.sizes[i], c.sizes[i + 1]) or b.shape != (c.sizes[i + 1],):
                raise ValueError("genome weight shapes are inconsistent with sizes")
        return c

    def genome_hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()
