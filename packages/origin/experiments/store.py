"""Persistent experiment store: SQLite metadata + Parquet/CSV metric exports.

Concurrency: writes are guarded by a ``filelock`` so multiple workers can
persist trials safely. Trial completion is recorded transactionally; a trial
is only marked ``done`` after its metrics are written, so a crashed worker
leaves a resumable ``running`` row rather than a silent gap.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import pandas as pd
from filelock import FileLock

SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    protocol TEXT,
    config_hash TEXT NOT NULL,
    config_json TEXT NOT NULL,
    git_sha TEXT,
    created_at REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'created'
);
CREATE TABLE IF NOT EXISTS trials (
    id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    algorithm TEXT NOT NULL,
    seed INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    interactions INTEGER DEFAULT 0,
    budget INTEGER DEFAULT 0,
    best_fitness REAL,
    train_fitness REAL,
    metrics_json TEXT,
    transfer_json TEXT,
    error TEXT,
    started_at REAL,
    finished_at REAL,
    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
);
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT NOT NULL,
    trial_id TEXT,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trials_exp ON trials(experiment_id);
CREATE INDEX IF NOT EXISTS idx_trials_algo ON trials(algorithm);
"""


class Store:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "origin.db"
        self.lock = FileLock(str(self.db_path) + ".lock")
        with self.lock:
            conn = self._conn()
            conn.executescript(SCHEMA)
            conn.commit()
            conn.close()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    # ------------------------------------------------------------------ #
    def upsert_experiment(self, exp_id: str, name: str, protocol: str, config_hash: str, config: dict[str, Any], git_sha: str | None) -> None:
        with self.lock:
            conn = self._conn()
            conn.execute(
                "INSERT OR IGNORE INTO experiments (id,name,protocol,config_hash,config_json,git_sha,created_at,status) VALUES (?,?,?,?,?,?,?,?)",
                (exp_id, name, protocol, config_hash, json.dumps(config), git_sha, time.time(), "running"),
            )
            conn.commit()
            conn.close()

    def add_trial(self, trial_id: str, exp_id: str, algorithm: str, seed: int, budget: int) -> None:
        with self.lock:
            conn = self._conn()
            conn.execute(
                "INSERT OR IGNORE INTO trials (id,experiment_id,algorithm,seed,status,budget,started_at) VALUES (?,?,?,?,?,?,?)",
                (trial_id, exp_id, algorithm, seed, "running", budget, time.time()),
            )
            conn.commit()
            conn.close()

    def complete_trial(self, trial_id: str, interactions: int, best_fitness: float, train_fitness: float, metrics: dict[str, Any], transfer: dict[str, Any] | None = None) -> None:
        with self.lock:
            conn = self._conn()
            conn.execute(
                "UPDATE trials SET status='done', interactions=?, best_fitness=?, train_fitness=?, metrics_json=?, transfer_json=?, finished_at=? WHERE id=?",
                (interactions, best_fitness, train_fitness, json.dumps(metrics), json.dumps(transfer) if transfer else None, time.time(), trial_id),
            )
            conn.commit()
            conn.close()

    def fail_trial(self, trial_id: str, error: str) -> None:
        with self.lock:
            conn = self._conn()
            conn.execute("UPDATE trials SET status='failed', error=?, finished_at=? WHERE id=?", (error, time.time(), trial_id))
            conn.commit()
            conn.close()

    def add_artifact(self, exp_id: str, trial_id: str | None, kind: str, path: str) -> None:
        with self.lock:
            conn = self._conn()
            conn.execute(
                "INSERT INTO artifacts (experiment_id,trial_id,kind,path,created_at) VALUES (?,?,?,?,?)",
                (exp_id, trial_id, kind, path, time.time()),
            )
            conn.commit()
            conn.close()

    # ------------------------------------------------------------------ #
    def trial_status(self, trial_id: str) -> str | None:
        conn = self._conn()
        row = conn.execute("SELECT status FROM trials WHERE id=?", (trial_id,)).fetchone()
        conn.close()
        return row["status"] if row else None

    def experiment(self, exp_id: str) -> dict[str, Any] | None:
        conn = self._conn()
        row = conn.execute("SELECT * FROM experiments WHERE id=?", (exp_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def list_experiments(self) -> list[dict[str, Any]]:
        conn = self._conn()
        rows = conn.execute("SELECT * FROM experiments ORDER BY created_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def trials(self, exp_id: str | None = None) -> list[dict[str, Any]]:
        conn = self._conn()
        if exp_id:
            rows = conn.execute("SELECT * FROM trials WHERE experiment_id=? ORDER BY algorithm,seed", (exp_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM trials ORDER BY finished_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def artifacts(self, exp_id: str | None = None) -> list[dict[str, Any]]:
        conn = self._conn()
        if exp_id:
            rows = conn.execute("SELECT * FROM artifacts WHERE experiment_id=? ORDER BY created_at", (exp_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM artifacts ORDER BY created_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    def export_trials(self, exp_id: str) -> dict[str, str]:
        rows = self.trials(exp_id)
        flat = []
        for r in rows:
            metrics = json.loads(r["metrics_json"]) if r.get("metrics_json") else {}
            flat.append({
                "trial_id": r["id"],
                "experiment_id": r["experiment_id"],
                "algorithm": r["algorithm"],
                "seed": r["seed"],
                "status": r["status"],
                "interactions": r["interactions"],
                "budget": r["budget"],
                "best_fitness": r["best_fitness"],
                "train_fitness": r["train_fitness"],
                "test_mean_reward": metrics.get("test_mean_reward"),
                "test_std_reward": metrics.get("test_std_reward"),
                "error": r["error"],
            })
        df = pd.DataFrame(flat)
        out = self.root / exp_id
        out.mkdir(parents=True, exist_ok=True)
        csv_path = out / "trials.csv"
        pq_path = out / "trials.parquet"
        df.to_csv(csv_path, index=False)
        try:
            df.to_parquet(pq_path, index=False)
        except Exception:
            pq_path = Path("")  # parquet engine may be unavailable
        return {"csv": str(csv_path), "parquet": str(pq_path) if pq_path else ""}

    def summary(self, exp_id: str) -> dict[str, Any]:
        rows = self.trials(exp_id)
        done = [r for r in rows if r["status"] == "done"]
        failed = [r for r in rows if r["status"] == "failed"]
        by_algo: dict[str, list[float]] = {}
        for r in done:
            metrics = json.loads(r["metrics_json"]) if r.get("metrics_json") else {}
            if metrics.get("test_mean_reward") is not None:
                by_algo.setdefault(r["algorithm"], []).append(metrics["test_mean_reward"])
        agg = {a: {"n": len(v), "mean": float(sum(v) / len(v))} for a, v in by_algo.items()}
        return {"n_trials": len(rows), "n_done": len(done), "n_failed": len(failed), "by_algorithm_test_reward": agg}
