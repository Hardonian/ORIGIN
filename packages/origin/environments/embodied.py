"""Embodied intelligence: articulated bodies simulated in a real physics engine.

Milestone 4. Where ``GridWorld`` studies sensor/actuator/body changes on a grid,
this module studies **morphology transfer across genuinely different body plans**
simulated with PyBullet: different link counts, link lengths, masses, joint
torques and friction.

Design note — why the control interface stays small and fixed
-------------------------------------------------------------
A body with N joints still exposes a **fixed-size** observation
(``[heading_error, yaw_vel, mean_joint_angle, mean_joint_vel, height,
heading_alignment, target_distance]``, 7-D) and a **fixed discrete action set** of
5 motor primitives.
The morphology changes the *dynamics* the controller must cope with, not the size of
its interface. That is what makes "transfer a controller to a different body" a
well-posed experiment instead of a shape error, and it lets every existing ORIGIN
algorithm (GA, novelty search, MAP-Elites, REINFORCE) run unchanged.

Task and reward — "reach the target while upright"
-------------------------------------------------
The task is only *solved* by reaching the target region while upright. Reward is
shaped by progress toward the target, and the shaping is **potential-based**
(``Phi`` = progress remaining): the failure state's potential is defined as zero,
so a fall *cancels* every unit of shaping banked so far and the episode returns
exactly ``-fall_penalty``. Without that cancellation a controller could maximise
reward by dashing toward the target and face-planting — banking all the progress
shaping and paying only the small fall penalty — which measures "travelled far",
not "locomoted upright". Success, fall and timeout are reported separately in
``info`` (``success`` / ``upright``), so partial competence (distance travelled,
upright fraction) remains visible in the metrics even though it no longer leaks
into the return of a failed episode.

Determinism: a fixed timestep, a fixed number of physics substeps per control step,
no wall-clock dependence, and seeded initial jitter make a rollout reproducible.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

try:
    import pybullet as p
    import pybullet_data
except Exception:  # pragma: no cover - only when pybullet missing
    p = None  # type: ignore
    pybullet_data = None  # type: ignore

# Motor primitives: index -> torque pattern applied to every joint.
# 0 flex, 1 extend, 2/3 travelling waves (gait), 4 brake/hold
N_ACTIONS = 5
ACTION_NAMES = {0: "flex", 1: "extend", 2: "wave_a", 3: "wave_b", 4: "brake"}

MORPHOLOGY_PRESETS: dict[str, dict[str, Any]] = {
    # name -> body plan parameters (see EmbodiedConfig)
    # Every current preset is a ground crawler.  A yaw joint plus higher transverse
    # than longitudinal friction is the minimum physically meaningful arrangement
    # for a snake-like travelling wave to create forward thrust.
    "worm": {"n_links": 8, "link_length": 0.16, "link_radius": 0.035, "link_mass": 0.25,
             "joint_max_torque": 2.5, "lateral_friction": 1.25, "longitudinal_friction": 0.20,
             "joint_axis": "yaw"},
    "centipede": {"n_links": 14, "link_length": 0.10, "link_radius": 0.028, "link_mass": 0.12,
                  "joint_max_torque": 1.4, "lateral_friction": 1.30, "longitudinal_friction": 0.18,
                  "joint_axis": "yaw"},
    "hopper": {"n_links": 3, "link_length": 0.30, "link_radius": 0.055, "link_mass": 0.9,
               "joint_max_torque": 7.0, "lateral_friction": 1.10, "longitudinal_friction": 0.20,
               "joint_axis": "yaw"},
}


@dataclass
class EmbodiedConfig:
    """Configuration schema for the embodied environment (validated in ``validate``)."""

    morphology: str = "worm"
    n_links: int = 8
    link_length: float = 0.16
    link_radius: float = 0.035
    link_mass: float = 0.25
    joint_max_torque: float = 2.5
    joint_limit: float = 1.10          # rad, symmetric
    # Direction-dependent contact makes the travelling wave a locomotion gait
    # rather than a symmetric in-place wiggle.  Friction is expressed in the
    # body's local frame: +x is along a capsule, +y is transverse to it.
    lateral_friction: float = 1.25
    longitudinal_friction: float = 0.20
    joint_axis: str = "yaw"            # yaw (ground crawler) or pitch (experimental)
    gait_amplitude: float = 0.60        # fraction of joint_limit used by a wave
    motor_position_gain: float = 0.35
    motor_velocity_gain: float = 0.75
    gravity: float = -9.81

    episode_seconds: float = 8.0
    physics_dt: float = 1.0 / 240.0
    control_dt: float = 1.0 / 30.0     # one controller action per control_dt
    torque_gain: float = 1.0

    target_distance: float = 3.0       # metres along +x
    target_tolerance: float = 0.25
    fall_height: float = 0.12          # base below this == fell over
    progress_scale: float = 10.0
    target_reward: float = 5.0
    # Deliberately zero: a per-step reward merely for existing let a policy collect
    # ~1.8 by standing still and never moving (verified by probe). Staying upright is
    # incentivised by the fall penalty + episode termination instead, so locomotion
    # strictly dominates standing.
    upright_bonus: float = 0.0
    energy_penalty: float = 0.002
    # On a fall the episode return collapses to exactly -fall_penalty: the shaping
    # banked so far is cancelled (see the module docstring), so "travel far, then
    # fall" can never outscore "travel less, stay upright".
    fall_penalty: float = 1.0
    init_jitter: float = 0.0           # rad, seeded
    seed: int = 0

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.morphology not in MORPHOLOGY_PRESETS:
            raise ValueError(f"morphology must be one of {sorted(MORPHOLOGY_PRESETS)}, got {self.morphology!r}")
        if self.n_links < 1:
            raise ValueError("n_links must be >= 1")
        if self.link_length <= 0 or self.link_radius <= 0 or self.link_mass <= 0:
            raise ValueError("link_length, link_radius and link_mass must be > 0")
        if self.joint_max_torque <= 0:
            raise ValueError("joint_max_torque must be > 0")
        if self.lateral_friction <= 0 or self.longitudinal_friction <= 0:
            raise ValueError("lateral_friction and longitudinal_friction must be > 0")
        if self.joint_axis not in {"yaw", "pitch"}:
            raise ValueError("joint_axis must be 'yaw' or 'pitch'")
        if not 0 < self.gait_amplitude <= 1:
            raise ValueError("gait_amplitude must be in (0, 1]")
        if self.motor_position_gain <= 0 or self.motor_velocity_gain < 0:
            raise ValueError("motor_position_gain must be > 0 and motor_velocity_gain must be >= 0")
        if not 0 < self.joint_limit <= np.pi:
            raise ValueError("joint_limit must be in (0, pi]")
        if self.episode_seconds <= 0:
            raise ValueError("episode_seconds must be > 0")
        if self.physics_dt <= 0 or self.control_dt <= 0:
            raise ValueError("physics_dt and control_dt must be > 0")
        if self.physics_dt > self.control_dt:
            raise ValueError("physics_dt must be <= control_dt (substeps per control step)")
        if self.target_tolerance <= 0:
            raise ValueError("target_tolerance must be > 0")

    @classmethod
    def preset(cls, morphology: str, **overrides: Any) -> EmbodiedConfig:
        """Build a config from a named body plan, with optional overrides."""
        if morphology not in MORPHOLOGY_PRESETS:
            raise ValueError(f"unknown morphology preset {morphology!r}")
        params = dict(MORPHOLOGY_PRESETS[morphology])
        params.update(overrides)
        return cls(morphology=morphology, **params)

    @property
    def n_substeps(self) -> int:
        return max(1, int(round(self.control_dt / self.physics_dt)))

    @property
    def max_steps(self) -> int:
        return max(1, int(round(self.episode_seconds / self.control_dt)))

    @property
    def n_actions(self) -> int:
        return N_ACTIONS

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EmbodiedConfig:
        known = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
        unknown = set(d) - known
        if unknown:
            raise ValueError(f"unknown config fields: {sorted(unknown)}")
        return cls(**d)

    def config_hash(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()[:16]


class EmbodiedCreature:
    """A planar articulated creature driven by discrete motor primitives."""

    def __init__(self, config: EmbodiedConfig | None = None, gui: bool = False):
        if p is None or pybullet_data is None:  # pragma: no cover
            raise RuntimeError("pybullet is required for EmbodiedCreature")
        # Non-optional aliases: static type checkers cannot narrow a module-level
        # optional import across methods, so bind them once here.
        self._p = p
        self._pd = pybullet_data
        # Own a copy: reset(seed=...) writes the active seed into the config, and
        # mutating a caller's shared config object would make unrelated runs
        # depend on each other's episode order.
        self.config = EmbodiedConfig.from_dict(config.to_dict()) if config is not None else EmbodiedConfig()
        self._client = self._p.connect(self._p.GUI if gui else self._p.DIRECT)
        self._body: int | None = None
        self._n_joints = int(self.config.n_links)
        # Resting height of the base capsule; used for spawn, target and fall detection.
        self._rest_z = self.config.link_radius + 0.01
        self._target = np.array([self.config.target_distance, 0.0, self._rest_z], dtype=float)
        self._steps = 0
        self._prev_dist = 0.0
        self._distance_travelled = 0.0
        self._upright_steps = 0
        self._energy = 0.0
        self._banked = 0.0
        self._success = False
        self._rng = np.random.default_rng(self.config.seed)
        self._plane: int | None = None
        try:
            self._build_world()
        except Exception:
            # Never leak a physics client, even if world construction fails.
            with contextlib.suppress(Exception):  # pragma: no cover
                self._p.disconnect(physicsClientId=self._client)
            raise

    # ------------------------------------------------------------------ #
    # World construction
    # ------------------------------------------------------------------ #
    def _build_world(self) -> None:
        cfg = self.config
        self._p.resetSimulation(physicsClientId=self._client)
        self._p.setGravity(0.0, 0.0, cfg.gravity, physicsClientId=self._client)
        self._p.setTimeStep(cfg.physics_dt, physicsClientId=self._client)
        self._p.setAdditionalSearchPath(self._pd.getDataPath(), physicsClientId=self._client)
        self._plane = self._p.loadURDF("plane.urdf", physicsClientId=self._client)
        self._p.changeDynamics(self._plane, -1, lateralFriction=cfg.lateral_friction, physicsClientId=self._client)
        self._build_body()

    def _build_body(self) -> None:
        """Procedurally build a planar chain: base + ``n_links`` revolute links."""
        cfg = self.config
        n = self._n_joints
        # PyBullet capsules are aligned with their local z axis; the chain extends
        # along +x, so each capsule is rotated +90 deg about y to lie along its link
        # direction. Without this the links are *vertical* posts joined end to end
        # — a standing multi-pendulum that topples even with zero input (probe:
        # "constant brake" fell after ~70 steps).
        lie_along_x = self._p.getQuaternionFromEuler([0.0, np.pi / 2.0, 0.0])
        shape = self._p.createCollisionShape(
            self._p.GEOM_CAPSULE, radius=cfg.link_radius, height=cfg.link_length,
            collisionFrameOrientation=lie_along_x, physicsClientId=self._client,
        )
        vis = self._p.createVisualShape(
            self._p.GEOM_CAPSULE, radius=cfg.link_radius, length=cfg.link_length,
            visualFrameOrientation=lie_along_x,
            rgbaColor=[0.35, 0.6, 0.95, 1.0], physicsClientId=self._client,
        )
        link_masses = [cfg.link_mass] * n
        link_collision = [shape] * n
        link_visual = [vis] * n
        # Links lie on the ground along +x.  Their default yaw joints bend the
        # chain in the ground plane, which is the conventional snake-robot body
        # plan.  ``pitch`` is retained only as an explicit experimental option;
        # it is not a viable default gait for a body resting on a flat plane.
        link_positions = [[cfg.link_length, 0.0, 0.0]] * n
        link_orientations = [[0.0, 0.0, 0.0, 1.0]] * n
        link_inertial_pos = [[0.0, 0.0, 0.0]] * n
        link_inertial_orn = [[0.0, 0.0, 0.0, 1.0]] * n
        # A serial chain: link 0 hangs off the base, link i off link i-1. (Parent
        # index 0 is the base; every entry as 0 would stack all links at one point
        # — a wobbling clump that topples at rest even with zero input, verified
        # by probe. The chain is what the presets and the docstring describe.)
        link_parent = list(range(n))
        link_joint_type = [self._p.JOINT_REVOLUTE] * n
        joint_axis = [0.0, 0.0, 1.0] if cfg.joint_axis == "yaw" else [0.0, 1.0, 0.0]
        link_joint_axis = [joint_axis] * n

        self._body = self._p.createMultiBody(
            baseMass=cfg.link_mass * 1.5,
            baseCollisionShapeIndex=shape,
            baseVisualShapeIndex=vis,
            basePosition=[0.0, 0.0, self._rest_z],
            baseOrientation=[0.0, 0.0, 0.0, 1.0],
            linkMasses=link_masses,
            linkCollisionShapeIndices=link_collision,
            linkVisualShapeIndices=link_visual,
            linkPositions=link_positions,
            linkOrientations=link_orientations,
            linkInertialFramePositions=link_inertial_pos,
            linkInertialFrameOrientations=link_inertial_orn,
            linkParentIndices=link_parent,
            linkJointTypes=link_joint_type,
            linkJointAxis=link_joint_axis,
            physicsClientId=self._client,
        )
        for j in range(n):
            self._p.setJointMotorControl2(
                self._body, j, self._p.VELOCITY_CONTROL, force=0.0, physicsClientId=self._client
            )
            self._set_link_dynamics(j)
        self._set_link_dynamics(-1)

    def _set_link_dynamics(self, link: int) -> None:
        """Apply the crawler's local, direction-dependent ground contact model.

        Bullet treats ``anisotropicFriction`` as a multiplier on
        ``lateralFriction``.  The local x axis is the long axis of every capsule,
        so longitudinal sliding is deliberately cheap while lateral sliding is
        expensive.  That broken symmetry is what lets a yaw travelling wave
        propel the body rather than simply shuffle it in place.
        """
        cfg = self.config
        kwargs: dict[str, Any] = {
            "lateralFriction": cfg.lateral_friction,
            "anisotropicFriction": [cfg.longitudinal_friction / cfg.lateral_friction, 1.0, 1.0],
            "physicsClientId": self._client,
        }
        if link >= 0:
            kwargs["jointLowerLimit"] = -cfg.joint_limit
            kwargs["jointUpperLimit"] = cfg.joint_limit
        self._p.changeDynamics(self._body, link, **kwargs)

    # ------------------------------------------------------------------ #
    # Gymnasium-style API
    # ------------------------------------------------------------------ #
    @property
    def action_space_n(self) -> int:
        return N_ACTIONS

    @property
    def n_actions(self) -> int:
        """Alias of ``action_space_n`` so any ORIGIN env presents one action-space name."""
        return N_ACTIONS

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        if seed is not None:
            self.config.seed = int(seed)
        self._rng = np.random.default_rng(self.config.seed)
        self._build_world()
        if self.config.init_jitter > 0:
            for j in range(self._n_joints):
                angle = float(self._rng.uniform(-self.config.init_jitter, self.config.init_jitter))
                self._p.resetJointState(self._body, j, angle, 0.0, physicsClientId=self._client)
        self._steps = 0
        self._distance_travelled = 0.0
        self._upright_steps = 0
        self._energy = 0.0
        self._banked = 0.0
        self._success = False
        self._prev_dist = self._target_distance()
        return self._observation(), self._info()

    def step(self, action: int):
        cfg = self.config
        if not 0 <= int(action) < N_ACTIONS:
            raise ValueError(f"invalid action {action!r}; expected 0..{N_ACTIONS - 1}")
        action = int(action)

        targets = self._motor_targets(action)
        max_force = cfg.joint_max_torque * cfg.torque_gain
        for _ in range(cfg.n_substeps):
            self._p.setJointMotorControlArray(
                self._body,
                list(range(self._n_joints)),
                self._p.POSITION_CONTROL,
                targetPositions=targets,
                targetVelocities=[0.0] * self._n_joints,
                forces=[max_force] * self._n_joints,
                positionGains=[cfg.motor_position_gain] * self._n_joints,
                velocityGains=[cfg.motor_velocity_gain] * self._n_joints,
                physicsClientId=self._client,
            )
            self._p.stepSimulation(physicsClientId=self._client)

        self._steps += 1
        base_pos, base_orn = self._base_pose()
        dist = self._target_distance()
        progress = self._prev_dist - dist
        self._distance_travelled += max(0.0, progress)
        # Applied motor torque is reported by Bullet after the final substep.
        # It is a better energy proxy than the available torque cap: a stalled or
        # unloaded motor should not be charged as though it delivered full work.
        applied = self._applied_joint_torques()
        self._energy += float(np.sum(np.abs(applied))) * cfg.control_dt
        upright = self._is_upright()
        if upright:
            self._upright_steps += 1

        reward = progress * cfg.progress_scale
        if upright:
            reward += cfg.upright_bonus
        reward -= cfg.energy_penalty * float(np.sum(np.abs(applied)))

        terminated = False
        self._success = False
        if not upright:
            # Failure state has zero potential: cancel the shaping banked so far,
            # so the return of any fallen episode is exactly -fall_penalty.
            reward = -cfg.fall_penalty - self._banked
            terminated = True
        else:
            self._banked += reward
            if dist <= cfg.target_tolerance:
                # Success requires arriving *upright*: the task is "reach the
                # target without falling", not "reach the target region".
                reward += cfg.target_reward
                self._success = True
                terminated = True
        truncated = self._steps >= cfg.max_steps
        self._prev_dist = dist
        return self._observation(), float(reward), bool(terminated), bool(truncated), self._info()

    def close(self) -> None:
        with contextlib.suppress(Exception):  # pragma: no cover
            self._p.disconnect(physicsClientId=self._client)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _is_upright(self) -> bool:
        """A planar crawler is upright unless it has tipped over or dropped.

        The tilt test reads the base orientation's **up axis** rather than Euler
        pitch: Euler pitch wraps at +/-90 degrees, so a body lying upside down
        reads as "upright" (a tipped test body at 2.4 rad reported pitch ~0.75).
        Height alone is meaningless (the base rests at ``link_radius``), so this
        combines the wrap-immune tilt with a sanity check that the body has not
        fallen through the ground.
        """
        pos, orn = self._base_pose()
        rot = self._p.getMatrixFromQuaternion(orn)
        up_z = float(rot[8])  # world-z component of the base's local up axis
        if up_z < float(np.cos(1.15)):
            return False
        return pos[2] >= self.config.link_radius * 0.5

    def _motor_targets(self, action: int) -> list[float]:
        """Map a discrete primitive to bounded joint-angle targets.

        The old open-loop torque pulses did not define a repeatable gait: a joint
        could hit a stop, keep receiving torque, and leave all contact forces
        symmetric.  Position targets are still force-limited by
        ``joint_max_torque`` in :meth:`step`, but create an actual travelling
        curvature wave that can be compared across morphologies.
        """
        cfg = self.config
        t = self._steps
        n = self._n_joints
        amplitude = cfg.gait_amplitude * cfg.joint_limit
        if action == 0:      # flex
            target = np.full(n, -amplitude)
        elif action == 1:    # extend
            target = np.full(n, amplitude)
        elif action == 2:    # travelling wave, phase moving tail -> head
            target = amplitude * np.sin(2.0 * np.pi * (np.arange(n) / max(1, n)) - 2.0 * np.pi * t * 0.08)
        elif action == 3:    # travelling wave in the opposite direction
            target = amplitude * np.sin(2.0 * np.pi * (np.arange(n) / max(1, n)) + 2.0 * np.pi * t * 0.08)
        else:                # brake / hold the neutral, straight posture
            target = np.zeros(n)
        return [float(v) for v in target]

    def _applied_joint_torques(self) -> np.ndarray:
        states = self._p.getJointStates(self._body, list(range(self._n_joints)), physicsClientId=self._client)
        return np.asarray([float(s[3]) for s in states], dtype=float)

    def _base_pose(self) -> tuple[list[float], list[float]]:
        pos, orn = self._p.getBasePositionAndOrientation(self._body, physicsClientId=self._client)
        return list(pos), list(orn)

    def _target_distance(self) -> float:
        pos, _ = self._base_pose()
        return float(np.linalg.norm(np.asarray(pos) - self._target))

    def _joint_state(self) -> tuple[np.ndarray, np.ndarray]:
        states = self._p.getJointStates(self._body, list(range(self._n_joints)), physicsClientId=self._client)
        angles = np.array([s[0] for s in states], dtype=float)
        vels = np.array([s[1] for s in states], dtype=float)
        return angles, vels

    def _pitch(self) -> tuple[float, float]:
        _, orn = self._base_pose()
        # quaternion -> roll/pitch; we care about pitch (rotation about y)
        r, pitch, _yaw = self._p.getEulerFromQuaternion(orn)
        ang_vel = self._p.getBaseVelocity(self._body, physicsClientId=self._client)[1]
        return float(pitch), float(ang_vel[1])

    def _heading_error(self) -> tuple[float, float]:
        """Return target bearing in the body's frame and yaw velocity.

        Ground crawlers steer in the x-y plane, so the old vertical target angle
        (x-z) carried almost no useful control information.  This preserves the
        seven-value interface while exposing the physically relevant error.
        """
        pos, orn = self._base_pose()
        rot = self._p.getMatrixFromQuaternion(orn)
        # First column of Bullet's rotation matrix is the body's local +x axis
        # expressed in world coordinates.
        heading = float(np.arctan2(rot[3], rot[0]))
        d = self._target - np.asarray(pos)
        target_heading = float(np.arctan2(d[1], d[0]))
        error = float(np.arctan2(np.sin(target_heading - heading), np.cos(target_heading - heading)))
        angular_velocity = self._p.getBaseVelocity(self._body, physicsClientId=self._client)[1]
        return error, float(angular_velocity[2])

    def _observation(self) -> np.ndarray:
        """Fixed 7-D observation, independent of the number of joints (see module docstring)."""
        cfg = self.config
        pos, _ = self._base_pose()
        heading_error, yaw_vel = self._heading_error()
        angles, vels = self._joint_state()
        d = self._target - np.asarray(pos)
        dist = float(np.linalg.norm(d))
        scale = max(1e-6, cfg.target_distance)
        return np.array(
            [
                float(np.sin(heading_error)),
                float(np.clip(yaw_vel, -10.0, 10.0) / 10.0),
                float(np.mean(angles) / cfg.joint_limit),
                float(np.clip(np.mean(vels), -10.0, 10.0) / 10.0),
                float(np.clip(pos[2], 0.0, 2.0) / 2.0),
                float(np.cos(heading_error)),
                float(np.clip(dist / scale, 0.0, 2.0)),
            ],
            dtype=np.float32,
        )

    @property
    def observation_size(self) -> int:
        return 7

    def _descriptor(self) -> np.ndarray:
        cfg = self.config
        steps = max(1, self._steps)
        return np.array(
            [
                self._distance_travelled,
                self._upright_steps / steps,
                self._energy,
                self._distance_travelled / (steps * cfg.control_dt),
                steps / cfg.max_steps,
            ],
            dtype=np.float32,
        )

    def _info(self) -> dict[str, Any]:
        pos, _ = self._base_pose()
        pitch, _ = self._pitch()
        heading_error, _ = self._heading_error()
        return {
            "position": [float(v) for v in pos],
            "agent": [float(pos[0]), float(pos[2])],
            "steps": int(self._steps),
            "distance_to_target": float(self._target_distance()),
            "distance_travelled": float(self._distance_travelled),
            "pitch": float(pitch),
            "heading_error": float(heading_error),
            "upright": bool(self._is_upright()),
            "success": bool(self._success),
            "energy": float(self._energy),
            "descriptor": self._descriptor().tolist(),
            "n_joints": int(self._n_joints),
            "joint_axis": self.config.joint_axis,
            "config_hash": self.config.config_hash(),
            "seed": int(self.config.seed),
        }

    # ------------------------------------------------------------------ #
    # State serialization (portable: no engine handles)
    # ------------------------------------------------------------------ #
    def get_state(self) -> dict[str, Any]:
        base_pos, base_orn = self._base_pose()
        lin_vel, ang_vel = self._p.getBaseVelocity(self._body, physicsClientId=self._client)
        states = self._p.getJointStates(self._body, list(range(self._n_joints)), physicsClientId=self._client)
        return {
            "version": 1,
            "config": self.config.to_dict(),
            "base_position": [float(v) for v in base_pos],
            "base_orientation": [float(v) for v in base_orn],
            "base_linear_velocity": [float(v) for v in lin_vel],
            "base_angular_velocity": [float(v) for v in ang_vel],
            "joint_positions": [float(s[0]) for s in states],
            "joint_velocities": [float(s[1]) for s in states],
            "steps": int(self._steps),
            "prev_dist": float(self._prev_dist),
            "distance_travelled": float(self._distance_travelled),
            "upright_steps": int(self._upright_steps),
            "energy": float(self._energy),
            "banked_reward": float(self._banked),
            "success": bool(self._success),
        }

    def set_state(self, state: dict[str, Any]) -> None:
        if state.get("version") != 1:
            raise ValueError("unsupported embodied state version")
        incoming_config = EmbodiedConfig.from_dict(state["config"])
        # Rebuild the complete world when any physical property differs.  The old
        # code rebuilt only when link count changed, leaving a same-sized restored
        # body with the *previous* collision shape, contact friction and gravity.
        # That made cross-morphology state restores physically inconsistent.
        rebuild_world = incoming_config.config_hash() != self.config.config_hash()
        self.config = incoming_config
        self._n_joints = int(self.config.n_links)
        if rebuild_world:
            self._build_world()
        if len(state["joint_positions"]) != self._n_joints or len(state["joint_velocities"]) != self._n_joints:
            raise ValueError("state joint count does not match the body")
        self._rest_z = self.config.link_radius + 0.01
        self._target = np.array([self.config.target_distance, 0.0, self._rest_z], dtype=float)
        self._p.resetBasePositionAndOrientation(
            self._body, state["base_position"], state["base_orientation"], physicsClientId=self._client
        )
        # Base velocity must be restored too: omitting it made a replay diverge
        # immediately even though pose and joints matched.
        self._p.resetBaseVelocity(
            self._body,
            state.get("base_linear_velocity", [0.0, 0.0, 0.0]),
            state.get("base_angular_velocity", [0.0, 0.0, 0.0]),
            physicsClientId=self._client,
        )
        for j, (q, v) in enumerate(zip(state["joint_positions"], state["joint_velocities"], strict=True)):
            self._p.resetJointState(self._body, j, q, v, physicsClientId=self._client)
        self._steps = int(state["steps"])
        self._prev_dist = float(state["prev_dist"])
        self._distance_travelled = float(state["distance_travelled"])
        self._upright_steps = int(state["upright_steps"])
        self._energy = float(state["energy"])
        # Additive fields: states recorded before this schema carry neither, and
        # defaulting keeps old replay traces loadable.
        self._banked = float(state.get("banked_reward", 0.0))
        self._success = bool(state.get("success", False))


# ---------------------------------------------------------------------- #
# Morphology variants for transfer experiments (Milestone 4)
# ---------------------------------------------------------------------- #
def embodied_morphology_variants(base: EmbodiedConfig) -> dict[str, EmbodiedConfig]:
    """Genuinely distinct body plans: link count, length, mass, torque and friction.

    Each changes the body the controller must drive while the observation (7-D) and
    action set (5 motor primitives) stay identical.
    """
    variants: dict[str, EmbodiedConfig] = {}
    for name, mut in {
        "body_centipede": {"n_links": 14, "link_length": 0.10, "link_mass": 0.12, "joint_max_torque": 1.4},
        "body_short_stiff": {"n_links": 5, "link_length": 0.22, "link_mass": 0.45, "joint_max_torque": 5.0},
        "body_heavy_slow": {"n_links": 8, "link_length": 0.16, "link_mass": 0.8, "joint_max_torque": 3.0,
                            "lateral_friction": 0.65, "longitudinal_friction": 0.10},
        "body_slippery": {"n_links": 8, "link_length": 0.16, "link_mass": 0.25, "joint_max_torque": 2.5,
                          "lateral_friction": 0.35, "longitudinal_friction": 0.06},
    }.items():
        d = base.to_dict()
        d.update(mut)
        variants[name] = EmbodiedConfig.from_dict(d)
    return variants


def embodied_perturbation_variants(base: EmbodiedConfig) -> dict[str, EmbodiedConfig]:
    """Environmental perturbations for the embodied task."""
    out: dict[str, EmbodiedConfig] = {}
    for name, mut in {
        "far_target": {"target_distance": 5.0},
        "heavy_gravity": {"gravity": -16.0},
        "low_gravity": {"gravity": -2.0},
        "low_grip": {"lateral_friction": 0.35, "longitudinal_friction": 0.06},
        "short_episode": {"episode_seconds": 4.0},
    }.items():
        d = base.to_dict()
        d.update(mut)
        out[name] = EmbodiedConfig.from_dict(d)
    return out
