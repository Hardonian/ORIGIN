"""Persistent experiment store: SQLite metadata + Parquet/CSV metric exports.

Concurrency: writes are guarded by a ``filelock`` so multiple workers can
persist trials safely. Trial completion is recorded transactionally; a trial
is only marked ``done`` after its metrics are written, so a crashed worker
leaves a resumable ``running`` row rather than a silent gap.

Worker model (Milestone 7): independent worker processes share one store.
A trial is claimed atomically (only one live worker may own a ``running``
row), workers heartbeat while they work, and a reaper returns the trials of
dead workers to the pool. Trial ids are deterministic
(``sha256(experiment|algorithm|seed)``), so merging stores (e.g. pulling a
remote node's results back) is idempotent by construction, and completion is
keep-first: a ``done`` row is never overwritten.
"""

from __future__ import annotations

import json
import sqlite3
import sys
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
    worker_id TEXT,
    claimed_at REAL,
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
CREATE TABLE IF NOT EXISTS workers (
    id TEXT PRIMARY KEY,
    host TEXT,
    pid INTEGER,
    status TEXT NOT NULL DEFAULT 'running',
    started_at REAL NOT NULL,
    last_heartbeat REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trials_exp ON trials(experiment_id);
CREATE INDEX IF NOT EXISTS idx_trials_algo ON trials(algorithm);
"""

# Columns added to the trials table after the worker model landed. Older
# stores are migrated in place (ALTER TABLE ADD COLUMN), so existing campaign
# data keeps working without a manual conversion step.
_TRIAL_COLUMNS = {
    "worker_id": "TEXT",
    "claimed_at": "REAL",
}

_EXPERIMENT_STATUSES = {"running", "completed", "failed", "cancelled"}


class Store:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "origin.db"
        self.lock = FileLock(str(self.db_path) + ".lock")
        with self.lock:
            conn = self._conn()
            conn.executescript(SCHEMA)
            self._migrate(conn)
            conn.commit()
            conn.close()

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """Add columns introduced after a store was created (idempotent)."""
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(trials)")}
        for col, coltype in _TRIAL_COLUMNS.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE trials ADD COLUMN {col} {coltype}")

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

    def set_experiment_status(self, exp_id: str, status: str) -> None:
        """Record a terminal (or resumed) campaign state without touching trials."""
        if status not in _EXPERIMENT_STATUSES:
            raise ValueError(f"unknown experiment status {status!r}")
        with self.lock:
            conn = self._conn()
            cur = conn.execute("UPDATE experiments SET status=? WHERE id=?", (status, exp_id))
            conn.commit()
            conn.close()
        if cur.rowcount != 1:
            raise KeyError(f"unknown experiment {exp_id}")

    def reconcile_experiment_statuses(self, dry_run: bool = False) -> list[dict[str, str]]:
        """Finalize legacy ``running`` experiments whose trials are terminal.

        Earlier runner versions completed every trial but never finalized the
        parent experiment record.  Infer only states that are mechanically
        unambiguous: the terminal trial count must exactly equal the matrix
        declared in the stored configuration; all-done trials are
        ``completed`` and any terminal matrix containing a failed trial is
        ``failed``. Experiments with no rows, incomplete/invalid matrices,
        pending/running rows, or an explicitly non-running state are
        deliberately left untouched.
        """
        changes: list[dict[str, str]] = []
        with self.lock:
            conn = self._conn()
            experiments = conn.execute(
                "SELECT id, status, config_json FROM experiments WHERE status='running' ORDER BY id"
            ).fetchall()
            for experiment in experiments:
                exp_id = str(experiment["id"])
                try:
                    config = json.loads(experiment["config_json"])
                    algorithms = config["algorithms"]
                    baselines = config["include_baselines"]
                    seeds = config["seeds"]
                    expected_count = (len(algorithms) + len(baselines)) * len(seeds)
                except (KeyError, TypeError, json.JSONDecodeError):
                    continue
                if (
                    not isinstance(algorithms, dict)
                    or not isinstance(baselines, list)
                    or not isinstance(seeds, list)
                    or expected_count <= 0
                ):
                    continue
                counts = {
                    str(row["status"]): int(row["n"])
                    for row in conn.execute(
                        "SELECT status, COUNT(*) AS n FROM trials WHERE experiment_id=? GROUP BY status",
                        (exp_id,),
                    ).fetchall()
                }
                terminal_count = counts.get("done", 0) + counts.get("failed", 0)
                if terminal_count != expected_count or counts.get("running", 0) or counts.get("pending", 0):
                    continue
                status = "failed" if counts.get("failed", 0) else "completed"
                changes.append({"experiment_id": exp_id, "from": "running", "to": status})
                if not dry_run:
                    conn.execute("UPDATE experiments SET status=? WHERE id=?", (status, exp_id))
            if not dry_run:
                conn.commit()
            conn.close()
        return changes

    def add_trial(self, trial_id: str, exp_id: str, algorithm: str, seed: int, budget: int) -> None:
        with self.lock:
            conn = self._conn()
            conn.execute(
                "INSERT OR IGNORE INTO trials (id,experiment_id,algorithm,seed,status,budget,started_at) VALUES (?,?,?,?,?,?,?)",
                (trial_id, exp_id, algorithm, seed, "running", budget, time.time()),
            )
            conn.commit()
            conn.close()

    def complete_trial(self, trial_id: str, interactions: int, best_fitness: float, train_fitness: float, metrics: dict[str, Any], transfer: dict[str, Any] | None = None, worker_id: str | None = None) -> bool:
        """Record a finished trial. Returns False (and changes nothing) if the
        trial is already ``done`` — completion is keep-first, so a duplicate
        computation (e.g. a stolen claim finishing late) can never overwrite a
        recorded result."""
        with self.lock:
            conn = self._conn()
            cur = conn.execute(
                "UPDATE trials SET status='done', interactions=?, best_fitness=?, train_fitness=?, metrics_json=?, transfer_json=?, finished_at=?, worker_id=COALESCE(?, worker_id) WHERE id=? AND status<>'done'",
                (interactions, best_fitness, train_fitness, json.dumps(metrics), json.dumps(transfer) if transfer else None, time.time(), worker_id, trial_id),
            )
            conn.commit()
            conn.close()
            return cur.rowcount == 1

    def fail_trial(self, trial_id: str, error: str, worker_id: str | None = None) -> bool:
        """Record a trial failure. Never downgrades a ``done`` trial."""
        with self.lock:
            conn = self._conn()
            cur = conn.execute(
                "UPDATE trials SET status='failed', error=?, finished_at=?, worker_id=COALESCE(?, worker_id) WHERE id=? AND status<>'done'",
                (error, time.time(), worker_id, trial_id),
            )
            conn.commit()
            conn.close()
            return cur.rowcount == 1

    def add_artifact(self, exp_id: str, trial_id: str | None, kind: str, path: str) -> None:
        with self.lock:
            conn = self._conn()
            conn.execute(
                "INSERT INTO artifacts (experiment_id,trial_id,kind,path,created_at) VALUES (?,?,?,?,?)",
                (exp_id, trial_id, kind, path, time.time()),
            )
            conn.commit()
            conn.close()

    # ------------------------------------------------------------- workers #
    def register_worker(self, worker_id: str, host: str, pid: int) -> None:
        now = time.time()
        with self.lock:
            conn = self._conn()
            conn.execute(
                "INSERT OR REPLACE INTO workers (id,host,pid,status,started_at,last_heartbeat) VALUES (?,?,?,?,?,?)",
                (worker_id, host, pid, "running", now, now),
            )
            conn.commit()
            conn.close()

    def heartbeat(self, worker_id: str) -> None:
        with self.lock:
            conn = self._conn()
            conn.execute("UPDATE workers SET last_heartbeat=? WHERE id=?", (time.time(), worker_id))
            conn.commit()
            conn.close()

    def finish_worker(self, worker_id: str, status: str = "finished") -> None:
        with self.lock:
            conn = self._conn()
            conn.execute("UPDATE workers SET status=?, last_heartbeat=? WHERE id=?", (status, time.time(), worker_id))
            conn.commit()
            conn.close()

    def workers(self) -> list[dict[str, Any]]:
        conn = self._conn()
        rows = conn.execute("SELECT * FROM workers ORDER BY started_at").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def claim_trial(
        self,
        trial_id: str,
        exp_id: str,
        algorithm: str,
        seed: int,
        budget: int,
        worker_id: str,
        stale_after: float = 120.0,
    ) -> str:
        """Atomically claim a trial for ``worker_id``.

        Returns one of:
        * ``claimed``      — this worker now owns the trial (fresh claim);
        * ``taken_over``   — this worker now owns the trial (previous owner's
          heartbeat is stale; the claim was recovered);
        * ``done``         — already completed; nothing to do;
        * ``busy``         — a live (registered, heartbeating) worker owns it.

        A claim is exclusive against workers with live heartbeats. An owner
        with no live heartbeat record is recoverable immediately: trials are
        pure functions of ``(algorithm, seed, config)`` and completion is
        keep-first, so recovery-first can waste duplicate compute at worst —
        it can never corrupt results or strand a trial on a dead owner.
        """
        now = time.time()
        with self.lock:
            conn = self._conn()
            row = conn.execute("SELECT status, worker_id FROM trials WHERE id=?", (trial_id,)).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO trials (id,experiment_id,algorithm,seed,status,budget,started_at,worker_id,claimed_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (trial_id, exp_id, algorithm, seed, "running", budget, now, worker_id, now),
                )
                conn.commit()
                conn.close()
                return "claimed"
            status = row["status"]
            if status == "done":
                conn.close()
                return "done"
            if status == "running":
                owner = row["worker_id"]
                if owner and owner != worker_id and self._worker_alive(conn, owner, stale_after, now):
                    conn.close()
                    return "busy"
                conn.execute(
                    "UPDATE trials SET status='running', worker_id=?, claimed_at=?, started_at=COALESCE(started_at, ?) WHERE id=?",
                    (worker_id, now, now, trial_id),
                )
                conn.commit()
                conn.close()
                return "taken_over" if owner and owner != worker_id else "claimed"
            # pending or failed: claimable again (resume semantics).
            conn.execute(
                "UPDATE trials SET status='running', worker_id=?, claimed_at=?, started_at=COALESCE(started_at, ?) WHERE id=?",
                (worker_id, now, now, trial_id),
            )
            conn.commit()
            conn.close()
            return "claimed"

    def _worker_alive(self, conn: sqlite3.Connection, worker_id: str, stale_after: float, now: float) -> bool:
        row = conn.execute("SELECT status, last_heartbeat FROM workers WHERE id=?", (worker_id,)).fetchone()
        if row is None or row["status"] != "running":
            return False
        return (now - float(row["last_heartbeat"])) <= stale_after

    def reap_stale_workers(self, stale_after: float = 120.0, now: float | None = None) -> dict[str, Any]:
        """Mark workers with stale heartbeats dead and return their trials to
        the pool (``running`` -> ``pending``) so another worker can claim them.

        This is the stale-worker recovery path: a killed/crashed worker leaves
        ``running`` rows behind, and this call makes them claimable again.
        """
        now = time.time() if now is None else now
        dead: list[str] = []
        reclaimed: list[str] = []
        with self.lock:
            conn = self._conn()
            for row in conn.execute("SELECT id, status, last_heartbeat FROM workers").fetchall():
                if row["status"] == "running" and (now - float(row["last_heartbeat"])) > stale_after:
                    conn.execute("UPDATE workers SET status='dead' WHERE id=?", (row["id"],))
                    dead.append(row["id"])
            for row in conn.execute("SELECT id, worker_id FROM trials WHERE status='running'").fetchall():
                owner = row["worker_id"]
                if owner is None or owner in dead or not self._worker_alive(conn, owner, stale_after, now):
                    conn.execute("UPDATE trials SET status='pending', worker_id=NULL, claimed_at=NULL WHERE id=?", (row["id"],))
                    reclaimed.append(row["id"])
            conn.commit()
            conn.close()
        return {"dead_workers": dead, "trials_reclaimed": reclaimed}

    def trial_counts(self, exp_id: str | None = None) -> dict[str, int]:
        conn = self._conn()
        if exp_id:
            rows = conn.execute("SELECT status, COUNT(*) AS n FROM trials WHERE experiment_id=? GROUP BY status", (exp_id,)).fetchall()
        else:
            rows = conn.execute("SELECT status, COUNT(*) AS n FROM trials GROUP BY status").fetchall()
        conn.close()
        return {r["status"]: int(r["n"]) for r in rows}

    # --------------------------------------------------------------- merge #
    def merge_from(self, other: Store) -> dict[str, Any]:
        """Merge another store's results in, keyed by deterministic trial id.

        Idempotent: merging twice changes nothing the second time. Completion
        is keep-first — a local ``done`` row is never overwritten, and when both
        sides are ``done`` with different values the row is counted as a
        conflict (reported, not silently resolved). Artifacts present only on
        the source side are copied when their files exist.
        """
        merged: dict[str, Any] = {"experiments": 0, "trials": 0, "trials_skipped_done": 0, "conflicts": [], "artifacts": 0}
        if other is self:
            return merged
        # Deterministic lock order (by db path) so two concurrent merges in
        # opposite directions cannot deadlock.
        first, second = sorted([self, other], key=lambda s: str(s.db_path))
        with first.lock, second.lock:
            conn = self._conn()
            oconn = other._conn()
            for exp in oconn.execute("SELECT * FROM experiments").fetchall():
                cur = conn.execute("INSERT OR IGNORE INTO experiments (id,name,protocol,config_hash,config_json,git_sha,created_at,status) VALUES (?,?,?,?,?,?,?,?)",
                                   (exp["id"], exp["name"], exp["protocol"], exp["config_hash"], exp["config_json"], exp["git_sha"], exp["created_at"], exp["status"]))
                merged["experiments"] += cur.rowcount
            for t in oconn.execute("SELECT * FROM trials").fetchall():
                local = conn.execute("SELECT status, best_fitness, metrics_json FROM trials WHERE id=?", (t["id"],)).fetchone()
                if local is None:
                    conn.execute(
                        "INSERT INTO trials (id,experiment_id,algorithm,seed,status,interactions,budget,best_fitness,train_fitness,metrics_json,transfer_json,error,started_at,finished_at,worker_id,claimed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (t["id"], t["experiment_id"], t["algorithm"], t["seed"], t["status"], t["interactions"], t["budget"], t["best_fitness"], t["train_fitness"], t["metrics_json"], t["transfer_json"], t["error"], t["started_at"], t["finished_at"], t["worker_id"], t["claimed_at"]),
                    )
                    merged["trials"] += 1
                elif local["status"] != "done" and t["status"] == "done":
                    conn.execute(
                        "UPDATE trials SET status='done', interactions=?, best_fitness=?, train_fitness=?, metrics_json=?, transfer_json=?, error=NULL, finished_at=?, worker_id=?, claimed_at=? WHERE id=?",
                        (t["interactions"], t["best_fitness"], t["train_fitness"], t["metrics_json"], t["transfer_json"], t["finished_at"], t["worker_id"], t["claimed_at"], t["id"]),
                    )
                    merged["trials"] += 1
                elif local["status"] == "done" and t["status"] == "done":
                    merged["trials_skipped_done"] += 1
                    if local["best_fitness"] != t["best_fitness"] or local["metrics_json"] != t["metrics_json"]:
                        merged["conflicts"].append(t["id"])
            for a in oconn.execute("SELECT * FROM artifacts").fetchall():
                # One artifact row per (experiment, trial, kind) — matching on
                # the path (which a merge rewrites to the local copy) would make
                # a second merge re-insert the same artifact.
                exists = conn.execute(
                    "SELECT 1 FROM artifacts WHERE experiment_id=? AND (trial_id IS ? OR trial_id = ?) AND kind=?",
                    (a["experiment_id"], a["trial_id"], a["trial_id"], a["kind"]),
                ).fetchone()
                if exists is None:
                    src = Path(a["path"])
                    out_path = a["path"]
                    if src.exists() and src.is_relative_to(other.root):
                        # Copy the artifact file into this store and record the
                        # local path — never leave a row pointing at a staging
                        # directory that will be deleted after the merge.
                        dest = self.root / src.relative_to(other.root)
                        if not dest.exists():
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            dest.write_bytes(src.read_bytes())
                        out_path = str(dest)
                    conn.execute("INSERT INTO artifacts (experiment_id,trial_id,kind,path,created_at) VALUES (?,?,?,?,?)",
                                 (a["experiment_id"], a["trial_id"], a["kind"], out_path, a["created_at"]))
                    merged["artifacts"] += 1
            conn.commit()
            conn.close()
            oconn.close()
        return merged

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


def merge_main(argv: list[str] | None = None) -> int:
    """CLI: merge one store directory into another, idempotently.

    Usage::

        origin-merge-stores --from runs-remote --into runs
    """
    import argparse

    ap = argparse.ArgumentParser(description="Merge ORIGIN stores by deterministic trial id")
    ap.add_argument("--from", dest="src", required=True, help="source store directory (e.g. a remote node's runs/)")
    ap.add_argument("--into", dest="dst", required=True, help="destination store directory")
    args = ap.parse_args(argv)

    result = Store(args.dst).merge_from(Store(args.src))
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["conflicts"]:
        print(f"WARNING: {len(result['conflicts'])} trial(s) done on both sides with differing values", file=sys.stderr)
        return 1
    return 0


def reconcile_main(argv: list[str] | None = None) -> int:
    """CLI: repair terminal experiment statuses left by older runner versions."""
    import argparse

    ap = argparse.ArgumentParser(description="Reconcile legacy ORIGIN experiment lifecycle statuses")
    ap.add_argument("--store", default="runs", help="experiment store directory")
    ap.add_argument("--dry-run", action="store_true", help="report inferred updates without writing them")
    args = ap.parse_args(argv)

    changes = Store(args.store).reconcile_experiment_statuses(dry_run=args.dry_run)
    print(json.dumps({"dry_run": args.dry_run, "changes": changes}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(merge_main())
