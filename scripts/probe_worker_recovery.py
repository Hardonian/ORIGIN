#!/usr/bin/env python3
"""Probe: SIGKILL a worker mid-trial and prove the campaign recovers.

This is the evidence for the Milestone 7 stale-worker recovery claim. A
scripted state manipulation cannot show what a real crash looks like, so this
probe kills a real worker process with SIGKILL (no cleanup runs, exactly like
a power loss) and then proves that:

1. the killed worker leaves an orphaned ``running`` trial behind;
2. the dead worker's heartbeat goes stale and is detected;
3. the next worker takes the orphaned trial over and finishes the campaign;
4. every trial ends ``done`` exactly once, with no lost and no duplicated
   recorded result.

Run:

    .venv/bin/python scripts/probe_worker_recovery.py

Exit code 0 = every check passed (evidence printed). Anything else = fail.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages"))

from origin.experiments.runner import experiment_id  # noqa: E402
from origin.experiments.store import Store  # noqa: E402
from origin.experiments.worker import Worker  # noqa: E402

# Trials here run ~8 s (measured), so a kill 0.5-1 s after a claim lands
# mid-trial with certainty, and the rescuer campaign is ~20 s total.
CFG = {
    "name": "probe-worker-recovery",
    "protocol": "probe",
    "env": {"height": 8, "width": 8, "max_steps": 30, "n_resources": 3, "n_hazards": 0,
            "obstacle_density": 0.05, "resource_regen": False, "step_penalty": 0.001,
            "wall_penalty": 0.0, "seed": 0},
    "train_seeds": [1, 2],
    "test_seeds": [7, 8],
    "budget": 200000,
    "seeds": [1, 2],
    "include_baselines": [],
    "transfer": {"adapt": False},
    "algorithms": {"fixed_objective_ga": {"pop_size": 12, "max_generations": 2000}},
}

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def main() -> int:
    store_root = Path(tempfile.mkdtemp(prefix="origin-probe-worker-"))
    print(f"probe store: {store_root}")
    try:
        exp_id = experiment_id(CFG)
        store = Store(store_root)
        expected_trials = len(CFG["seeds"])  # one algorithm, no baselines

        # ---------------------------------------------------------- victim
        victim = subprocess.Popen(
            [sys.executable, "-m", "origin.experiments.worker",
             "--config", str(_write_cfg(store_root)), "--store", str(store_root),
             "--worker-id", "probe-victim", "--heartbeat", "0.3", "--stale-after", "2",
             "--no-baselines"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        print(f"victim worker started (pid {victim.pid}); waiting for it to claim a trial...")

        orphan: list[dict] = []
        deadline = time.time() + 60
        while time.time() < deadline:
            rows = [dict(r) for r in store.trials(exp_id) if r["status"] == "running"]
            if rows:
                orphan = rows
                break
            time.sleep(0.02)
        if not orphan:
            victim.kill()
            check("victim claimed a trial before the deadline", False)
            return 1

        victim.kill()  # SIGKILL: no cleanup, like a crash / power loss
        victim.wait(timeout=10)
        print(f"  victim SIGKILLed mid-trial; orphaned row(s): {[r['id'] for r in orphan]}")
        for r in orphan:
            check(f"orphaned trial {r['id']} owned by probe-victim", r["worker_id"] == "probe-victim")

        post = [dict(r) for r in store.trials(exp_id)]
        running_after_kill = [r for r in post if r["status"] == "running"]
        check("the store still shows the running row after the crash (no silent gap)",
              len(running_after_kill) == len(orphan),
              f"{len(running_after_kill)} running row(s)")

        # ------------------------------------- heartbeat goes stale -> reaped
        stale_after = 2.0
        print(f"waiting {stale_after + 0.5:.1f}s for the victim's heartbeat to go stale...")
        time.sleep(stale_after + 0.5)

        # ---------------------------------------------------------- rescuer
        print("starting rescuer worker...")
        rescuer = Worker(CFG, store_root=store_root, worker_id="probe-rescuer",
                         stale_after=stale_after, heartbeat_interval=0.5,
                         include_baselines=False)
        summary = rescuer.run()
        print(f"  rescuer summary: claimed={summary['claimed']} completed={summary['completed']} "
              f"recovered={summary['recovered_trials']} taken_over={summary['taken_over']}")

        # ---------------------------------------------------------- checks
        check("victim detected as dead worker",
              "probe-victim" in summary["dead_workers_seen"],
              f"dead_workers_seen={summary['dead_workers_seen']}")
        recovered = set(summary["recovered_trials"]) | set(summary["taken_over"])
        orphan_ids = {r["id"] for r in orphan}
        check("every orphaned trial was recovered", orphan_ids <= recovered,
              f"orphans={sorted(orphan_ids)} recovered={sorted(recovered)}")
        check("no trial failed in recovery", summary["failed"] == [], str(summary["failed"]))
        check("no duplicate result was recorded", summary["duplicates_dropped"] == [],
              str(summary["duplicates_dropped"]))

        counts = store.trial_counts(exp_id)
        check("all trials done", counts.get("done") == expected_trials, f"counts={counts}")
        check("no trial left running or pending",
              counts.get("running", 0) == 0 and counts.get("pending", 0) == 0, f"counts={counts}")

        rows = [dict(r) for r in store.trials(exp_id)]
        check("every done row names its executing worker",
              all(r["worker_id"] for r in rows), str([(r["id"], r["worker_id"]) for r in rows]))
        check("exactly one recorded result per trial (deterministic trial ids)",
              len({r["id"] for r in rows}) == expected_trials)

        # The rescued trial really was recomputed by the rescuer (the victim's
        # work died with it), and its result is recorded under the rescuer.
        rescued_rows = [r for r in rows if r["id"] in orphan_ids]
        check("rescued trials recorded under the rescuer",
              all(r["worker_id"] == "probe-rescuer" for r in rescued_rows),
              str([(r["id"], r["worker_id"]) for r in rescued_rows]))

        print("\nRESULT:", "ALL CHECKS PASSED" if not FAILURES else f"{len(FAILURES)} CHECK(S) FAILED: {FAILURES}")
        return 0 if not FAILURES else 1
    finally:
        shutil.rmtree(store_root, ignore_errors=True)


def _write_cfg(store_root: Path) -> Path:
    p = store_root / "probe-config.json"
    p.write_text(json.dumps(CFG))
    return p


if __name__ == "__main__":
    raise SystemExit(main())
