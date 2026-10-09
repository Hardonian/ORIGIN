"""Completeness guards for the REINFORCE promotion analysis."""

import pytest
from scripts.analyze_reinforce import require_complete_paired_data


def _cfg() -> dict:
    return {"seeds": [200, 201]}


def test_reinforce_analysis_accepts_complete_finite_pairs():
    require_complete_paired_data(
        {"reinforce": {200: 2.0, 201: 3.0}, "random": {200: 1.0, 201: 1.0}}, _cfg()
    )


def test_reinforce_analysis_rejects_a_missing_registered_seed():
    with pytest.raises(ValueError, match=r"reinforce: missing seeds \[201\]"):
        require_complete_paired_data(
            {"reinforce": {200: 2.0}, "random": {200: 1.0, 201: 1.0}}, _cfg()
        )


def test_reinforce_analysis_rejects_nonfinite_scores():
    with pytest.raises(ValueError, match="non-finite held-out values"):
        require_complete_paired_data(
            {"reinforce": {200: float("nan"), 201: 3.0}, "random": {200: 1.0, 201: 1.0}}, _cfg()
        )
