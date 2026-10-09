#!/usr/bin/env python3
"""Record high-fidelity PyBullet 3D kinematics trajectories for embodied trials.

Runs in PyBullet DIRECT mode on a supported host (e.g. epyc), loading the
persisted organism checkpoint and stepping the policy on an evaluation seed.
Saves the full physics trajectory to `runs/<exp_id>/<trial_id>.trajectory.json`.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from origin.environments.embodied import ACTION_NAMES, EmbodiedConfig, EmbodiedCreature
from origin.experiments.store import Store
from origin.organisms import Organism


def record_trial_trajectory(
    store_root: str,
    exp_id: str,
    trial_id: str,
    seed: int = 101,
) -> dict[str, Any]:
    store = Store(store_root)
    exp = store.experiment(exp_id)
    if not exp:
        raise FileNotFoundError(f"experiment {exp_id} not found in store")

    cfg = json.loads(exp["config_json"])
    env_cfg = EmbodiedConfig.from_dict(cfg["env"])

    org_path = Path(store_root) / exp_id / f"{trial_id}.organism.json"
    if not org_path.exists():
        raise FileNotFoundError(f"organism checkpoint not found: {org_path}")

    org_dict = json.loads(org_path.read_text())
    organism = Organism.from_dict(org_dict)

    creature = EmbodiedCreature(env_cfg)
    trajectory: list[dict[str, Any]] = []

    try:
        obs, info = creature.reset(seed=seed)

        # Capture initial state at step 0
        state0 = creature.get_state()
        base_pos0 = [round(float(v), 5) for v in state0["base_position"]]
        base_orn0 = [round(float(v), 5) for v in state0["base_orientation"]]
        angles0 = [round(float(v), 4) for v in state0["joint_positions"]]

        trajectory.append({
            "step": 0,
            "time_s": 0.0,
            "base_pos": base_pos0,
            "base_orn": base_orn0,
            "joint_angles": angles0,
            "action": 4,
            "action_name": "brake",
            "reward": 0.0,
            "cumulative_reward": 0.0,
            "distance_to_target": round(float(info.get("target_distance", env_cfg.target_distance)), 4),
            "upright": True,
            "success": False,
        })

        cum_reward = 0.0
        for step_idx in range(1, env_cfg.max_steps + 1):
            action = int(organism.act(obs))
            obs, reward, term, trunc, info = creature.step(action)
            cum_reward += float(reward)

            st = creature.get_state()
            base_pos = [round(float(v), 5) for v in st["base_position"]]
            base_orn = [round(float(v), 5) for v in st["base_orientation"]]
            angles = [round(float(v), 4) for v in st["joint_positions"]]

            trajectory.append({
                "step": step_idx,
                "time_s": round(step_idx * env_cfg.control_dt, 4),
                "base_pos": base_pos,
                "base_orn": base_orn,
                "joint_angles": angles,
                "action": action,
                "action_name": ACTION_NAMES.get(action, str(action)),
                "reward": round(float(reward), 4),
                "cumulative_reward": round(cum_reward, 4),
                "distance_to_target": round(float(info.get("target_distance", 0.0)), 4),
                "upright": bool(info.get("upright", True)),
                "success": bool(info.get("success", False)),
            })

            if term or trunc:
                break

    finally:
        creature.close()

    total_dist = math.sqrt(
        (trajectory[-1]["base_pos"][0] - trajectory[0]["base_pos"][0]) ** 2
        + (trajectory[-1]["base_pos"][1] - trajectory[0]["base_pos"][1]) ** 2
    )

    out = {
        "experiment_id": exp_id,
        "trial_id": trial_id,
        "seed": seed,
        "morphology": env_cfg.morphology,
        "n_links": env_cfg.n_links,
        "link_length": env_cfg.link_length,
        "link_radius": env_cfg.link_radius,
        "joint_axis": env_cfg.joint_axis,
        "target_distance": env_cfg.target_distance,
        "steps": len(trajectory) - 1,
        "total_reward": round(cum_reward, 4),
        "total_displacement_m": round(total_dist, 4),
        "final_upright": trajectory[-1]["upright"],
        "success": trajectory[-1]["success"],
        "trajectory": trajectory,
    }

    out_file = Path(store_root) / exp_id / f"{trial_id}.trajectory.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(out, indent=2))
    print(f"Recorded trajectory for {trial_id} (seed={seed}): {len(trajectory)} steps, {total_dist:.3f}m -> {out_file}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Record PyBullet kinematics trajectory")
    ap.add_argument("--store", default="runs")
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--trial", default=None, help="specific trial id, or omit for all done trials")
    ap.add_argument("--seed", type=int, default=101)
    args = ap.parse_args()

    store = Store(args.store)
    trials = [t for t in store.trials(args.experiment) if t["status"] == "done"]

    if args.trial:
        target_trials = [t for t in trials if t["id"] == args.trial]
    else:
        # Default: record all learner trials with checkpoints
        target_trials = [t for t in trials if (Path(args.store) / args.experiment / f"{t['id']}.organism.json").exists()]

    if not target_trials:
        print(f"No matching trials found in experiment {args.experiment}")
        return 1

    print(f"Recording physics trajectories for {len(target_trials)} trial(s)...")
    for t in target_trials:
        record_trial_trajectory(args.store, args.experiment, t["id"], seed=args.seed)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
