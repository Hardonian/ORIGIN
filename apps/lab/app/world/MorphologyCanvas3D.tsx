"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { sfx } from "@/lib/sound";
import { RecordedTrajectory } from "@/lib/api";

interface BodyPlan {
  morphology: string;
  segments: { index: number; center_x: number; length: number; radius: number }[];
  joints: { index: number; x: number; axis: string }[];
  joint_axis: string;
  joint_limit: number;
  joint_max_torque: number;
  gait_amplitude: number;
  motor_position_gain: number;
  motor_velocity_gain: number;
  lateral_friction: number;
  longitudinal_friction: number;
}

interface Props {
  body: BodyPlan;
  trajectory?: RecordedTrajectory | null;
  playbackStep?: number;
  isReplayMode?: boolean;
}

type ThemeKey = "cyberpunk" | "abyssal" | "stealth" | "solar";

const THEMES: Record<
  ThemeKey,
  {
    name: string;
    head: [string, string, string];
    body: [string, string, string];
    tread: string;
    pin: string;
    pinBorder: string;
  }
> = {
  cyberpunk: {
    name: "Cyberpunk Neon",
    head: ["#00f0ff", "#3b82f6", "#1d4ed8"],
    body: ["#a855f7", "#7c3aed", "#4c1d95"],
    tread: "rgba(0, 240, 255, 0.45)",
    pin: "#00f0ff",
    pinBorder: "#0e7490",
  },
  abyssal: {
    name: "Bioluminescent Abyssal",
    head: ["#34d399", "#10b981", "#047857"],
    body: ["#2dd4bf", "#0d9488", "#115e59"],
    tread: "rgba(52, 211, 153, 0.45)",
    pin: "#34d399",
    pinBorder: "#065f46",
  },
  stealth: {
    name: "Obsidian Stealth",
    head: ["#94a3b8", "#64748b", "#334155"],
    body: ["#475569", "#334155", "#1e293b"],
    tread: "rgba(245, 158, 11, 0.45)",
    pin: "#fbbf24",
    pinBorder: "#78350f",
  },
  solar: {
    name: "Solar Flare",
    head: ["#f87171", "#ef4444", "#b91c1c"],
    body: ["#fb923c", "#f97316", "#c2410c"],
    tread: "rgba(251, 191, 36, 0.45)",
    pin: "#facc15",
    pinBorder: "#854d0e",
  },
};

