"""Distributed worker model (Milestone 7): many independent worker processes,
one shared store, exactly-once trial execution.

A worker derives its work from the experiment config (a trial is a pure
function of ``(algorithm, seed, config)`` with a deterministic trial id),
atomically claims each trial from the store, runs it, and records the result.

The guarantees, all enforced in :mod:`origin.experiments.store`:

* **Exclusive claims** — a ``running`` trial row has exactly one live owner;
  a second worker is told ``busy`` and moves on.
* **Heartbeats** — a worker heartbeats while it works, so liveness is a
  measured fact, not an assumption.
* **Stale-worker recovery** — a worker whose heartbeat went stale is marked
  dead and its trials return to the pool (``claim_trial`` takes them over, or
  :meth:`Store.reap_stale_workers` resets them explicitly). A killed worker
  therefore costs at most one wasted trial, never a stuck campaign.
* **Idempotent completion** — trial ids are deterministic and completion is
  keep-first: a duplicate computation can never overwrite a recorded result.
* **Idempotent merge** — stores merge by deterministic trial id
  (``origin-merge-stores``), so pulling results back from remote nodes is
  safe to repeat.

Usage::

    origin-worker --config configs/pilot.json --store runs --stale-after 120
    origin-worker --store runs --status          # who is working on what

Run several of these (locally or over SSH) against the same store directory
and the campaign distributes itself; each writes a per-worker record
(``<store>/<experiment>/worker-<id>.json``) naming exactly which trials it
claimed and completed.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import platform
import random
import socket
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from origin.experiments.runner import (
    _persist,
    environment_manifest,
    experiment_id,
    run_trial,
    trial_id_for,
    validate_config,
)
from origin.experiments.store import Store

DEFAULT_STALE_AFTER = 120.0
DEFAULT_HEARTBEAT = 5.0


def derive_work(cfg: dict[str, Any], include_baselines: bool = True) -> tuple[str, list[tuple[str, int, str]]]:
    """Deterministic work list: ``(exp_id, [(algorithm, seed, trial_id), ...])``.

    Every worker given the same config derives the same trial ids, which is
    what makes claims exclusive and merges idempotent.
    """
    validate_config(cfg)
    exp_id = experiment_id(cfg)
    work: list[tuple[str, int, str]] = []
    for algo in cfg.get("algorithms", {}):
        for seed in cfg["seeds"]:
            work.append((algo, int(seed), trial_id_for(exp_id, algo, int(seed))))
    if include_baselines:
        for algo in cfg.get("include_baselines", ["random", "heuristic"]):
            for seed in cfg["seeds"]:
                work.append((algo, int(seed), trial_id_for(exp_id, algo, int(seed))))
    return exp_id, work


class Worker:
    def __init__(
        self,
        cfg: dict[str, Any],
        store_root: str | Path = "runs",
        worker_id: str | None = None,
        stale_after: float = DEFAULT_STALE_AFTER,
        heartbeat_interval: float = DEFAULT_HEARTBEAT,
        cancel_file: str | Path | None = None,
        max_trials: int | None = None,
        include_baselines: bool = True,
    ) -> None:
        if stale_after <= heartbeat_interval:
            raise ValueError(
                f"stale_after ({stale_after}) must exceed heartbeat_interval ({heartbeat_interval}) "
                "or a live worker would reap itself"
            )
        self.cfg = cfg
        self.store = Store(store_root)
        self.worker_id = worker_id or f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self.stale_after = float(stale_after)
        self.heartbeat_interval = float(heartbeat_interval)
        self.cancel_file = str(cancel_file) if cancel_file else ""
        self.max_trials = max_trials
        self.include_baselines = include_baselines
        self._stop = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None

    # ---------------------------------------------------------- lifecycle #
    def _heartbeat_loop(self) -> None:
        while not self._stop.is_set():
            # A transient lock/sqlite contention error must not kill the
            # heartbeat thread — the next interval retries.
            with contextlib.suppress(Exception):  # pragma: no cover
                self.store.heartbeat(self.worker_id)
            self._stop.wait(self.heartbeat_interval)

    def _start_heartbeat(self) -> None:
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True, name=f"heartbeat-{self.worker_id}")
        self._heartbeat_thread.start()

    def _stop_heartbeat(self) -> None:
        self._stop.set()
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join(timeout=self.heartbeat_interval + 1.0)

    def cancelled(self) -> bool:
        return bool(self.cancel_file) and Path(self.cancel_file).exists()

    # --------------------------------------------------------------- work #
    def run(self) -> dict[str, Any]:
        cfg = self.cfg
        validate_config(cfg)
        exp_id = experiment_id(cfg)
        store = self.store
        manifest = environment_manifest()
        store.upsert_experiment(
            exp_id,
            cfg["name"],
            cfg.get("protocol", ""),
            hashlib.sha256(json.dumps(cfg["env"], sort_keys=True).encode()).hexdigest()[:12],
            cfg,
            manifest.get("git_sha"),
        )
        exp_dir = Path(store.root) / exp_id
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "manifest.json").write_text(
            json.dumps({"experiment_id": exp_id, "config": cfg, "environment": manifest}, indent=2, sort_keys=True)
        )

        store.register_worker(self.worker_id, platform.platform(), os.getpid())
        self._start_heartbeat()
        started = time.time()

        # Stale-worker recovery happens as part of normal work: every worker
        # reclaims orphaned trials before and during its claim loop.
        recovery = store.reap_stale_workers(self.stale_after)
        reaped_trials: list[str] = list(recovery["trials_reclaimed"])
        dead_workers: list[str] = list(recovery["dead_workers"])

        exp_id2, work = derive_work(cfg, include_baselines=self.include_baselines)
        assert exp_id2 == exp_id  # deterministic ids: same config -> same experiment
        # Stagger claim order per worker so parallel workers start on
        # different trials instead of colliding on the first one.
        random.Random(hashlib.sha256(self.worker_id.encode()).hexdigest()).shuffle(work)  # nosec B311 — claim-order jitter, not security-sensitive

        claimed: list[str] = []
        completed: list[str] = []
        duplicates_dropped: list[str] = []
        skipped: list[str] = []
        taken_over: list[str] = []
        failed: list[dict[str, str]] = []

        for algo, seed, tid in work:
            if self.cancelled():
                break
            if self.max_trials is not None and len(claimed) >= self.max_trials:
                break
            outcome = store.claim_trial(
                tid, exp_id, algo, seed, int(cfg["budget"]), self.worker_id, stale_after=self.stale_after
            )
            if outcome == "done":
                skipped.append(tid)
                continue
            if outcome == "busy":
                skipped.append(tid)
                continue
            if outcome == "taken_over":
                taken_over.append(tid)
                reaped_trials.append(tid)
            claimed.append(tid)
            results: list[dict[str, Any]] = []
            try:
                res = run_trial(algo, seed, cfg)
                _persist(store, exp_id, res, tid, exp_dir, results, worker_id=self.worker_id)
                if results and results[-1].get("status") == "duplicate_dropped":
                    duplicates_dropped.append(tid)
                else:
                    completed.append(tid)
            except Exception as exc:
                store.fail_trial(tid, f"{type(exc).__name__}: {exc}", worker_id=self.worker_id)
                failed.append({"trial_id": tid, "error": f"{type(exc).__name__}: {exc}"})

        self._stop_heartbeat()
        store.heartbeat(self.worker_id)
        store.finish_worker(self.worker_id)

        summary: dict[str, Any] = {
            "worker_id": self.worker_id,
            "experiment_id": exp_id,
            "claimed": claimed,
            "completed": completed,
            "duplicates_dropped": duplicates_dropped,
            "skipped": skipped,
            "taken_over": taken_over,
            "recovered_trials": reaped_trials,
            "dead_workers_seen": dead_workers,
            "failed": failed,
            "n_claimed": len(claimed),
            "n_completed": len(completed),
            "wall_seconds": round(time.time() - started, 2),
            "cancelled": self.cancelled(),
        }
        # Per-worker record: the auditable evidence of exactly which trials
        # this process executed (and which it refused to duplicate).
        (exp_dir / f"worker-{self.worker_id}.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
        return summary


def status_report(store_root: str | Path) -> dict[str, Any]:
    store = Store(store_root)
    now = time.time()
    workers = []
    for w in store.workers():
        entry = dict(w)
        entry["heartbeat_age_seconds"] = round(now - float(w["last_heartbeat"]), 1)
        workers.append(entry)
    return {"store": str(store_root), "trial_counts": store.trial_counts(), "workers": workers}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ORIGIN worker: claim and run trials from a shared store")
    ap.add_argument("--config", default=None, help="path to experiment JSON config")
    ap.add_argument("--store", default="runs", help="experiment store directory (shared between workers)")
    ap.add_argument("--worker-id", default=None, help="explicit worker id (default: host-pid-random)")
    ap.add_argument("--stale-after", type=float, default=DEFAULT_STALE_AFTER, help="seconds without heartbeat before a worker is considered dead")
    ap.add_argument("--heartbeat", type=float, default=DEFAULT_HEARTBEAT, help="heartbeat interval in seconds")
    ap.add_argument("--cancel-file", default=None, help="path to a file whose presence cancels the run")
    ap.add_argument("--max-trials", type=int, default=None, help="stop after claiming this many trials")
    ap.add_argument("--no-baselines", action="store_true")
    ap.add_argument("--status", action="store_true", help="print store/worker status and exit")
    args = ap.parse_args(argv)

    if args.status:
        print(json.dumps(status_report(args.store), indent=2, sort_keys=True))
        return 0
    if not args.config:
        ap.error("--config is required unless --status is given")

    cfg = json.loads(Path(args.config).read_text())
    worker = Worker(
        cfg,
        store_root=args.store,
        worker_id=args.worker_id,
        stale_after=args.stale_after,
        heartbeat_interval=args.heartbeat,
        cancel_file=args.cancel_file,
        max_trials=args.max_trials,
        include_baselines=not args.no_baselines,
    )
    summary = worker.run()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
