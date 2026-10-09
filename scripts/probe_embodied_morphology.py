#!/usr/bin/env python
"""Calibrate whether the embodied crawler can locomote before spending seeds.

The v2 morphology was a vertical-plane torque chain on isotropic ground and
could not locomote.  The current model is a yaw-jointed crawler with
direction-dependent contact and force-limited position motors.  This script is
its acceptance harness, not a substitute for a campaign:

1. **Rest stability** — braking must not itself cause a fall.
2. **Production-gait sweep** — run the exact five actions exposed to policies,
   measure net x motion, lateral drift and upright completion.
3. **Acceptance** — at least one unprivileged motor program must advance by
   5 cm in a three-second calibration episode.  Only after that passes should a
   fresh transfer campaign be configured; no retracted v2 result is revived.

Usage:
  .venv/bin/python scripts/probe_embodied_morphology.py
  .venv/bin/python scripts/probe_embodied_morphology.py \
      --config configs/actor_critic_embodied_v2.json \
      --json-out runs/actor_critic_embodied_v2-calibration.json
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np

from origin.environments.embodied import EmbodiedConfig, EmbodiedCreature
from origin.environments.embodied import p as pybullet_engine

ACCEPTANCE_GAIN_M = 0.05
CALIBRATION_SECONDS = 3.0
PROGRAMS: dict[str, tuple[int, ...]] = {
    "wave_a": (2,),
    "wave_b": (3,),
    "wave_23": (2, 3),
    "wave_32": (3, 2),
    "flex_extend": (0, 1),
}


def campaign_config() -> EmbodiedConfig:
    """The historical v3 transfer body used when no registration is supplied."""
    return EmbodiedConfig.preset(
        "centipede", n_links=10, link_length=0.10, link_radius=0.028, link_mass=0.12,
        joint_max_torque=1.4, lateral_friction=0.9, episode_seconds=6.0, target_distance=3.0,
    )


def config_from_registration(path: Path) -> EmbodiedConfig:
    """Load exactly the embodied body declared by an experiment registration."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("env_kind") != "embodied":
        raise ValueError("registered calibration config must declare env_kind='embodied'")
    env = data.get("env")
    if not isinstance(env, dict):
        raise ValueError("registered calibration config must contain an env object")
    return EmbodiedConfig.from_dict(env)


def rest_stability(cfg: EmbodiedConfig) -> list[dict[str, Any]]:
    print("== rest stability (motor primitive: brake) ==")
    results: list[dict[str, Any]] = []
    for n_links in dict.fromkeys((cfg.n_links, 5, 10, 20)):
        c = EmbodiedConfig.from_dict({**cfg.to_dict(), "n_links": n_links})
        env = EmbodiedCreature(c)
        try:
            env.reset(seed=0)
            fell_at = None
            for step in range(1, c.max_steps + 1):
                _obs, _r, term, trunc, _info = env.step(4)
                if term:
                    fell_at = step
                    break
                if trunc:
                    break
        finally:
            env.close()
        survived = fell_at is None
        results.append({"n_links": n_links, "survived": survived, "fell_at_step": fell_at})
        message = f"survived {c.max_steps} steps" if survived else f"toppled at step {fell_at}"
        print(f"  n_links={n_links:2d}: {message}")
    return results


def gait_sweep(cfg: EmbodiedConfig) -> tuple[float, list[dict[str, Any]]]:
    """Exercise production actions, returning the best gain and evidence rows."""
    print(f"== production gait programs ({CALIBRATION_SECONDS:g} s calibration) ==")
    best = float("-inf")
    results: list[dict[str, Any]] = []
    short = EmbodiedConfig.from_dict({**cfg.to_dict(), "episode_seconds": CALIBRATION_SECONDS})
    for name, program in PROGRAMS.items():
        env = EmbodiedCreature(short)
        try:
            _obs, info = env.reset(seed=0)
            start = np.asarray(info["position"], dtype=float)
            while True:
                action = program[info["steps"] % len(program)]
                _obs, _reward, term, trunc, info = env.step(action)
                if term or trunc:
                    break
            finish = np.asarray(info["position"], dtype=float)
            gain = float(finish[0] - start[0])
            drift = float(abs(finish[1] - start[1]))
            row = {
                "program": name,
                "actions": list(program),
                "x_gain_m": gain,
                "lateral_drift_m": drift,
                "upright": bool(info["upright"]),
                "success": bool(info["success"]),
                "steps": int(info["steps"]),
            }
            results.append(row)
            best = max(best, gain)
            print(
                f"  {name:11s}: x_gain={gain:+.3f}m  lateral_drift={drift:.3f}m  "
                f"upright={info['upright']} success={info['success']}"
            )
        finally:
            env.close()
    return best, results


def write_report(report: dict[str, Any], output: Path | None) -> None:
    if output is None:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    # Publish only a complete JSON document.  A killed probe must not replace a
    # previously captured artifact with a truncated file that the API can read.
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(f"wrote calibration evidence: {output}")


def unavailable_report(cfg: EmbodiedConfig) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "passed": False,
        "config_hash": cfg.config_hash(),
        "reason": "PyBullet is not importable in this environment.",
        "config": cfg.to_dict(),
        "acceptance": {
            "minimum_forward_gain_m": ACCEPTANCE_GAIN_M,
            "duration_seconds": CALIBRATION_SECONDS,
            "command": "uv pip install -e '.[dev,embodied]' --python .venv/bin/python",
        },
        "runtime": {"python": sys.version.split()[0], "platform": platform.platform()},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json-out",
        type=Path,
        help="write a machine-readable calibration evidence report to this path",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="registered embodied experiment JSON whose exact env body must be calibrated",
    )
    args = parser.parse_args(argv)
    try:
        cfg = config_from_registration(args.config) if args.config else campaign_config()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(f"invalid calibration configuration: {exc}")

    if pybullet_engine is None:
        report = unavailable_report(cfg)
        report["registered_config"] = str(args.config) if args.config else None
        write_report(report, args.json_out)
        print("UNAVAILABLE: PyBullet is required; install the embodied extra on a supported host.")
        return 2

    rest = rest_stability(cfg)
    best_gain, gaits = gait_sweep(cfg)
    passed = best_gain >= ACCEPTANCE_GAIN_M
    report = {
        "status": "passed" if passed else "failed",
        "passed": passed,
        "registered_config": str(args.config) if args.config else None,
        "config_hash": cfg.config_hash(),
        "config": cfg.to_dict(),
        "acceptance": {
            "minimum_forward_gain_m": ACCEPTANCE_GAIN_M,
            "duration_seconds": CALIBRATION_SECONDS,
            "best_forward_gain_m": best_gain,
        },
        "rest_stability": rest,
        "gaits": gaits,
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "pybullet_api_version": getattr(pybullet_engine, "getAPIVersion", lambda: None)(),
        },
    }
    write_report(report, args.json_out)
    if not passed:
        print(
            f"FAIL: best forward gain {best_gain:.3f}m is below the "
            f"{ACCEPTANCE_GAIN_M:.3f}m acceptance threshold"
        )
        return 1
    print(f"PASS: best forward gain {best_gain:.3f}m meets the 0.050m acceptance threshold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
