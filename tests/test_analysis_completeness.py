"""Completeness checks for registered paired analyses."""

import pytest
from scripts.analyze import require_complete_paired_data


def _cfg() -> dict:
    return {
        "seeds": [10, 11],
        "algorithms": {"fixed_objective_ga": {}, "map_elites": {}},
    }


def test_paired_analysis_accepts_exact_complete_finite_data():
    by_seed = {
        "fixed_objective_ga": {10: 1.0, 11: 2.0},
        "map_elites": {10: 2.0, 11: 3.0},
    }

    require_complete_paired_data(by_seed, _cfg())


def test_paired_analysis_rejects_a_missing_registered_seed():
    by_seed = {
        "fixed_objective_ga": {10: 1.0, 11: 2.0},
        "map_elites": {10: 2.0},
    }

    with pytest.raises(ValueError, match=r"map_elites: missing seeds \[11\]"):
        require_complete_paired_data(by_seed, _cfg())


def test_paired_analysis_rejects_nonfinite_held_out_value():
    by_seed = {
        "fixed_objective_ga": {10: 1.0, 11: 2.0},
        "map_elites": {10: float("nan"), 11: 3.0},
    }

    with pytest.raises(ValueError, match="non-finite held-out values"):
        require_complete_paired_data(by_seed, _cfg())
