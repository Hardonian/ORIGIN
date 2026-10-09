"""Tests for origin-doctor diagnostic tooling."""

from __future__ import annotations

from origin.doctor import (
    check_core_dependencies,
    check_embodied_calibration,
    check_optional_extensions,
    check_store,
    main,
)


def test_doctor_core_dependencies():
    results = check_core_dependencies()
    assert len(results) >= 8
    # All core dependencies must be installed
    for name, ok, _ in results:
        assert ok is True, f"core dependency missing: {name}"


def test_doctor_optional_extensions():
    results = check_optional_extensions()
    assert len(results) >= 4
    names = [label for label, _, _ in results]
    assert any("pybullet" in n for n in names)
    assert any("PyTorch" in n for n in names)


def test_doctor_store_check(tmp_path):
    # Non-existent
    rep = check_store(tmp_path / "nonexistent")
    assert rep["exists"] is False

    # Initialized
    from origin.experiments.store import Store

    Store(tmp_path / "runs")
    rep = check_store(tmp_path / "runs")
    assert rep["exists"] is True
    assert rep["initialized"] is True
    assert rep["experiments"] == 0


def test_doctor_embodied_calibration_is_fail_closed(tmp_path):
    rep = check_embodied_calibration(tmp_path / "runs")
    assert rep["evidence"]["status"] == "not_run"
    assert rep["evidence"]["passed"] is False

    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "embodied-calibration.json").write_text(
        '{"status":"passed","passed":true,"acceptance":{"minimum_forward_gain_m":0.05,"best_forward_gain_m":0.06},"gaits":[{"program":"wave_a"}]}'
    )
    rep = check_embodied_calibration(runs)
    assert rep["evidence"]["passed"] is True
    assert "passed" in rep["next_action"].lower()


def test_doctor_main_cli(tmp_path, capsys):
    ret = main(["--store", str(tmp_path / "runs")])
    assert ret == 0
    captured = capsys.readouterr()
    assert "ORIGIN SYSTEM DIAGNOSTICS" in captured.out
    assert "Core Dependencies" in captured.out

    # JSON mode
    ret_json = main(["--store", str(tmp_path / "runs"), "--json"])
    assert ret_json == 0
