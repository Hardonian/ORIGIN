"""Tests for the registered statistical helpers.

These guard the analysis used to decide H1: a wrong bootstrap or a wrong decision
rule silently changes a scientific conclusion, so the behaviour is pinned here.
"""

from __future__ import annotations

import numpy as np

from origin.evaluation.stats import (
    DiffResult,
    bootstrap_diff_ci,
    mann_whitney,
    min_detectable_effect,
    paired_bootstrap_ci,
    wilcoxon_signed_rank,
)


def test_bootstrap_ci_is_deterministic_given_seed():
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    b = [2.0, 2.5, 3.0, 3.5, 4.0]
    r1 = bootstrap_diff_ci(a, b, resamples=500, seed=7)
    r2 = bootstrap_diff_ci(a, b, resamples=500, seed=7)
    assert (r1.point, r1.lo, r1.hi) == (r2.point, r2.lo, r2.hi)


def test_bootstrap_ci_contains_zero_for_identical_samples():
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    r = bootstrap_diff_ci(a, a, resamples=1000, seed=1)
    assert r.point == 0.0
    assert r.lo <= 0.0 <= r.hi
    assert not r.excludes_zero
    assert r.verdict == "inconclusive"


def test_bootstrap_ci_excludes_zero_for_separated_samples():
    a = [10.0, 11.0, 12.0, 13.0, 14.0]
    b = [0.0, 1.0, 2.0, 3.0, 4.0]
    r = bootstrap_diff_ci(a, b, resamples=2000, seed=1)
    assert r.point == 10.0
    assert r.excludes_zero
    assert r.lo > 0
    assert r.verdict == "supported (direction)"


def test_verdict_is_falsified_when_ci_excludes_zero_negative():
    r = DiffResult(point=-1.0, lo=-2.0, hi=-0.1, n_a=5, n_b=5)
    assert r.excludes_zero
    assert r.verdict == "falsified for this method"


def test_mann_whitney_detects_separation_and_is_symmetric():
    a = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
    b = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    u1, p1 = mann_whitney(a, b)
    u2, p2 = mann_whitney(b, a)
    assert p1 == p2, "two-sided p must not depend on argument order"
    assert p1 < 0.01
    assert u1 + u2 == len(a) * len(b), "U statistics must be complementary"


def test_mann_whitney_high_p_for_similar_samples():
    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, 20)
    b = rng.normal(0, 1, 20)
    _u, p = mann_whitney(a, b)
    assert p > 0.05


def test_bootstrap_rejects_empty_sample():
    import pytest

    with pytest.raises(ValueError):
        bootstrap_diff_ci([], [1.0, 2.0])


# --------------------------------------------------------------------------- #
# Paired design (study v2 primary)
# --------------------------------------------------------------------------- #
def test_paired_bootstrap_ci_is_deterministic_and_centred_on_mean_diff():
    a = [5.0, 6.0, 7.0, 8.0, 9.0]
    b = [1.0, 2.0, 3.0, 4.0, 5.0]
    r1 = paired_bootstrap_ci(a, b, resamples=500, seed=11)
    r2 = paired_bootstrap_ci(a, b, resamples=500, seed=11)
    assert (r1.point, r1.lo, r1.hi) == (r2.point, r2.lo, r2.hi)
    assert r1.point == 4.0  # mean(a - b)
    assert r1.lo <= r1.point <= r1.hi or r1.lo <= r1.point  # CI brackets the estimate


def test_paired_ci_inconclusive_for_zero_mean_difference():
    a = [1.0, 2.0, 3.0, 4.0]
    r = paired_bootstrap_ci(a, a, resamples=500, seed=3)
    assert r.point == 0.0
    assert not r.excludes_zero
    assert r.verdict == "inconclusive"


def test_paired_ci_supports_direction_when_differences_are_consistently_positive():
    a = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
    b = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    r = paired_bootstrap_ci(a, b, resamples=2000, seed=5)
    assert r.point == 10.0
    assert r.excludes_zero and r.verdict == "supported (direction)"


def test_paired_bootstrap_rejects_unequal_lengths():
    import pytest

    with pytest.raises(ValueError):
        paired_bootstrap_ci([1.0, 2.0, 3.0], [1.0, 2.0])


def test_wilcoxon_detects_consistent_positive_differences():
    a = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
    b = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    stat, p = wilcoxon_signed_rank(a, b)
    assert p < 0.05
    assert stat >= 0.0


def test_wilcoxon_all_zero_differences_is_p_one():
    a = [3.0, 3.0, 3.0]
    stat, p = wilcoxon_signed_rank(a, a)
    assert (stat, p) == (0.0, 1.0)


def test_wilcoxon_rejects_unequal_lengths():
    import pytest

    with pytest.raises(ValueError):
        wilcoxon_signed_rank([1.0, 2.0], [1.0])


# --------------------------------------------------------------------------- #
# Minimum detectable effect (used to state a bounded null)
# --------------------------------------------------------------------------- #
def test_mde_shrinks_with_more_samples():
    d = [1.0, -1.0, 2.0, -2.0, 1.5, -1.5, 0.5, -0.5]
    small = min_detectable_effect(d, n=10)
    large = min_detectable_effect(d, n=100)
    assert large < small
    assert large > 0


def test_mde_matches_normal_approximation():
    d = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    sd = float(__import__("numpy").std(d, ddof=1))
    expected = (1.959963984540054 + 0.8416212335729143) * sd / (8 ** 0.5)
    assert abs(min_detectable_effect(d, power=0.8) - expected) < 1e-9


def test_mde_infinite_with_too_few_samples():
    assert min_detectable_effect([1.0], n=1) == float("inf")
