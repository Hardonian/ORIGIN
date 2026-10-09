"""Validation contract for persisted articulated-crawler calibration evidence.

The probe writes a small JSON record beside an experiment store.  Both the API
and the local doctor consume it through this module so a dashboard cannot claim
that the crawler passed a calibration which command-line diagnostics reject.
"""


from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

CALIBRATION_EVIDENCE_FILE = "embodied-calibration.json"
MAX_EVIDENCE_BYTES = 1_000_000


def read_calibration_evidence(store_root: str | Path) -> dict[str, Any]:
    """Read crawler calibration evidence and fail closed on malformed claims.

    A passing record is only valid if it includes the recorded threshold, a
    measured gain meeting that threshold, and at least one measured gait.  A
    failed or unavailable report is also valid evidence of its own status.
    """
    path = Path(store_root).resolve() / CALIBRATION_EVIDENCE_FILE
    unavailable: dict[str, Any] = {
        "available": False,
        "valid": False,
        "status": "not_run",
        "passed": False,
        "file": CALIBRATION_EVIDENCE_FILE,
        "message": "No persisted PyBullet calibration evidence was found.",
        "command": "python scripts/probe_embodied_morphology.py --json-out runs/embodied-calibration.json",
    }
    if not path.exists():
        return unavailable
    try:
        oversized = path.stat().st_size > MAX_EVIDENCE_BYTES
    except OSError:
        return unavailable
    if oversized:
        return {
            **unavailable,
            "available": True,
            "status": "invalid",
            "message": f"Calibration evidence exceeds {MAX_EVIDENCE_BYTES // 1_000_000} MB.",
        }
    try:
        raw_value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            **unavailable,
            "available": True,
            "status": "invalid",
            "message": f"Unreadable calibration evidence: {exc}",
        }
    if not isinstance(raw_value, dict):
        return {
            **unavailable,
            "available": True,
            "status": "invalid",
            "message": "Calibration evidence must be a JSON object.",
        }
    raw: dict[str, Any] = raw_value

    status = raw.get("status")
    passed = raw.get("passed") is True
    acceptance_value = raw.get("acceptance")
    acceptance: dict[str, Any] = acceptance_value if isinstance(acceptance_value, dict) else {}
    minimum = acceptance.get("minimum_forward_gain_m")
    best = acceptance.get("best_forward_gain_m")
    gaits_value = raw.get("gaits")
    gaits: list[Any] = gaits_value if isinstance(gaits_value, list) else []
    def finite_number(value: Any) -> float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        converted = float(value)
        return converted if math.isfinite(converted) else None

    minimum_value = finite_number(minimum)
    best_value = finite_number(best)
    measured_gains = [
        gain
        for row in gaits
        if isinstance(row, dict)
        for gain in [finite_number(row.get("x_gain_m"))]
        if gain is not None
    ]
    config_hash = raw.get("config_hash")
    valid_pass = (
        status == "passed"
        and passed
        and isinstance(config_hash, str)
        and bool(config_hash)
        and minimum_value is not None
        and minimum_value > 0
        and best_value is not None
        and best_value >= minimum_value
        and bool(measured_gains)
        and max(measured_gains) >= minimum_value
    )
    valid_nonpass = status in {"failed", "unavailable"} and not passed
    valid = valid_pass or valid_nonpass
    if not valid:
        status = "invalid"

    return {
        "available": True,
        "valid": valid,
        "status": status,
        "passed": valid_pass,
        "file": CALIBRATION_EVIDENCE_FILE,
        "message": "Validated probe evidence." if valid else "Calibration evidence does not meet the evidence contract.",
        "config_hash": config_hash,
        "acceptance": {
            "minimum_forward_gain_m": minimum_value,
            "duration_seconds": acceptance.get("duration_seconds"),
            "best_forward_gain_m": best_value,
        },
        "gaits": gaits if valid else [],
        "runtime": raw.get("runtime") if isinstance(raw.get("runtime"), dict) else {},
    }
