"use client";

import { useEffect, useRef, useState } from "react";

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
}

export default function MorphologyCanvas3D({ body }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [gait, setGait] = useState<"wave_a" | "wave_b" | "flex" | "extend" | "neutral">("wave_a");
  const [speed, setSpeed] = useState(1.0);
  const [amplitude, setAmplitude] = useState(body.gait_amplitude || 0.8);
  const [azimuth, setAzimuth] = useState(35); // camera rotation degrees
  const [elevation, setElevation] = useState(25); // camera pitch degrees

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

  useEffect(() => {
    let animId: number;
    let lastStamp = performance.now();

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const render = (now: number) => {
      const dt = Math.min((now - lastStamp) / 1000, 0.1);
      lastStamp = now;

      if (isPlaying) {
        animTimeRef.current += dt * speed;
      }

      const t = animTimeRef.current;
      const width = canvas.width;
      const height = canvas.height;
      ctx.clearRect(0, 0, width, height);

      // Camera transforms
      const radAz = (azimuth * Math.PI) / 180;
      const radEl = (elevation * Math.PI) / 180;

      // 3D to 2D isometric/perspective projection
      const project = (x: number, y: number, z: number): [number, number, number] => {
        // Rotate around Z (azimuth)
        const rx = x * Math.cos(radAz) - y * Math.sin(radAz);
        const ry = x * Math.sin(radAz) + y * Math.cos(radAz);

        // Rotate around X (elevation)
        const py = ry * Math.cos(radEl) - z * Math.sin(radEl);
        const pz = ry * Math.sin(radEl) + z * Math.cos(radEl);

        // Perspective scale
        const cameraDist = 3.5;
        const factor = 260 / (cameraDist + py);
        const screenX = width / 2 + rx * factor;
        const screenY = height / 2 - (pz + 0.1) * factor;
        return [screenX, screenY, py];
      };

      // Draw perspective ground grid
      ctx.strokeStyle = "#1b2431";
      ctx.lineWidth = 1;
      const gridSize = 1.6;
      const gridStep = 0.2;
      for (let gx = -gridSize; gx <= gridSize; gx += gridStep) {
        const [x1, y1] = project(gx, -gridSize, 0);
        const [x2, y2] = project(gx, gridSize, 0);
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
      for (let gy = -gridSize; gy <= gridSize; gy += gridStep) {
        const [x1, y1] = project(-gridSize, gy, 0);
        const [x2, y2] = project(gridSize, gy, 0);
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      // Origin target indicator (+x axis)
      const [ox, oy] = project(0, 0, 0);
      const [tx, ty] = project(1.2, 0, 0);
      ctx.strokeStyle = "rgba(79, 156, 249, 0.4)";
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(ox, oy);
      ctx.lineTo(tx, ty);
      ctx.stroke();
      ctx.setLineDash([]);

      // Compute forward kinematics of the crawler body
      const nSegments = body.segments.length;
      const segLen = body.segments[0]?.length || 0.16;
      const segRadius = body.segments[0]?.radius || 0.035;
      const maxJointAngle = body.joint_limit * amplitude;

      // Joint angles from selected gait
      const jointAngles: number[] = [];
      const nJoints = body.joints.length;
      for (let j = 0; j < nJoints; j++) {
        let angle = 0;
        const phase = (2 * Math.PI * j) / Math.max(1, nJoints);
        if (gait === "wave_a") {
          // Propulsion traveling wave
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
      }

      // Calculate 3D segment positions and orientations
      // Base segment 0 centered near origin
      const nodes: { x: number; y: number; z: number; heading: number }[] = [];
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

      // Center the body around origin for visualization
      const avgX = nodes.reduce((acc, p) => acc + p.x, 0) / nodes.length;
      const avgY = nodes.reduce((acc, p) => acc + p.y, 0) / nodes.length;
      const centered = nodes.map((p) => ({
        ...p,
        x: p.x - avgX,
        y: p.y - avgY,
      }));

      // Draw ground shadows first
      for (let i = 0; i < centered.length - 1; i++) {
        const p1 = centered[i];
        const p2 = centered[i + 1];
        const [s1x, s1y] = project(p1.x, p1.y, 0.005);
        const [s2x, s2y] = project(p2.x, p2.y, 0.005);

        ctx.strokeStyle = "rgba(10, 15, 22, 0.75)";
        ctx.lineWidth = segRadius * 480;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(s1x, s1y);
        ctx.lineTo(s2x, s2y);
        ctx.stroke();
      }

      // Sort segments by depth (Z-buffer order)
      const renderSegments = [];
      for (let i = 0; i < centered.length - 1; i++) {
        const p1 = centered[i];
        const p2 = centered[i + 1];
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

        // Cylinder body
        const grad = ctx.createLinearGradient(x1, y1 - 10, x1, y1 + 10);
        if (i === 0) {
          // Head link: vibrant cyan/blue
          grad.addColorStop(0, "#60a5fa");
          grad.addColorStop(0.5, "#2563eb");
          grad.addColorStop(1, "#1d4ed8");
        } else {
          // Body links: metallic slate blue
          grad.addColorStop(0, "#475569");
          grad.addColorStop(0.5, "#334155");
          grad.addColorStop(1, "#1e293b");
        }

        ctx.strokeStyle = grad;
        ctx.lineWidth = segRadius * 440;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();

        // Directional tread lines (representing anisotropic friction scales)
        ctx.strokeStyle = i === 0 ? "rgba(255, 255, 255, 0.4)" : "rgba(255, 215, 0, 0.35)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      // Draw revolute joint pins (brass/gold)
      for (let i = 0; i < centered.length; i++) {
        const p = centered[i];
        const [jx, jy] = project(p.x, p.y, p.z);
        ctx.fillStyle = i === 0 ? "#38bdf8" : "#fbbf24";
        ctx.strokeStyle = "#78350f";
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
  }, [body, isPlaying, gait, speed, amplitude, azimuth, elevation]);

  return (
    <div style={{ position: "relative", width: "100%" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <div className="row" style={{ gap: 8 }}>
          <button
            className={isPlaying ? "primary" : ""}
            onClick={() => setIsPlaying((p) => !p)}
            style={{ minWidth: 70 }}
          >
            {isPlaying ? "⏸ Pause" : "▶ Play"}
          </button>
          <select value={gait} onChange={(e) => setGait(e.target.value as typeof gait)}>
            <option value="wave_a">Gait: Wave A (Propulsion Tail→Head)</option>
            <option value="wave_b">Gait: Wave B (Reverse Wave)</option>
            <option value="flex">Gait: Max Flexion</option>
            <option value="extend">Gait: Max Extension</option>
            <option value="neutral">Gait: Neutral Rest</option>
          </select>
        </div>

        <div className="row" style={{ gap: 12, fontSize: 12 }}>
          <label className="row" style={{ gap: 4 }}>
            <span>Speed</span>
            <input
              type="range"
              min="0.2"
              max="2.5"
              step="0.1"
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
              style={{ width: 70 }}
            />
            <span>{speed.toFixed(1)}×</span>
          </label>
          <label className="row" style={{ gap: 4 }}>
            <span>Amplitude</span>
            <input
              type="range"
              min="0.2"
              max="1.5"
              step="0.1"
              value={amplitude}
              onChange={(e) => setAmplitude(Number(e.target.value))}
              style={{ width: 70 }}
            />
            <span>{amplitude.toFixed(1)}×</span>
          </label>
        </div>
      </div>

      <div
        style={{
          position: "relative",
          width: "100%",
          height: 280,
          background: "#080d14",
          border: "1px solid var(--border)",
          borderRadius: 8,
          overflow: "hidden",
          cursor: "grab",
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <canvas
          ref={canvasRef}
          width={820}
          height={280}
          style={{ width: "100%", height: "100%", display: "block" }}
        />
        <div
          style={{
            position: "absolute",
            bottom: 8,
            left: 12,
            fontSize: 11,
            color: "var(--muted)",
            pointerEvents: "none",
            display: "flex",
            gap: 12,
          }}
        >
          <span>🖱 Drag to orbit camera</span>
          <span>🔵 Cyan Head (+x direction)</span>
          <span>🟡 Anisotropic traction treads</span>
        </div>
      </div>
    </div>
  );
}
