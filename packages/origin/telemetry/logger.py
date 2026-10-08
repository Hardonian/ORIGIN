"""Telemetry: structured, append-only metric logging per trial."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MetricLogger:
    """Collects per-step/per-generation metrics and writes them as JSONL + records."""

    trial_id: str
    records: list[dict[str, Any]] = field(default_factory=list)

    def log(self, step: int, **values: Any) -> None:
        rec = {"trial_id": self.trial_id, "step": int(step), **values}
        self.records.append(rec)

    def extend(self, history: list[dict[str, Any]]) -> None:
        for h in history:
            self.records.append({"trial_id": self.trial_id, **h})

    def to_jsonl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as fh:
            for rec in self.records:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")

    def summary(self) -> dict[str, Any]:
        if not self.records:
            return {"n_records": 0}
        last = self.records[-1]
        return {"n_records": len(self.records), "last": last}
