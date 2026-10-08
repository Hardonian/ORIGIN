"""ORIGIN Cluster Manager: Spawns and manages multi-process compute workers locally or across hosts.

Usage:
    python scripts/cluster_manager.py --config configs/pilot.json --workers 4 --store runs
"""

from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
import time
from pathlib import Path

from origin.experiments.store import Store
from origin.experiments.worker import status_report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ORIGIN Local Cluster Manager")
    ap.add_argument("--config", required=True, help="path to experiment JSON config")
    ap.add_argument("--store", default="runs", help="experiment store directory")
    ap.add_argument("--workers", type=int, default=3, help="number of concurrent worker processes to launch")
    ap.add_argument("--stale-after", type=float, default=60.0, help="seconds before heartbeat is considered stale")
    ap.add_argument("--poll-interval", type=float, default=2.0, help="dashboard refresh interval in seconds")
    args = ap.parse_args(argv)

    cfg_path = Path(args.config).resolve()
    if not cfg_path.exists():
        print(f"Error: Config file not found: {cfg_path}")
        return 1

    store_path = Path(args.store).resolve()
    store = Store(store_path)

    print(f"Starting cluster of {args.workers} workers for config: {cfg_path.name}")
    print(f"Store: {store_path}")

    processes: list[subprocess.Popen] = []
    worker_ids: list[str] = []

    # Launch worker processes
    for i in range(args.workers):
        wid = f"cluster-w{i+1}-{int(time.time())}"
        worker_ids.append(wid)
        cmd = [
            sys.executable,
            "-m",
            "origin.experiments.worker",
            "--config",
            str(cfg_path),
            "--store",
            str(store_path),
            "--worker-id",
            wid,
            "--stale-after",
            str(args.stale_after),
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(proc)
        print(f"  [+] Spawned {wid} (PID {proc.pid})")

    interrupted = False

    def handle_sigint(_sig, _frame):
        nonlocal interrupted
        print("\nInterrupt received. Stopping workers gracefully...")
        interrupted = True
        for p in processes:
            if p.poll() is None:
                p.terminate()

    signal.signal(signal.SIGINT, handle_sigint)

    try:
        while not interrupted:
            # Check if all processes have exited
            all_done = all(p.poll() is not None for p in processes)
            counts = store.trial_counts()
            active_pids = [p.pid for p in processes if p.poll() is None]

            print(
                f"\r[Cluster] Active workers: {len(active_pids)}/{args.workers} | "
                f"Trials - done: {counts.get('done', 0)}, running: {counts.get('running', 0)}, "
                f"pending: {counts.get('pending', 0)}, failed: {counts.get('failed', 0)}",
                end="",
                flush=True,
            )

            if all_done:
                print("\nAll worker processes completed.")
                break

            time.sleep(args.poll_interval)

    except KeyboardInterrupt:
        handle_sigint(None, None)

    # Wait for child processes to terminate
    for p in processes:
        p.wait()

    print("\n--- Final Cluster Status ---")
    rep = status_report(store_path)
    print(json.dumps(rep["trial_counts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
