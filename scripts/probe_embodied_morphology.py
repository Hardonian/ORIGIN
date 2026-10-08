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
"""

from __future__ import annotations

import numpy as np

from origin.environments.embodied import EmbodiedConfig, EmbodiedCreature


def campaign_config() -> EmbodiedConfig:
    """The exact body used by configs/embodied_transfer.json."""
    return EmbodiedConfig.preset(
        "centipede", n_links=10, link_length=0.10, link_radius=0.028, link_mass=0.12,
        joint_max_torque=1.4, lateral_friction=0.9, episode_seconds=6.0, target_distance=3.0,
    )


def rest_stability(cfg: EmbodiedConfig) -> None:
    print("== rest stability (motor primitive: brake) ==")
    for n_links in (5, 10, 20):
        c = EmbodiedConfig.from_dict({**cfg.to_dict(), "n_links": n_links})
        env = EmbodiedCreature(c)
        env.reset(seed=0)
        fell_at = None
        for step in range(1, c.max_steps + 1):
            _obs, _r, term, trunc, info = env.step(4)
            if term:
                fell_at = step
                break
            if trunc:
                break
        print(f"  n_links={n_links:2d}: {'survived ' + str(c.max_steps) + ' steps' if fell_at is None else 'toppled at step ' + str(fell_at)}")
        env.close()


def gait_sweep(cfg: EmbodiedConfig) -> float:
    """Exercise the production actions, returning the best forward gain."""
    print("== production gait programs (3 s calibration) ==")
    programs = {
        "wave_a": (2,),
        "wave_b": (3,),
        "wave_23": (2, 3),
        "wave_32": (3, 2),
        "flex_extend": (0, 1),
    }
    best = float("-inf")
    short = EmbodiedConfig.from_dict({**cfg.to_dict(), "episode_seconds": 3.0})
    for name, program in programs.items():
        env = EmbodiedCreature(short)
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
        best = max(best, gain)
        print(
            f"  {name:11s}: x_gain={gain:+.3f}m  lateral_drift={drift:.3f}m  "
            f"upright={info['upright']} success={info['success']}"
        )
        env.close()
    return best


def main() -> int:
    cfg = campaign_config()
    rest_stability(cfg)
    best_gain = gait_sweep(cfg)
    if best_gain < 0.05:
        print(f"FAIL: best forward gain {best_gain:.3f}m is below the 0.050m acceptance threshold")
        return 1
    print(f"PASS: best forward gain {best_gain:.3f}m meets the 0.050m acceptance threshold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
