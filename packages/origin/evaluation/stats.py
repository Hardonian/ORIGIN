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


def paired_bootstrap_ci(
    a: list[float] | np.ndarray,
    b: list[float] | np.ndarray,
    resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_SEED,
) -> DiffResult:
    """Percentile bootstrap CI for the mean *paired* difference ``mean(a - b)``.

    Unlike :func:`bootstrap_diff_ci`, resampling is over the paired differences
    themselves, which preserves the correlation induced by common random numbers
    (all methods share identical training environments) and is the pre-registered
    primary analysis of study v2. Samples must be aligned and equal length.
    """
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    if a_arr.size != b_arr.size:
        raise ValueError("paired samples must have equal length (align by seed)")
    if a_arr.size == 0:
        raise ValueError("samples must be non-empty")
    d = a_arr - b_arr
    rng = np.random.default_rng(seed)
    n = d.size
    means = np.empty(int(resamples), dtype=float)
    for i in range(int(resamples)):
        means[i] = d[rng.integers(0, n, n)].mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    return DiffResult(point=float(d.mean()), lo=float(lo), hi=float(hi), n_a=n, n_b=n)


def wilcoxon_signed_rank(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> tuple[float, float]:
    """Two-sided Wilcoxon signed-rank test on paired samples; returns (statistic, p).

    All-zero differences carry no information and are dropped by scipy; that case
    is reported as p = 1.0 rather than raising.
    """
    from scipy.stats import wilcoxon

    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    if a_arr.size != b_arr.size:
        raise ValueError("paired samples must have equal length")
    d = a_arr - b_arr
    if np.allclose(d, 0.0):
        return 0.0, 1.0
    res = wilcoxon(a_arr, b_arr, alternative="two-sided")
    return float(res.statistic), float(res.pvalue)


def min_detectable_effect(
    diffs: list[float] | np.ndarray,
    n: int | None = None,
    power: float = 0.8,
    alpha: float = 0.05,
) -> float:
    """Minimum paired effect detectable at the given power (normal approximation).

    ``MDE = (z_{1-alpha/2} + z_{power}) * sd / sqrt(n)``, with ``sd`` the sample
    standard deviation of the observed differences. Used to state a *bounded* null:
    an inconclusive test at this n rules out effects larger than the MDE, which is
    a stronger and more honest claim than "not proven".
    """
    d = np.asarray(diffs, dtype=float)
    k = int(n) if n is not None else d.size
    if k < 2:
        return float("inf")
    from scipy.stats import norm

    z = float(norm.ppf(1 - alpha / 2) + norm.ppf(power))
    sd = float(d.std(ddof=1))
    return z * sd / np.sqrt(k)
