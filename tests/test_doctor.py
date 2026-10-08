"""Tests for origin-doctor diagnostic tooling."""

from __future__ import annotations

from origin.doctor import (
    check_core_dependencies,
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

    store = Store(tmp_path / "runs")
    rep = check_store(tmp_path / "runs")
    assert rep["exists"] is True
    assert rep["initialized"] is True
    assert rep["experiments"] == 0


def test_doctor_main_cli(tmp_path, capsys):
    ret = main(["--store", str(tmp_path / "runs")])
    assert ret == 0
    captured = capsys.readouterr()
    assert "ORIGIN SYSTEM DIAGNOSTICS" in captured.out
    assert "Core Dependencies" in captured.out

    # JSON mode
    ret_json = main(["--store", str(tmp_path / "runs"), "--json"])
    assert ret_json == 0
