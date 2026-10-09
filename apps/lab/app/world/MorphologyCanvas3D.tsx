"use client";

import { useEffect, useRef, useState } from "react";
import { sfx } from "@/lib/sound";

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

export default function MorphologyCanvas3D({ body }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [gait, setGait] = useState<"wave_a" | "wave_b" | "flex" | "extend" | "neutral">("wave_a");
  const [speed, setSpeed] = useState(1.0);
  const [amplitude, setAmplitude] = useState(body.gait_amplitude || 0.8);
  const [azimuth, setAzimuth] = useState(35); // camera rotation degrees
  const [elevation, setElevation] = useState(25); // camera pitch degrees
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
    setAzimuth(35);
    setElevation(25);
  };

  const currentTheme = THEMES[theme];

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
      ctx.strokeStyle = "rgba(27, 36, 49, 0.7)";
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
      ctx.strokeStyle = "rgba(0, 240, 255, 0.4)";
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(ox, oy);
      ctx.lineTo(tx, ty);
      ctx.stroke();
      ctx.setLineDash([]);

      // Compute forward kinematics of the crawler body
      const segLen = body.segments[0]?.length || 0.16;
      const segRadius = body.segments[0]?.radius || 0.035;
      const maxJointAngle = body.joint_limit * amplitude;

      // Joint angles from selected gait
      const jointAngles: number[] = [];
      const currentLoads: number[] = [];
      const nJoints = body.joints.length;
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
        // Load is proportional to displacement and acceleration
        currentLoads.push(Math.abs(angle) / Math.max(0.01, maxJointAngle));
      }

      // Throttled update of joint loads for HUD
      loadSampleCounter++;
      if (loadSampleCounter % 4 === 0) {
        setJointLoads(currentLoads);
      }

      // Calculate 3D segment positions and orientations
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

        // Directional tread lines
        ctx.strokeStyle = currentTheme.tread;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }

      // Draw revolute joint pins
      for (let i = 0; i < centered.length; i++) {
        const p = centered[i];
        const [jx, jy] = project(p.x, p.y, p.z);
        ctx.fillStyle = i === 0 ? currentTheme.pin : currentTheme.pin;
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
  }, [body, isPlaying, gait, speed, amplitude, azimuth, elevation, currentTheme]);

  const freqHz = (0.8 * speed).toFixed(2);
  const estimatedVelocity = (0.8 * speed * body.longitudinal_friction * amplitude * 1.4).toFixed(2);
  const metabolicCost = (speed * amplitude * body.joint_max_torque * 0.75).toFixed(1);

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
        <div className="row" style={{ gap: 8 }}>
          <button
            className={isPlaying ? "primary" : ""}
            onClick={() => {
              sfx.toggle();
              setIsPlaying((p) => !p);
            }}
            style={{ minWidth: 78 }}
          >
            {isPlaying ? "⏸ Pause" : "▶ Play"}
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
        </div>

        {/* Theme Picker */}
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

        {/* Sliders */}
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
              style={{ width: 68 }}
            />
            <span style={{ fontFamily: "monospace", width: 34 }}>{speed.toFixed(1)}×</span>
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
      </div>

      {/* 3D Viewport with Holodeck HUD */}
      <div
        style={{
          position: "relative",
          width: "100%",
          height: 320,
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
          height={320}
          style={{ width: "100%", height: "100%", display: "block" }}
        />

        {/* Cybernetic Holodeck HUD */}
        <div className="holodeck-hud">
          <div className="holodeck-hud-title">
            <span>Holodeck Telemetry</span>
            <span className="pulse-dot" style={{ width: 6, height: 6 }} />
          </div>
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

          {/* Joint stress mini heatmap */}
          <div style={{ marginTop: 8 }}>
            <span style={{ fontSize: 9, textTransform: "uppercase", letterSpacing: 0.5 }}>
              Joint Load Heatmap
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
                  title={`Joint ${idx}: ${(load * 100).toFixed(0)}% torque load`}
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
          <span>↔ Anisotropic Traction Active</span>
        </div>
      </div>
    </div>
  );
}

