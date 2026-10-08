"""Statistical helpers for ORIGIN's registered analyses.

Kept in the package (not the script) so they are unit-tested and reusable. The
bootstrap is seeded, so an analysis is reproducible from its inputs alone.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_RESAMPLES = 10_000
DEFAULT_SEED = 20261008


@dataclass
class DiffResult:
    point: float
    lo: float
    hi: float
    n_a: int
    n_b: int

    @property
    def excludes_zero(self) -> bool:
        return not (self.lo <= 0.0 <= self.hi)

    @property
    def verdict(self) -> str:
        """Registered decision rule: CI excluding 0 decides; otherwise inconclusive."""
        if self.excludes_zero and self.point > 0:
            return "supported (direction)"
        if self.excludes_zero and self.point < 0:
            return "falsified for this method"
        return "inconclusive"


def bootstrap_diff_ci(
    a: list[float] | np.ndarray,
    b: list[float] | np.ndarray,
    resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_SEED,
) -> DiffResult:
    """Percentile bootstrap CI for ``mean(a) - mean(b)``.

    Independent resampling of each group (unpaired), deterministic given ``seed``.
    """
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    if a_arr.size == 0 or b_arr.size == 0:
        raise ValueError("both samples must be non-empty")
    rng = np.random.default_rng(seed)
    point = float(a_arr.mean() - b_arr.mean())
    n_a, n_b = a_arr.size, b_arr.size
    diffs = np.empty(int(resamples), dtype=float)
    for i in range(int(resamples)):
        diffs[i] = a_arr[rng.integers(0, n_a, n_a)].mean() - b_arr[rng.integers(0, n_b, n_b)].mean()
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return DiffResult(point=point, lo=float(lo), hi=float(hi), n_a=n_a, n_b=n_b)


def mann_whitney(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> tuple[float, float]:
    """Two-sided Mann-Whitney U test; returns (U, p)."""
    from scipy.stats import mannwhitneyu

    res = mannwhitneyu(np.asarray(a, dtype=float), np.asarray(b, dtype=float), alternative="two-sided")
    return float(res.statistic), float(res.pvalue)
