#!/usr/bin/env python
"""Probe whether the embodied morphology can locomote at all.

Motivation (2026-10-08): the M4 embodied campaign scored high for controllers
that travelled and then fell, yet no method ever reached the target upright.
Before redesigning the task, the morphology itself was probed:

1. **Rest stability** — does the body stay upright for a full episode with zero
   input? (The pre-fix body toppled spontaneously: all links were parented to
   the base at a single point and the capsules stood vertically.)
2. **Locomotion sweep** — drive the environment's own motor primitives across a
   torque range and measure net displacement.
3. **Joint-axis sweep** — rebuild the same chain with yaw-axis joints (lateral
   undulation, the standard snake-robot arrangement) and sweep torques/gaits in
   a raw PyBullet harness, to separate "bad gaits" from "unlocomotable body".

Finding (recorded in research/reports/ORIGIN_M4_Embodied_Transfer_Report.md):
no variant travels more than a few millimetres in 6 s of actuation. The task is
unsolvable as configured; the morphology needs a design pass (e.g. anisotropic
friction or a different actuation scheme), not parameter tuning.

Usage:
  .venv/bin/python scripts/probe_embodied_morphology.py
"""

from __future__ import annotations

import numpy as np

from origin.environments.embodied import ACTION_NAMES, EmbodiedConfig, EmbodiedCreature


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


def primitive_sweep(cfg: EmbodiedConfig) -> None:
    print("== motor primitives x torque (net displacement over one episode) ==")
    for torque in (0.2, 0.5, 1.4):
        row = []
        for a in range(5):
            c = EmbodiedConfig.from_dict({**cfg.to_dict(), "joint_max_torque": torque})
            env = EmbodiedCreature(c)
            env.reset(seed=0)
            steps = 0
            while True:
                _obs, _r, term, trunc, info = env.step(a)
                steps += 1
                if term or trunc:
                    break
            row.append(f"{ACTION_NAMES[a]}={info['distance_travelled']:+.3f}m/{steps}st")
            env.close()
        print(f"  torque={torque:3.1f}: " + "  ".join(row))


def _raw_chain(joint_axis: list[float], program: str, max_torque: float,
               n: int = 10, link_length: float = 0.10, radius: float = 0.028,
               mass: float = 0.12, friction: float = 0.9,
               episode_seconds: float = 6.0) -> tuple[float, float]:
    """Same chain as the environment, with a configurable joint axis."""
    import pybullet as p
    import pybullet_data

    client = p.connect(p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=client)
    p.setGravity(0, 0, -9.81, physicsClientId=client)
    p.setTimeStep(1.0 / 240.0, physicsClientId=client)
    plane = p.loadURDF("plane.urdf", physicsClientId=client)
    p.changeDynamics(plane, -1, lateralFriction=friction, physicsClientId=client)

    lie = p.getQuaternionFromEuler([0.0, np.pi / 2.0, 0.0])
    shape = p.createCollisionShape(p.GEOM_CAPSULE, radius=radius, height=link_length,
                                   collisionFrameOrientation=lie, physicsClientId=client)
    vis = p.createVisualShape(p.GEOM_CAPSULE, radius=radius, length=link_length,
                              visualFrameOrientation=lie, physicsClientId=client)
    body = p.createMultiBody(
        baseMass=mass * 1.5, baseCollisionShapeIndex=shape, baseVisualShapeIndex=vis,
        basePosition=[0, 0, radius + 0.01],
        linkMasses=[mass] * n, linkCollisionShapeIndices=[shape] * n,
        linkVisualShapeIndices=[vis] * n,
        linkPositions=[[link_length, 0, 0]] * n, linkOrientations=[[0, 0, 0, 1]] * n,
        linkInertialFramePositions=[[0, 0, 0]] * n,
        linkInertialFrameOrientations=[[0, 0, 0, 1]] * n,
        linkParentIndices=list(range(n)),
        linkJointTypes=[p.JOINT_REVOLUTE] * n, linkJointAxis=[joint_axis] * n,
        physicsClientId=client,
    )
    for j in range(n):
        p.changeDynamics(body, j, lateralFriction=friction, physicsClientId=client)
    p.changeDynamics(body, -1, lateralFriction=friction, physicsClientId=client)

    steps = int(episode_seconds * 30)
    for t in range(steps):
        if program == "none":
            tor = np.zeros(n)
        else:
            freq = 0.08 if program == "wave" else 0.03
            tor = np.sin(2 * np.pi * (np.arange(n) / n) - 2 * np.pi * t * freq) * max_torque
        for _ in range(8):
            p.setJointMotorControlArray(body, list(range(n)), p.TORQUE_CONTROL,
                                        forces=[float(v) for v in tor], physicsClientId=client)
            p.stepSimulation(physicsClientId=client)

    pos, orn = p.getBasePositionAndOrientation(body, physicsClientId=client)
    up_dev = abs(1.0 - float(p.getMatrixFromQuaternion(orn)[8]))
    p.disconnect(physicsClientId=client)
    return float(pos[0]), up_dev


def joint_axis_sweep() -> None:
    print("== joint axis x torque x gait (raw chain harness) ==")
    for axis_label, axis in (("pitch(y)", [0.0, 1.0, 0.0]), ("yaw(z)", [0.0, 0.0, 1.0])):
        for program in ("none", "wave", "slow"):
            for torque in (0.4, 0.8, 1.4):
                x, up_dev = _raw_chain(axis, program, torque)
                print(f"  {axis_label:9s} {program:5s} torque={torque:3.1f}: x={x:+.3f} m  max_tilt_dev={up_dev:.3f}")


def main() -> int:
    cfg = campaign_config()
    rest_stability(cfg)
    primitive_sweep(cfg)
    joint_axis_sweep()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
