"""Contract tests for the fail-closed embodied calibration harness."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_probe():
    path = Path(__file__).resolve().parents[1] / "scripts" / "probe_embodied_morphology.py"
    spec = importlib.util.spec_from_file_location("origin_embodied_probe", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_writes_explicit_evidence_when_pybullet_is_unavailable(tmp_path, monkeypatch, capsys):
    probe = _load_probe()
    monkeypatch.setattr(probe, "pybullet_engine", None)
    output = tmp_path / "calibration.json"

    assert probe.main(["--json-out", str(output)]) == 2

    report = json.loads(output.read_text())
    assert report["status"] == "unavailable"
    assert report["passed"] is False
    assert report["acceptance"]["minimum_forward_gain_m"] == 0.05
    assert "embodied" in report["acceptance"]["command"]
    assert "UNAVAILABLE" in capsys.readouterr().out
    assert not output.with_name(f".{output.name}.tmp").exists()
