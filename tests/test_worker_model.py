"""Milestone 7 tests: worker claims, heartbeats, stale-worker recovery and
idempotent store merges — including a real multi-process campaign.

The in-process tests exercise each store invariant fail-closed; the
subprocess tests prove the model works across *real* independent worker
processes sharing one store (exactly-once execution, disjoint claims).
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from origin.experiments.runner import experiment_id, trial_id_for
from origin.experiments.store import Store
from origin.experiments.worker import Worker, derive_work, status_report

# Small and fast: 2 trials x 2 seeds, tiny budget. Used by the multi-process
# tests, which must stay cheap enough to run in the normal gate.
TINY_WORKER = {
    "name": "tiny-worker",
    "protocol": "test",
    "env": {"height": 6, "width": 6, "max_steps": 20, "n_resources": 2, "n_hazards": 0,
            "obstacle_density": 0.05, "resource_regen": False, "step_penalty": 0.001,
            "wall_penalty": 0.0, "seed": 0},
    "train_seeds": [1, 2],
    "test_seeds": [7, 8],
    "budget": 300,
    "seeds": [1, 2],
    "include_baselines": ["random"],
    "transfer": {"adapt": False},
    "algorithms": {"fixed_objective_ga": {"pop_size": 4, "max_generations": 3}},
}


def _trial_row(store: Store, tid: str) -> dict:
    conn = store._conn()
    row = conn.execute("SELECT * FROM trials WHERE id=?", (tid,)).fetchone()
    conn.close()
    assert row is not None
    return dict(row)


# ------------------------------------------------------------------ claims #
def test_claim_is_exclusive_against_live_workers(tmp_path):
    store = Store(tmp_path / "runs")
    store.register_worker("w1", "host", 1)
    store.register_worker("w2", "host", 2)
    tid, exp = "t1", "e1"
    assert store.claim_trial(tid, exp, "algo", 1, 100, "w1") == "claimed"
    assert store.claim_trial(tid, exp, "algo", 1, 100, "w2") == "busy"
    row = _trial_row(store, tid)
    assert row["status"] == "running"
    assert row["worker_id"] == "w1"


def test_claim_recovers_unregistered_owner_immediately(tmp_path):
    """Contract: only registered heartbeating workers hold protected claims.
    An owner with no heartbeat record is recoverable at once — safe because
    trials are pure and completion is keep-first (worst case: duplicate
    compute dropped, never a stuck campaign)."""
    store = Store(tmp_path / "runs")
    assert store.claim_trial("t1", "e1", "algo", 1, 100, "w-unregistered") == "claimed"
    assert store.claim_trial("t1", "e1", "algo", 1, 100, "w2") == "taken_over"
    assert _trial_row(store, "t1")["worker_id"] == "w2"


def test_claim_skips_done(tmp_path):
    store = Store(tmp_path / "runs")
    store.claim_trial("t1", "e1", "algo", 1, 100, "w1")
    assert store.complete_trial("t1", 5, 1.0, 1.0, {"x": 1}, worker_id="w1")
    assert store.claim_trial("t1", "e1", "algo", 1, 100, "w2") == "done"


def test_claim_takes_over_stale_owner(tmp_path):
    store = Store(tmp_path / "runs")
    store.register_worker("w1", "host", 1)
    store.claim_trial("t1", "e1", "algo", 1, 100, "w1")
    conn = store._conn()
    conn.execute("UPDATE workers SET last_heartbeat=? WHERE id='w1'", (time.time() - 600,))
    conn.commit()
    conn.close()
    # w1's heartbeat is old -> its claim is recoverable.
    assert store.claim_trial("t1", "e1", "algo", 1, 100, "w2", stale_after=30.0) == "taken_over"
    row = _trial_row(store, "t1")
    assert row["worker_id"] == "w2"


def test_claim_retries_failed(tmp_path):
    store = Store(tmp_path / "runs")
    store.claim_trial("t1", "e1", "algo", 1, 100, "w1")
    assert store.fail_trial("t1", "boom", worker_id="w1")
    assert store.claim_trial("t1", "e1", "algo", 1, 100, "w2") == "claimed"


# ------------------------------------------------- completion idempotency #
def test_complete_is_keep_first(tmp_path):
    store = Store(tmp_path / "runs")
    store.claim_trial("t1", "e1", "algo", 1, 100, "w1")
    assert store.complete_trial("t1", 5, 1.0, 1.0, {"x": 1}, worker_id="w1") is True
    # A duplicate computation (stolen claim finishing late) must NOT overwrite
    # the recorded result.
    assert store.complete_trial("t1", 9, 9.9, 9.9, {"x": 9}, worker_id="w2") is False
    row = _trial_row(store, "t1")
    assert row["best_fitness"] == 1.0
    assert json.loads(row["metrics_json"]) == {"x": 1}


def test_fail_never_clobbers_done(tmp_path):
    store = Store(tmp_path / "runs")
    store.claim_trial("t1", "e1", "algo", 1, 100, "w1")
    store.complete_trial("t1", 5, 1.0, 1.0, {"x": 1}, worker_id="w1")
    assert store.fail_trial("t1", "late error", worker_id="w2") is False
    assert _trial_row(store, "t1")["status"] == "done"


# ------------------------------------------------------ heartbeat / reaper #
def test_worker_lifecycle_and_heartbeat(tmp_path):
    store = Store(tmp_path / "runs")
    store.register_worker("w1", "host", 123)
    before = store.workers()[0]["last_heartbeat"]
    time.sleep(0.01)
    store.heartbeat("w1")
    after = store.workers()[0]["last_heartbeat"]
    assert after > before
    store.finish_worker("w1")
    assert store.workers()[0]["status"] == "finished"


def test_reaper_recovers_dead_workers_trials_only(tmp_path):
    store = Store(tmp_path / "runs")
    store.register_worker("w-dead", "host", 1)
    store.register_worker("w-live", "host", 2)
    store.claim_trial("t-dead", "e1", "algo", 1, 100, "w-dead")
    store.claim_trial("t-live", "e1", "algo", 2, 100, "w-live")
    store.heartbeat("w-live")
    conn = store._conn()
    conn.execute("UPDATE workers SET last_heartbeat=? WHERE id='w-dead'", (time.time() - 600,))
    conn.commit()
    conn.close()

    out = store.reap_stale_workers(stale_after=30.0)
    assert out["dead_workers"] == ["w-dead"]
    assert out["trials_reclaimed"] == ["t-dead"]
    assert _trial_row(store, "t-dead")["status"] == "pending"
    assert _trial_row(store, "t-live")["status"] == "running"
    # After the reap, the orphaned trial is claimable again.
    assert store.claim_trial("t-dead", "e1", "algo", 1, 100, "w3", stale_after=30.0) == "claimed"


def test_worker_rejects_unsafe_heartbeat_config(tmp_path):
    with pytest.raises(ValueError, match="stale_after"):
        Worker(TINY_WORKER, store_root=tmp_path / "runs", stale_after=1.0, heartbeat_interval=5.0)


# ------------------------------------------------------------ store merge #
def _fill_store(root: Path, n: int = 2) -> Store:
    store = Store(root)
    for i in range(n):
        tid = f"t{i}"
        store.claim_trial(tid, "e1", "algo", i, 100, "w")
        store.complete_trial(tid, 5, float(i), float(i), {"i": i}, worker_id="w")
    return store


def test_merge_is_idempotent_and_keep_first(tmp_path):
    src = _fill_store(tmp_path / "src")
    dst = Store(tmp_path / "dst")
    first = dst.merge_from(src)
    assert first["trials"] == 2
    second = dst.merge_from(src)
    assert second["trials"] == 0
    assert second["trials_skipped_done"] == 2
    assert second["conflicts"] == []
    assert len(dst.trials("e1")) == 2

    # A conflicting done row on the source never overwrites the local record;
    # it is reported as a conflict instead of silently resolved.
    src2 = Store(tmp_path / "src2")
    src2.claim_trial("t0", "e1", "algo", 0, 100, "w")
    src2.complete_trial("t0", 5, 999.0, 999.0, {"i": 999}, worker_id="w")
    third = dst.merge_from(src2)
    assert third["conflicts"] == ["t0"]
    assert _trial_row(dst, "t0")["best_fitness"] == 0.0


def test_merge_upgrades_local_incomplete_rows(tmp_path):
    src = _fill_store(tmp_path / "src", n=1)
    dst = Store(tmp_path / "dst")
    dst.claim_trial("t0", "e1", "algo", 0, 100, "crashed-worker")  # never finished
    out = dst.merge_from(src)
    assert out["trials"] == 1
    assert _trial_row(dst, "t0")["status"] == "done"
    assert _trial_row(dst, "t0")["best_fitness"] == 0.0


def test_merge_copies_artifact_files_to_local_paths(tmp_path):
    src = _fill_store(tmp_path / "src", n=1)
    art = tmp_path / "src" / "e1" / "t0.jsonl"
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_text('{"k": 1}\n')
    src.add_artifact("e1", "t0", "history_jsonl", str(art))

    dst = Store(tmp_path / "dst")
    out = dst.merge_from(src)
    assert out["artifacts"] == 1
    rows = dst.artifacts("e1")
    assert len(rows) == 1
    copied = Path(rows[0]["path"])
    assert copied.exists() and copied.read_text() == '{"k": 1}\n'
    assert str(tmp_path / "dst") in str(copied)  # local path, not the staging dir
    # Second merge: no duplicate artifact rows.
    assert dst.merge_from(src)["artifacts"] == 0


def test_store_migrates_pre_worker_schema(tmp_path):
    root = tmp_path / "runs"
    root.mkdir()
    conn = sqlite3.connect(root / "origin.db")
    conn.execute(
        "CREATE TABLE trials (id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL, algorithm TEXT NOT NULL,"
        " seed INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending', interactions INTEGER DEFAULT 0,"
        " budget INTEGER DEFAULT 0, best_fitness REAL, train_fitness REAL, metrics_json TEXT,"
        " transfer_json TEXT, error TEXT, started_at REAL, finished_at REAL)"
    )
    conn.commit()
    conn.close()
    store = Store(root)  # opens and migrates in place
    cols = {r["name"] for r in store._conn().execute("PRAGMA table_info(trials)")}
    assert {"worker_id", "claimed_at"} <= cols
    assert store.claim_trial("t1", "e1", "algo", 1, 100, "w1") == "claimed"


# ------------------------------------------------------- derive_work / ids #
def test_derive_work_is_deterministic():
    exp_a, work_a = derive_work(TINY_WORKER)
    exp_b, work_b = derive_work(TINY_WORKER)
    assert exp_a == exp_b == experiment_id(TINY_WORKER)
    assert work_a == work_b
    ids = [tid for _, _, tid in work_a]
    assert len(ids) == len(set(ids))
    for algo, seed, tid in work_a:
        assert tid == trial_id_for(exp_a, algo, seed)


# ------------------------------------------------------ the worker itself #
def test_worker_runs_campaign_end_to_end(tmp_path):
    worker = Worker(TINY_WORKER, store_root=tmp_path / "runs", worker_id="w-solo",
                    stale_after=30.0, heartbeat_interval=1.0)
    summary = worker.run()
    exp_id = summary["experiment_id"]
    store = Store(tmp_path / "runs")
    counts = store.trial_counts(exp_id)
    assert summary["failed"] == []
    assert counts.get("done") == 4  # 2 seeds x (1 algorithm + 1 baseline)
    assert counts.get("running", 0) == 0
    assert summary["n_completed"] == 4
    # Second run: everything already done, nothing claimed.
    summary2 = Worker(TINY_WORKER, store_root=tmp_path / "runs", worker_id="w-solo-2",
                      stale_after=30.0, heartbeat_interval=1.0).run()
    assert summary2["n_claimed"] == 0
    assert summary2["skipped"] and len(summary2["skipped"]) == 4


def test_worker_records_name_claimed_trials(tmp_path):
    worker = Worker(TINY_WORKER, store_root=tmp_path / "runs", worker_id="w-rec",
                    stale_after=30.0, heartbeat_interval=1.0)
    summary = worker.run()
    record = json.loads((Path(tmp_path / "runs") / summary["experiment_id"] / "worker-w-rec.json").read_text())
    assert record["claimed"] == summary["claimed"]
    assert record["completed"] == summary["completed"]


# --------------------------------------------- real multi-process workers #
def test_multiprocess_workers_share_store_exactly_once(tmp_path):
    """The Milestone 7 acceptance shape: several REAL worker processes, one
    shared store, every trial executed exactly once."""
    store_root = tmp_path / "runs"
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(TINY_WORKER))
    n_workers = 3

    procs = [
        subprocess.Popen(
            [sys.executable, "-m", "origin.experiments.worker",
             "--config", str(cfg_path), "--store", str(store_root),
             "--worker-id", f"mp-{i}", "--heartbeat", "0.2", "--stale-after", "30"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        for i in range(n_workers)
    ]
    outs = []
    for p in procs:
        out, err = p.communicate(timeout=300)
        assert p.returncode == 0, f"worker failed: {err}"
        outs.append(json.loads(out))

    exp_id = experiment_id(TINY_WORKER)
    store = Store(store_root)
    counts = store.trial_counts(exp_id)
    assert counts.get("done") == 4
    assert counts.get("running", 0) == 0

    # Exactly-once execution, audited from the per-worker records: claimed
    # sets are disjoint and their union is the full work list.
    claimed_sets = [set(o["claimed"]) for o in outs]
    union: set[str] = set()
    for s in claimed_sets:
        assert not (union & s), f"trial claimed by two workers: {union & s}"
        union |= s
    _, work = derive_work(TINY_WORKER)
    assert union == {tid for _, _, tid in work}
    total_completed = sum(o["n_completed"] for o in outs)
    assert total_completed == 4
    assert all(o["duplicates_dropped"] == [] for o in outs)

    # Every done row names the worker that executed it.
    for row in store.trials(exp_id):
        assert row["status"] == "done"
        assert row["worker_id"] and row["worker_id"].startswith("mp-")


def test_status_report_lists_workers_and_counts(tmp_path):
    worker = Worker(TINY_WORKER, store_root=tmp_path / "runs", worker_id="w-st",
                    stale_after=30.0, heartbeat_interval=1.0, max_trials=1)
    worker.run()
    report = status_report(tmp_path / "runs")
    assert any(w["id"] == "w-st" for w in report["workers"])
    assert report["trial_counts"].get("done") == 1