export default function MorphologyCanvas3D({
  body,
  trajectory = null,
  playbackStep = 0,
  isReplayMode = false,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isPlayingProcedural, setIsPlayingProcedural] = useState(true);
  const [gait, setGait] = useState<"wave_a" | "wave_b" | "flex" | "extend" | "neutral">("wave_a");
  const [proceduralSpeed, setProceduralSpeed] = useState(1.0);
  const [amplitude, setAmplitude] = useState(body.gait_amplitude || 0.8);
  const [azimuth, setAzimuth] = useState(38); // camera rotation degrees
  const [elevation, setElevation] = useState(24); // camera pitch degrees
  const [cameraFollow, setCameraFollow] = useState(true);
  const [theme, setTheme] = useState<ThemeKey>("cyberpunk");
  const [jointLoads, setJointLoads] = useState<number[]>([]);

  const isDraggingRef = useRef(false);
  const lastMouseRef = useRef({ x: 0, y: 0 });
  const animTimeRef = useRef(0);

  // Mouse drag for 3D orbit
  const handleMouseDown = (e: React.MouseEvent) => {
    isDraggingRef.current = true;
    lastMouseRef.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDraggingRef.current) return;
    const dx = e.clientX - lastMouseRef.current.x;
    const dy = e.clientY - lastMouseRef.current.y;
    lastMouseRef.current = { x: e.clientX, y: e.clientY };

    setAzimuth((prev) => (prev + dx * 0.5) % 360);
    setElevation((prev) => Math.max(5, Math.min(85, prev - dy * 0.5)));
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  const handleThemeChange = (t: ThemeKey) => {
    sfx.blip();
    setTheme(t);
  };

  const handleResetCamera = () => {
    sfx.toggle();
    setAzimuth(38);
    setElevation(24);
  };

  const currentTheme = THEMES[theme];

  // Resolve active frame when in replay mode
  const activeFrame = useMemo(() => {
    if (!isReplayMode || !trajectory || !trajectory.trajectory.length) return null;
    const idx = Math.max(0, Math.min(playbackStep, trajectory.trajectory.length - 1));
    return trajectory.trajectory[idx];
  }, [isReplayMode, trajectory, playbackStep]);

  useEffect(() => {
    let animId: number;
    let lastStamp = performance.now();
    let loadSampleCounter = 0;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const render = (now: number) => {
      const dt = Math.min((now - lastStamp) / 1000, 0.1);
      lastStamp = now;

      if (!isReplayMode && isPlayingProcedural) {
        animTimeRef.current += dt * proceduralSpeed;
      }

      const t = animTimeRef.current;
      const width = canvas.width;
      const height = canvas.height;
      ctx.clearRect(0, 0, width, height);

      // Camera transforms
      const radAz = (azimuth * Math.PI) / 180;
      const radEl = (elevation * Math.PI) / 180;

      // Camera focus anchor
      let camFocusX = 0;
      let camFocusY = 0;
      let camFocusZ = 0;

      if (isReplayMode && activeFrame) {
        if (cameraFollow) {
          camFocusX = activeFrame.base_pos[0];
          camFocusY = activeFrame.base_pos[1];
          camFocusZ = activeFrame.base_pos[2] * 0.5;
        } else {
          camFocusX = 1.5; // midpoint of 3.0 m track
          camFocusY = 0;
          camFocusZ = 0;
        }
      }

      // 3D to 2D isometric/perspective projection centered on camFocus
      const project = (x: number, y: number, z: number): [number, number, number] => {
        const dx = x - camFocusX;
        const dy = y - camFocusY;
        const dz = z - camFocusZ;

        // Rotate around Z (azimuth)
        const rx = dx * Math.cos(radAz) - dy * Math.sin(radAz);
        const ry = dx * Math.sin(radAz) + dy * Math.cos(radAz);

        // Rotate around X (elevation)
        const py = ry * Math.cos(radEl) - dz * Math.sin(radEl);
        const pz = ry * Math.sin(radEl) + dz * Math.cos(radEl);

        // Perspective scale
        const cameraDist = isReplayMode && !cameraFollow ? 4.6 : 3.5;
        const factor = 260 / (cameraDist + py);
        const screenX = width / 2 + rx * factor;
        const screenY = height / 2 - (pz + 0.1) * factor;
        return [screenX, screenY, py];
      };

      // Draw perspective ground grid
      ctx.strokeStyle = "rgba(27, 36, 49, 0.7)";
      ctx.lineWidth = 1;
      const gridMinX = isReplayMode ? -0.8 : -1.6;
      const gridMaxX = isReplayMode ? 3.6 : 1.6;
      const gridMinY = -1.2;
      const gridMaxY = 1.2;
      const gridStep = 0.2;

      for (let gx = gridMinX; gx <= gridMaxX; gx += gridStep) {
        const [x1, y1] = project(gx, gridMinY, 0);
        const [x2, y2] = project(gx, gridMaxY, 0);
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
      for (let gy = gridMinY; gy <= gridMaxY; gy += gridStep) {
        const [x1, y1] = project(gridMinX, gy, 0);
        const [x2, y2] = project(gridMaxX, gy, 0);
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      // If in replay mode, draw track features (Start, Meters, Goal Finish Gate, Breadcrumbs)
      if (isReplayMode && trajectory) {
        // Start line at x = 0
        const [sx1, sy1] = project(0, -0.6, 0);
        const [sx2, sy2] = project(0, 0.6, 0);
        ctx.strokeStyle = "rgba(63, 185, 80, 0.75)";
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(sx1, sy1);
        ctx.lineTo(sx2, sy2);
        ctx.stroke();

        // Target Finish Line at x = target_distance
        const targetDist = trajectory.target_distance || 3.0;
        const [gx1, gy1] = project(targetDist, -0.7, 0);
        const [gx2, gy2] = project(targetDist, 0.7, 0);
        ctx.strokeStyle = "rgba(0, 240, 255, 0.9)";
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(gx1, gy1);
        ctx.lineTo(gx2, gy2);
        ctx.stroke();

        // Finish Gate Goal Posts
        const [gp1x, gp1y] = project(targetDist, -0.7, 0.35);
        const [gp2x, gp2y] = project(targetDist, 0.7, 0.35);
        ctx.strokeStyle = "rgba(0, 240, 255, 0.6)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(gx1, gy1);
        ctx.lineTo(gp1x, gp1y);
        ctx.moveTo(gx2, gy2);
        ctx.lineTo(gp2x, gp2y);
        ctx.moveTo(gp1x, gp1y);
        ctx.lineTo(gp2x, gp2y);
        ctx.stroke();

        // Goal beacon pulse
        ctx.fillStyle = "rgba(0, 240, 255, 0.8)";
        ctx.beginPath();
        ctx.arc((gp1x + gp2x) / 2, (gp1y + gp2y) / 2, 4.5, 0, Math.PI * 2);
        ctx.fill();

        // Meter labels on ground
        ctx.font = "10px monospace";
        ctx.fillStyle = "rgba(139, 148, 158, 0.85)";
        for (const distM of [0.0, 1.0, 2.0, 3.0]) {
          const [mx, my] = project(distM, -0.75, 0);
          ctx.fillText(`${distM.toFixed(1)}m`, mx - 12, my + 4);
        }

        // Draw trajectory breadcrumb path
        const currentIdx = Math.max(0, Math.min(playbackStep, trajectory.trajectory.length - 1));
        if (currentIdx > 0) {
          ctx.strokeStyle = "rgba(0, 240, 255, 0.55)";
          ctx.lineWidth = 2;
          ctx.beginPath();
          const firstPt = trajectory.trajectory[0].base_pos;
          const [startX, startY] = project(firstPt[0], firstPt[1], 0.005);
          ctx.moveTo(startX, startY);
          for (let stepI = 1; stepI <= currentIdx; stepI++) {
            const pt = trajectory.trajectory[stepI].base_pos;
            const [px, py] = project(pt[0], pt[1], 0.005);
            ctx.lineTo(px, py);
          }
          ctx.stroke();
        }
      } else {
        // Procedural mode target axis line (+x axis)
        const [ox, oy] = project(0, 0, 0);
        const [tx, ty] = project(1.2, 0, 0);
        ctx.strokeStyle = "rgba(0, 240, 255, 0.4)";
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(ox, oy);
        ctx.lineTo(tx, ty);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Compute forward kinematics of the crawler body
      const segLen = body.segments[0]?.length || 0.16;
      const segRadius = body.segments[0]?.radius || 0.035;
      const maxJointAngle = body.joint_limit * amplitude;
      const nJoints = body.joints.length;

      const nodes: { x: number; y: number; z: number; heading: number }[] = [];
      const currentLoads: number[] = [];

      if (isReplayMode && activeFrame) {
        // EXACT PyBullet recorded kinematics
        const basePos = activeFrame.base_pos;
        // Quaternion [x, y, z, w] -> yaw
        const qz = activeFrame.base_orn[2];
        const qw = activeFrame.base_orn[3];
        const baseYaw = 2 * Math.atan2(qz, qw);

        nodes.push({ x: basePos[0], y: basePos[1], z: basePos[2], heading: baseYaw });

        let curX = basePos[0];
        let curY = basePos[1];
        let curHeading = baseYaw;
        const curZ = basePos[2];

        for (let i = 0; i < nJoints; i++) {
          const jointAngle = activeFrame.joint_angles[i] ?? 0;
          curHeading += jointAngle;
          curX += segLen * Math.cos(curHeading);
          curY += segLen * Math.sin(curHeading);
          nodes.push({ x: curX, y: curY, z: curZ, heading: curHeading });

          const load = Math.min(1.0, Math.abs(jointAngle) / Math.max(0.01, body.joint_limit));
          currentLoads.push(load);
        }
      } else {
        // Procedural synthetic kinematic wave
        const jointAngles: number[] = [];
        for (let j = 0; j < nJoints; j++) {
          let angle = 0;
          const phase = (2 * Math.PI * j) / Math.max(1, nJoints);
          if (gait === "wave_a") {
            angle = maxJointAngle * Math.sin(phase - 2 * Math.PI * t * 0.8);
          } else if (gait === "wave_b") {
            angle = maxJointAngle * Math.sin(phase + 2 * Math.PI * t * 0.8);
          } else if (gait === "flex") {
            angle = -maxJointAngle;
          } else if (gait === "extend") {
            angle = maxJointAngle;
          } else {
            angle = 0;
          }
          jointAngles.push(angle);
          currentLoads.push(Math.abs(angle) / Math.max(0.01, maxJointAngle));
        }

        let curX = 0;
        let curY = 0;
        let curHeading = 0;
        nodes.push({ x: curX, y: curY, z: segRadius, heading: curHeading });
        for (let i = 0; i < nJoints; i++) {
          curHeading += jointAngles[i];
          curX += segLen * Math.cos(curHeading);
          curY += segLen * Math.sin(curHeading);
          nodes.push({ x: curX, y: curY, z: segRadius, heading: curHeading });
        }

        // Center procedural body around origin
        const avgX = nodes.reduce((acc, p) => acc + p.x, 0) / nodes.length;
        const avgY = nodes.reduce((acc, p) => acc + p.y, 0) / nodes.length;
        for (let i = 0; i < nodes.length; i++) {
          nodes[i].x -= avgX;
          nodes[i].y -= avgY;
        }
      }

      // Throttled update of joint loads for HUD
      loadSampleCounter++;
      if (loadSampleCounter % 4 === 0) {
        setJointLoads(currentLoads);
      }

      // Draw ground shadows
      for (let i = 0; i < nodes.length - 1; i++) {
        const p1 = nodes[i];
        const p2 = nodes[i + 1];
        const [s1x, s1y] = project(p1.x, p1.y, 0.005);
        const [s2x, s2y] = project(p2.x, p2.y, 0.005);

        ctx.strokeStyle = "rgba(5, 10, 16, 0.85)";
        ctx.lineWidth = segRadius * 480;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(s1x, s1y);
        ctx.lineTo(s2x, s2y);
        ctx.stroke();
      }

      // Sort segments by depth (Z-buffer order)
      const renderSegments = [];
      for (let i = 0; i < nodes.length - 1; i++) {
        const p1 = nodes[i];
        const p2 = nodes[i + 1];
        const midX = (p1.x + p2.x) / 2;
        const midY = (p1.y + p2.y) / 2;
        const midZ = (p1.z + p2.z) / 2;
        const [sx, sy, depth] = project(midX, midY, midZ);
        renderSegments.push({ i, p1, p2, sx, sy, depth });
      }
      renderSegments.sort((a, b) => b.depth - a.depth);

      // Draw articulated capsule links
      for (const seg of renderSegments) {
        const { i, p1, p2 } = seg;
        const [x1, y1] = project(p1.x, p1.y, p1.z);
        const [x2, y2] = project(p2.x, p2.y, p2.z);

        // Cylinder body gradient
        const grad = ctx.createLinearGradient(x1, y1 - 10, x1, y1 + 10);
        const colors = i === 0 ? currentTheme.head : currentTheme.body;
        grad.addColorStop(0, colors[0]);
        grad.addColorStop(0.5, colors[1]);
        grad.addColorStop(1, colors[2]);

        ctx.strokeStyle = grad;
        ctx.lineWidth = segRadius * 440;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();

        // Directional tread lines showing anisotropic traction
        ctx.strokeStyle = currentTheme.tread;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      // Draw revolute joint pins
      for (let i = 0; i < nodes.length; i++) {
        const p = nodes[i];
        const [jx, jy] = project(p.x, p.y, p.z);
        ctx.fillStyle = currentTheme.pin;
        ctx.strokeStyle = currentTheme.pinBorder;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(jx, jy, i === 0 ? 5 : 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animId);
  }, [
    body,
    trajectory,
    playbackStep,
    isReplayMode,
    activeFrame,
    isPlayingProcedural,
    gait,
    proceduralSpeed,
    amplitude,
    azimuth,
    elevation,
    cameraFollow,
    currentTheme,
  ]);

  const freqHz = (0.8 * proceduralSpeed).toFixed(2);
  const estimatedVelocity = (
    0.8 *
    proceduralSpeed *
    body.longitudinal_friction *
    amplitude *
    1.4
  ).toFixed(2);
  const metabolicCost = (proceduralSpeed * amplitude * body.joint_max_torque * 0.75).toFixed(1);

  return (
    <div style={{ position: "relative", width: "100%" }}>
      {/* Top Controls Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 10,
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <div className="row" style={{ gap: 8, alignItems: "center" }}>
          {isReplayMode ? (
            <div className="row" style={{ gap: 6, alignItems: "center" }}>
              <span className="badge done" style={{ fontSize: 11 }}>
                ● PyBullet Rigid-Body Replay
              </span>
              <button
                onClick={() => {
                  sfx.toggle();
                  setCameraFollow((f) => !f);
                }}
                style={{
                  padding: "3px 8px",
                  fontSize: 11,
                  background: cameraFollow ? "var(--panel2)" : "transparent",
                  borderColor: cameraFollow ? "var(--accent)" : "var(--border)",
                  color: cameraFollow ? "var(--accent)" : "var(--muted)",
                }}
              >
                {cameraFollow ? "🎥 Camera: Follow Body" : "🎥 Camera: Track Center"}
              </button>
            </div>
          ) : (
            <>
              <button
                className={isPlayingProcedural ? "primary" : ""}
                onClick={() => {
                  sfx.toggle();
                  setIsPlayingProcedural((p) => !p);
                }}
                style={{ minWidth: 78 }}
              >
                {isPlayingProcedural ? "⏸ Pause" : "▶ Play"}
              </button>
              <select
                value={gait}
                onChange={(e) => {
                  sfx.click();
                  setGait(e.target.value as typeof gait);
                }}
              >
                <option value="wave_a">Gait: Wave A (Propulsion Tail→Head)</option>
                <option value="wave_b">Gait: Wave B (Reverse Wave)</option>
                <option value="flex">Gait: Max Flexion</option>
                <option value="extend">Gait: Max Extension</option>
                <option value="neutral">Gait: Neutral Rest</option>
              </select>
            </>
          )}
        </div>

        {/* Theme Picker & Orbit Reset */}
        <div className="row" style={{ gap: 6, alignItems: "center" }}>
          <span style={{ fontSize: 11, color: "var(--muted)" }}>Theme:</span>
          {(Object.keys(THEMES) as ThemeKey[]).map((tKey) => (
            <button
              key={tKey}
              onClick={() => handleThemeChange(tKey)}
              style={{
                padding: "2px 8px",
                fontSize: 11,
                background: theme === tKey ? "var(--panel2)" : "transparent",
                borderColor: theme === tKey ? "var(--accent)" : "var(--border)",
                color: theme === tKey ? "var(--accent)" : "var(--muted)",
              }}
            >
              {THEMES[tKey].name.split(" ")[0]}
            </button>
          ))}
          <button
            onClick={handleResetCamera}
            title="Reset Camera Angle"
            style={{ padding: "2px 8px", fontSize: 11 }}
          >
            Reset Orbit
          </button>
        </div>

        {/* Sliders (Only shown in schematic/procedural mode) */}
        {!isReplayMode && (
          <div className="row" style={{ gap: 12, fontSize: 12 }}>
            <label className="row" style={{ gap: 4 }}>
              <span>Speed</span>
              <input
                type="range"
                min="0.2"
                max="2.5"
                step="0.1"
                value={proceduralSpeed}
                onChange={(e) => setProceduralSpeed(Number(e.target.value))}
                style={{ width: 68 }}
              />
              <span style={{ fontFamily: "monospace", width: 34 }}>{proceduralSpeed.toFixed(1)}×</span>
            </label>
            <label className="row" style={{ gap: 4 }}>
              <span>Amp</span>
              <input
                type="range"
                min="0.2"
                max="1.5"
                step="0.1"
                value={amplitude}
                onChange={(e) => setAmplitude(Number(e.target.value))}
                style={{ width: 68 }}
              />
              <span style={{ fontFamily: "monospace", width: 34 }}>{amplitude.toFixed(1)}×</span>
            </label>
          </div>
        )}
      </div>

      {/* 3D Viewport with Holodeck HUD */}
      <div
        style={{
          position: "relative",
          width: "100%",
          height: 340,
          background: "radial-gradient(ellipse at 50% 60%, #0d1522 0%, #060a10 100%)",
          border: "1px solid var(--border)",
          borderRadius: 10,
          overflow: "hidden",
          cursor: "grab",
          boxShadow: "inset 0 0 30px rgba(0, 0, 0, 0.6)",
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <canvas
          ref={canvasRef}
          width={840}
          height={340}
          style={{ width: "100%", height: "100%", display: "block" }}
        />

        {/* Cybernetic Holodeck HUD */}
        <div className="holodeck-hud">
          <div className="holodeck-hud-title">
            <span>{isReplayMode ? "Physics Telemetry" : "Kinematics Telemetry"}</span>
            <span
              className="pulse-dot"
              style={{
                width: 6,
                height: 6,
                backgroundColor: isReplayMode ? "var(--ok)" : "var(--accent)",
              }}
            />
          </div>

          {isReplayMode && activeFrame ? (
            <>
              <div className="hud-metric-row">
                <span>Step &amp; Time:</span>
                <span className="hud-metric-val">
                  #{activeFrame.step} · {activeFrame.time_s.toFixed(2)}s
                </span>
              </div>
              <div className="hud-metric-row">
                <span>Displacement:</span>
                <span className="hud-metric-val" style={{ color: "var(--ok)" }}>
                  +{activeFrame.base_pos[0].toFixed(3)} m
                </span>
              </div>
              <div className="hud-metric-row">
                <span>Lateral Drift:</span>
                <span className="hud-metric-val">
                  {activeFrame.base_pos[1] >= 0 ? "+" : ""}
                  {activeFrame.base_pos[1].toFixed(3)} m
                </span>
              </div>
              <div className="hud-metric-row">
                <span>Base Clearance:</span>
                <span className="hud-metric-val">
                  {(activeFrame.base_pos[2] * 100).toFixed(1)} cm
                </span>
              </div>
              <div className="hud-metric-row">
                <span>Action:</span>
                <span className="hud-metric-val" style={{ color: "var(--accent)" }}>
                  {activeFrame.action_name.toUpperCase()} (#{activeFrame.action})
                </span>
              </div>
              <div className="hud-metric-row">
                <span>Target Dist:</span>
                <span className="hud-metric-val">
                  {activeFrame.distance_to_target.toFixed(3)} m
                </span>
              </div>
              <div className="hud-metric-row">
                <span>Reward:</span>
                <span className="hud-metric-val">
                  {activeFrame.cumulative_reward.toFixed(2)}
                </span>
              </div>
              <div className="hud-metric-row">
                <span>Stability:</span>
                <span
                  className="hud-metric-val"
                  style={{ color: activeFrame.upright ? "#3fb950" : "#f85149" }}
                >
                  {activeFrame.upright ? "UPRIGHT" : "TUMBLED"}
                </span>
              </div>
            </>
          ) : (
            <>
              <div className="hud-metric-row">
                <span>Undulation:</span>
                <span className="hud-metric-val">{freqHz} Hz</span>
              </div>
              <div className="hud-metric-row">
                <span>Est. Velocity:</span>
                <span className="hud-metric-val">{estimatedVelocity} m/s</span>
              </div>
              <div className="hud-metric-row">
                <span>Metabolic Burn:</span>
                <span className="hud-metric-val">{metabolicCost} J/s</span>
              </div>
              <div className="hud-metric-row">
                <span>Camera Orbit:</span>
                <span className="hud-metric-val">
                  {Math.round(azimuth)}° / {Math.round(elevation)}°
                </span>
              </div>
            </>
          )}

          {/* Joint stress mini heatmap */}
          <div style={{ marginTop: 8 }}>
            <span style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: 0.5 }}>
              Joint Deflection Stress
            </span>
            <div style={{ display: "flex", gap: 3, marginTop: 3 }}>
              {jointLoads.map((load, idx) => (
                <div
                  key={idx}
                  style={{
                    flex: 1,
                    height: 12,
                    background: `rgba(${Math.round(255 * load)}, ${Math.round(240 * (1 - load))}, 100, 0.75)`,
                    borderRadius: 2,
                    border: "1px solid rgba(255, 255, 255, 0.1)",
                  }}
                  title={`Joint ${idx}: ${(load * 100).toFixed(0)}% limit deflection`}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Bottom helper prompt */}
        <div
          style={{
            position: "absolute",
            bottom: 10,
            left: 14,
            fontSize: 11,
            color: "var(--muted)",
            pointerEvents: "none",
            display: "flex",
            gap: 16,
            background: "rgba(10, 15, 24, 0.75)",
            padding: "4px 10px",
            borderRadius: 6,
            backdropFilter: "blur(6px)",
          }}
        >
          <span>🖱 Drag to orbit camera</span>
          <span style={{ color: currentTheme.pin }}>● {currentTheme.name}</span>
          <span>
            {isReplayMode
              ? `🎯 Target: ${trajectory?.target_distance ?? 3.0}m · PyBullet DIRECT`
              : "↔ Anisotropic Traction Active"}
          </span>
        </div>
      </div>
    </div>
  );
}
