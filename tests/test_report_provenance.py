"""Guards that keep superseded experiment rows out of current-looking reports."""

import pytest
from scripts.make_report import legacy_protocol_reason, multi_niche_analysis_defaults


def test_invalidated_v2_protocol_requires_an_archival_override():
    reason = legacy_protocol_reason("multi_niche_transfer_v2_H1MN")

    assert reason is not None
    assert "invalidated" in reason
    assert "strict-cap v3" in reason


def test_current_strict_cap_protocol_is_reportable():
    assert legacy_protocol_reason("multi_niche_transfer_v3_strict_cap_H1MN") is None


def test_unknown_protocol_is_not_silently_classified_as_legacy():
    assert legacy_protocol_reason("future_pre_registered_protocol") is None


def test_current_multi_niche_defaults_point_to_its_registered_protocol():
    analysis_file, bootstrap_seed, protocol_doc = multi_niche_analysis_defaults(
        "multi_niche_transfer_v3_strict_cap_H1MN"
    )

    assert analysis_file == "H1_multi_niche_v3_analysis.md"
    assert bootstrap_seed == 20261015
    assert protocol_doc.endswith("multi_niche_replication_v3.md")


def test_unknown_multi_niche_protocol_cannot_inherit_pilot_metadata():
    with pytest.raises(ValueError, match="unknown multi-niche protocol"):
        multi_niche_analysis_defaults("future_pre_registered_protocol")
