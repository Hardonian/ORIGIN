"use client";

import { useEffect, useMemo, useState } from "react";
import {
  API_BASE,
  apiGet,
  CalibrationEvidence,
  ExperimentSummary,
  RecordedTrajectory,
  RecordedTrajectoryFrame,
  Trial,
} from "@/lib/api";
import { sfx } from "@/lib/sound";
import MorphologyCanvas3D from "./MorphologyCanvas3D";

interface WorldData {
  experiment_id: string;
  trial_id: string;
  seed: number;
  config: Record<string, number | string>;
  grid: number[][];
  trajectory: {
    agent: number[];
    action: number;
    reward: number;
    collected: number;
    collected_a?: number;
    collected_b?: number;
    energy: number;
  }[];
  total_reward: number;
  steps: number;
  terminated: boolean;
  morphology: Record<string, unknown>;
}

interface ExperimentDetail {
  experiment: { config_json: string };
  trials: Trial[];
}

interface MorphologyPlan {
  viewer_kind: "morphology_plan";
  experiment_id: string;
  trial_id: string;
  physics_replay: false;
  has_recorded_trajectory?: boolean;
  trajectory_url?: string | null;
  body: {
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
  };
  organism_morphology: Record<string, unknown> | null;
  calibration: { status: string; acceptance: string; command: string };
}

type EnvironmentKind = "gridworld" | "embodied" | null;
type EmbodiedViewerMode = "physics_replay" | "schematic_3d" | "schematic_2d";

const COLORS: Record<number, string> = {
  0: "#121821",
  1: "#3b4657",
  2: "#3fb950",
  3: "#f85149",
  4: "#f5a623",
  5: "#f5a623",
  9: "#00f0ff",
};

function kindFromDetail(detail: ExperimentDetail): Exclude<EnvironmentKind, null> {
  try {
    const config = JSON.parse(detail.experiment.config_json) as { env_kind?: string };
    return config.env_kind === "embodied" ? "embodied" : "gridworld";
  } catch {
    return "gridworld";
  }
}

export default function WorldPage() {
  const [exps, setExps] = useState<ExperimentSummary[]>([]);
  const [expId, setExpId] = useState("");
  const [trials, setTrials] = useState<Trial[]>([]);
  const [trialId, setTrialId] = useState("");
  const [envKind, setEnvKind] = useState<EnvironmentKind>(null);
  const [resolvedExpId, setResolvedExpId] = useState("");
  const [seed, setSeed] = useState(101);
  const [world, setWorld] = useState<WorldData | null>(null);
  const [plan, setPlan] = useState<MorphologyPlan | null>(null);
  const [evidence, setEvidence] = useState<CalibrationEvidence | null>(null);
  const [trajectory, setTrajectory] = useState<RecordedTrajectory | null>(null);
  const [step, setStep] = useState(0);
  const [isPlayingReplay, setIsPlayingReplay] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [loopReplay, setLoopReplay] = useState<boolean>(true);

  // Embodied trajectory playback state
  const [trajStep, setTrajStep] = useState(0);
  const [isPlayingTraj, setIsPlayingTraj] = useState(false);
  const [trajSpeed, setTrajSpeed] = useState<number>(1);
  const [trajLoop, setTrajLoop] = useState<boolean>(true);
  const [embodiedMode, setEmbodiedMode] = useState<EmbodiedViewerMode>("physics_replay");

  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    apiGet<ExperimentSummary[]>("/api/experiments")
      .then((d) => {
        setExps(d);
        if (d.length) setExpId(d[0].id);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  useEffect(() => {
    if (!expId) return;
    let cancelled = false;
    apiGet<ExperimentDetail>(`/api/experiments/${expId}`)
      .then((d) => {
        if (cancelled) return;
        const kind = kindFromDetail(d);
        const completed = d.trials.filter(
          (t) =>
            t.status === "done" &&
            (kind === "embodied" || !["random", "heuristic"].includes(t.algorithm))
        );
        setResolvedExpId(expId);
        setEnvKind(kind);
        setTrials(completed);
        setTrialId(completed[0]?.id ?? "");
        setErr(null);
      })
      .catch((e) => !cancelled && setErr(String(e)));
    return () => {
      cancelled = true;
    };
  }, [expId]);

  useEffect(() => {
    if (!expId || resolvedExpId !== expId || !trialId || !envKind) return;
    let cancelled = false;

    if (envKind === "embodied") {
      Promise.all([
        apiGet<MorphologyPlan>(`/api/morphology?experiment=${expId}&trial=${trialId}`),
        apiGet<CalibrationEvidence>("/api/calibration"),
        apiGet<RecordedTrajectory>(`/api/trajectory?experiment=${expId}&trial=${trialId}`).catch(() => null),
      ])
        .then(([bodyPlan, calibrationEvidence, recordedTrajectory]) => {
          if (cancelled) return;
          setPlan(bodyPlan);
          setEvidence(calibrationEvidence);
          setTrajectory(recordedTrajectory);
          setTrajStep(0);
          setIsPlayingTraj(false);
          if (recordedTrajectory) {
            setEmbodiedMode("physics_replay");
          } else {
            setEmbodiedMode("schematic_3d");
          }
        })
        .catch((e) => !cancelled && setErr(String(e)));
    } else {
      apiGet<WorldData>(`/api/world?experiment=${expId}&trial=${trialId}&seed=${seed}`)
        .then((data) => {
          if (cancelled) return;
          setWorld(data);
          setStep(0);
          setIsPlayingReplay(false);
        })
        .catch((e) => !cancelled && setErr(String(e)));
    }
    return () => {
      cancelled = true;
    };
  }, [envKind, expId, resolvedExpId, trialId, seed]);

  // GridWorld Trajectory auto-player
  useEffect(() => {
    if (!isPlayingReplay || !world || world.trajectory.length === 0) return;
    const intervalMs = Math.max(50, 260 / playbackSpeed);
    const interval = setInterval(() => {
      setStep((cur) => {
        if (cur >= world.trajectory.length) {
          if (loopReplay) {
            sfx.toggle();
            return 0;
          } else {
            setIsPlayingReplay(false);
            return cur;
          }
        }
        sfx.step();
        return cur + 1;
      });
    }, intervalMs);

    return () => clearInterval(interval);
  }, [isPlayingReplay, playbackSpeed, world, loopReplay]);

  // Embodied Physics Trajectory auto-player (~30 Hz simulation clock)
  useEffect(() => {
    if (!isPlayingTraj || !trajectory || trajectory.trajectory.length === 0) return;
    const intervalMs = Math.max(25, Math.round(100 / trajSpeed));
    const interval = setInterval(() => {
      setTrajStep((cur) => {
        if (cur >= trajectory.trajectory.length - 1) {
          if (trajLoop) {
            sfx.toggle();
            return 0;
          } else {
            setIsPlayingTraj(false);
            return cur;
          }
        }
        sfx.step();
        return cur + 1;
      });
    }, intervalMs);

    return () => clearInterval(interval);
  }, [isPlayingTraj, trajSpeed, trajectory, trajLoop]);

  const detailStale = resolvedExpId !== expId;
  const stale =
    detailStale ||
    (envKind === "embodied"
      ? !plan || plan.trial_id !== trialId || plan.experiment_id !== expId
      : !world || world.trial_id !== trialId || world.experiment_id !== expId || world.seed !== seed);
  const loading = Boolean(expId && trialId && envKind && stale && !err);

  const grid = useMemo(() => {
    if (!world) return null;
    const replay = world.grid.map((row) => row.slice());
    const regen = Boolean(world.config.resource_regen);
    if (!regen) {
      for (let i = 0; i < step && i < world.trajectory.length; i++) {
        const cur = world.trajectory[i];
        const prev = i > 0 ? world.trajectory[i - 1] : null;
        const collectedDiff = prev ? cur.collected - prev.collected : cur.collected;
        if (collectedDiff > 0) {
          replay[cur.agent[0]][cur.agent[1]] = 0;
        }
      }
    }
    if (world.trajectory.length > 0) {
      const pos = step === 0 ? null : world.trajectory[step - 1].agent;
      if (pos) replay[pos[0]][pos[1]] = 9;
    }
    return replay;
  }, [world, step]);

  const currentStepData = useMemo(() => {
    if (!world || world.trajectory.length === 0 || step === 0) {
      return null;
    }
    return world.trajectory[Math.min(step - 1, world.trajectory.length - 1)];
  }, [world, step]);

  const currentTrajFrame: RecordedTrajectoryFrame | null = useMemo(() => {
    if (!trajectory || !trajectory.trajectory.length) return null;
    const idx = Math.max(0, Math.min(trajStep, trajectory.trajectory.length - 1));
    return trajectory.trajectory[idx];
  }, [trajectory, trajStep]);

  const segmentPositions = useMemo(() => {
    const n = plan?.body.segments.length ?? 0;
    const width = Math.max(420, n * 58);
    const spacing = n > 1 ? (width - 80) / (n - 1) : 0;
    return { width, y: 110, at: (i: number) => 40 + i * spacing };
  }, [plan]);

  return (
    <div>
      <h1>World viewer &amp; body plans</h1>
      <p className="sub">
        Grid experiments are replayed from stored organisms. Embodied experiments render their
        persisted body specifications, calibration evidence, and interactive 3D rigid-body
        physical trajectories recorded in PyBullet DIRECT simulation.
      </p>

      <div className="panel">
        <div className="row">
          <label>experiment</label>
          <select value={expId} onChange={(e) => setExpId(e.target.value)}>
            {exps.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name} ({e.id})
              </option>
            ))}
          </select>
          <label>trial</label>
          <select value={trialId} onChange={(e) => setTrialId(e.target.value)}>
            {trials.map((t) => (
              <option key={t.id} value={t.id}>
                {t.algorithm} · seed {t.seed}
              </option>
            ))}
          </select>
          {envKind === "gridworld" ? (
            <>
              <label>world seed</label>
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
                style={{ width: 90 }}
              />
            </>
          ) : envKind === "embodied" ? (
            trajectory ? (
              <span className="badge done">
                ● 3d physics trajectory recorded ({trajectory.steps} steps)
              </span>
            ) : (
              <span className="badge running">physics calibration required</span>
            )
          ) : null}
        </div>
      </div>

      {loading && <p className="muted">loading persisted experiment state…</p>}
      {err && (
        <div className="panel">
          <p className="err">{err}</p>
          <p className="muted">API: {API_BASE}</p>
        </div>
      )}

      {/* GRIDWORLD VIEW */}
      {!stale && grid && world && envKind === "gridworld" && (
        <div className="panel">
          {/* Replay Controls & Scrubber */}
          <div
            className="row"
            style={{
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 12,
              flexWrap: "wrap",
              gap: 10,
            }}
          >
            <div className="row" style={{ gap: 8 }}>
              <button
                className={isPlayingReplay ? "primary" : ""}
                onClick={() => {
                  sfx.toggle();
                  setIsPlayingReplay((p) => !p);
                }}
                style={{ minWidth: 78 }}
              >
                {isPlayingReplay ? "⏸ Pause" : "▶ Replay"}
              </button>
              <button
                onClick={() => {
                  sfx.step();
                  setStep((s) => Math.max(0, s - 1));
                }}
              >
                ◀ Step
              </button>
              <button
                onClick={() => {
                  sfx.step();
                  setStep((s) => Math.min(world.trajectory.length, s + 1));
                }}
              >
                Step ▶
              </button>
              <button
                onClick={() => {
                  sfx.toggle();
                  setStep(0);
                }}
                title="Reset to initial state"
              >
                ↺
              </button>
            </div>

            {/* Speed Multiplier & Loop */}
            <div className="row" style={{ gap: 8, alignItems: "center" }}>
              <span style={{ fontSize: 11, color: "var(--muted)" }}>Speed:</span>
              {[0.5, 1, 2, 5].map((spd) => (
                <button
                  key={spd}
                  onClick={() => {
                    sfx.click();
                    setPlaybackSpeed(spd);
                  }}
                  style={{
                    padding: "2px 8px",
                    fontSize: 11,
                    background: playbackSpeed === spd ? "var(--panel2)" : "transparent",
                    borderColor: playbackSpeed === spd ? "var(--accent)" : "var(--border)",
                    color: playbackSpeed === spd ? "var(--accent)" : "var(--muted)",
                  }}
                >
                  {spd}×
                </button>
              ))}
              <label
                style={{
                  fontSize: 11,
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  cursor: "pointer",
                  color: "var(--muted)",
                  marginLeft: 6,
                }}
              >
                <input
                  type="checkbox"
                  checked={loopReplay}
                  onChange={(e) => setLoopReplay(e.target.checked)}
                />
                Loop
              </label>
            </div>

            {/* Scrubber slider */}
            <div className="row" style={{ gap: 10, alignItems: "center" }}>
              <input
                type="range"
                min={0}
                max={world.trajectory.length}
                value={step}
                onChange={(e) => {
                  sfx.step();
                  setStep(Number(e.target.value));
                }}
                style={{ width: 140 }}
              />
              <span
                style={{
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 12,
                  minWidth: 70,
                  textAlign: "right",
                }}
              >
                {step} / {world.trajectory.length}
              </span>
            </div>
          </div>

          {/* Telemetry HUD Cards */}
          <div className="metric-grid" style={{ marginBottom: 14 }}>
            <div>
              <span>Current Step</span>
              <strong style={{ color: "var(--accent)" }}>
                step {step} / {world.trajectory.length}
              </strong>
            </div>
            <div>
              <span>Position [R, C]</span>
              <strong>
                {currentStepData
                  ? `[${currentStepData.agent[0]}, ${currentStepData.agent[1]}]`
                  : "Origin [0, 0]"}
              </strong>
            </div>
            <div>
              <span>Energy Remaining</span>
              <strong
                style={{
                  color: currentStepData && currentStepData.energy < 20 ? "var(--warn)" : "var(--ok)",
                }}
              >
                {currentStepData ? `${Math.round(currentStepData.energy)}%` : "100%"}
              </strong>
            </div>
            <div>
              <span>Resources Collected</span>
              <strong>
                {currentStepData ? (
                  currentStepData.collected_b !== undefined ? (
                    <span>
                      <span style={{ color: "#3fb950" }}>
                        {currentStepData.collected_a ?? currentStepData.collected} A
                      </span>
                      <span style={{ color: "var(--muted)", margin: "0 6px" }}>/</span>
                      <span style={{ color: "#f5a623" }}>{currentStepData.collected_b} B</span>
                    </span>
                  ) : (
                    `${currentStepData.collected} items`
                  )
                ) : world.config.n_resources_b ? (
                  <span>
                    <span style={{ color: "#3fb950" }}>0 A</span>
                    <span style={{ color: "var(--muted)", margin: "0 6px" }}>/</span>
                    <span style={{ color: "#f5a623" }}>0 B</span>
                  </span>
                ) : (
                  "0 items"
                )}
              </strong>
            </div>
            <div>
              <span>Total Reward</span>
              <strong style={{ color: "var(--ok)" }}>{world.total_reward.toFixed(2)}</strong>
            </div>
            <div>
              <span>Status</span>
              <strong>
                <span className={`badge ${world.terminated ? "done" : "running"}`}>
                  {world.terminated ? "completed" : "active"}
                </span>
              </strong>
            </div>
          </div>

          {/* Grid View */}
          <div
            style={{
              padding: 16,
              background: "#080c12",
              border: "1px solid var(--border)",
              borderRadius: 8,
              display: "inline-block",
            }}
          >
            <div
              className="grid"
              style={{
                gridTemplateColumns: `repeat(${world.grid[0].length}, 18px)`,
                gap: 2,
              }}
            >
              {grid.map((row, r) =>
                row.map((cell, c) => (
                  <div
                    key={`${r}-${c}`}
                    className="cell"
                    style={{
                      width: 18,
                      height: 18,
                      background: COLORS[cell] || COLORS[0],
                      borderRadius: cell === 9 ? "50%" : 2,
                      boxShadow:
                        cell === 9
                          ? "0 0 10px #00f0ff"
                          : cell === 4 || cell === 5
                          ? "0 0 6px #f5a623"
                          : cell === 2
                          ? "0 0 6px #3fb950"
                          : "none",
                      transition: "all 0.1s ease",
                    }}
                    title={`Cell [${r}, ${c}] - ${
                      cell === 9
                        ? "Agent"
                        : cell === 1
                        ? "Obstacle"
                        : cell === 2
                        ? "Resource A"
                        : cell === 4 || cell === 5
                        ? "Resource B"
                        : cell === 3
                        ? "Hazard"
                        : "Empty"
                    }`}
                  />
                ))
              )}
            </div>
          </div>

          <div className="legend" style={{ marginTop: 12 }}>
            <span>
              <span className="swatch" style={{ background: COLORS[0], border: "1px solid #333" }} />
              empty
            </span>
            <span>
              <span className="swatch" style={{ background: COLORS[1] }} />
              obstacle
            </span>
            <span>
              <span className="swatch" style={{ background: COLORS[2] }} />
              resource A (+reward)
            </span>
            <span>
              <span className="swatch" style={{ background: COLORS[5] }} />
              resource B (+high reward)
            </span>
            <span>
              <span className="swatch" style={{ background: COLORS[3] }} />
              hazard (-damage)
            </span>
            <span>
              <span
                className="swatch"
                style={{ background: COLORS[9], borderRadius: "50%", boxShadow: "0 0 6px #00f0ff" }}
              />
              agent
            </span>
          </div>
          <p className="muted" style={{ marginTop: 10 }}>
            morphology: {JSON.stringify(world.morphology)} · obs mode {String(world.config.obs_mode)}
          </p>
        </div>
      )}

      {/* EMBODIED INTELLIGENCE VIEW */}
      {!stale && plan && envKind === "embodied" && (
        <div className="panel">
          <div
            className="row"
            style={{
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 14,
              flexWrap: "wrap",
              gap: 8,
            }}
          >
            <div>
              <strong>{plan.body.morphology}</strong> · {plan.body.segments.length} capsules ·{" "}
              {plan.body.joints.length} {plan.body.joint_axis} joints
              {trajectory ? (
                <span className="badge done" style={{ marginLeft: 8 }}>
                  ● PyBullet Replay ({trajectory.steps} steps)
                </span>
              ) : (
                <span className="badge running" style={{ marginLeft: 8 }}>
                  schematic, not a physics replay
                </span>
              )}
            </div>

            {/* Viewer Mode Switcher */}
            <div className="row" style={{ gap: 6 }}>
              {trajectory && (
                <button
                  className={embodiedMode === "physics_replay" ? "primary" : ""}
                  onClick={() => {
                    sfx.click();
                    setEmbodiedMode("physics_replay");
                  }}
                  style={{ padding: "4px 11px", fontSize: 12 }}
                >
                  ▶ Physics Trajectory Replay
                </button>
              )}
              <button
                className={embodiedMode === "schematic_3d" ? "primary" : ""}
                onClick={() => {
                  sfx.click();
                  setEmbodiedMode("schematic_3d");
                }}
                style={{ padding: "4px 11px", fontSize: 12 }}
              >
                ⚙ Kinematics Wave
              </button>
              <button
                className={embodiedMode === "schematic_2d" ? "primary" : ""}
                onClick={() => {
                  sfx.click();
                  setEmbodiedMode("schematic_2d");
                }}
                style={{ padding: "4px 11px", fontSize: 12 }}
              >
                📐 2D Blueprint
              </button>
            </div>
          </div>

          {/* EMBODIED TRAJECTORY CONTROLS & HUD */}
          {embodiedMode === "physics_replay" && trajectory && (
            <div style={{ marginBottom: 14 }}>
              <div
                className="row"
                style={{
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 12,
                  flexWrap: "wrap",
                  gap: 10,
                }}
              >
                <div className="row" style={{ gap: 8 }}>
                  <button
                    className={isPlayingTraj ? "primary" : ""}
                    onClick={() => {
                      sfx.toggle();
                      setIsPlayingTraj((p) => !p);
                    }}
                    style={{ minWidth: 78 }}
                  >
                    {isPlayingTraj ? "⏸ Pause" : "▶ Replay"}
                  </button>
                  <button
                    onClick={() => {
                      sfx.step();
                      setTrajStep((s) => Math.max(0, s - 1));
                    }}
                  >
                    ◀ Step
                  </button>
                  <button
                    onClick={() => {
                      sfx.step();
                      setTrajStep((s) => Math.min(trajectory.trajectory.length - 1, s + 1));
                    }}
                  >
                    Step ▶
                  </button>
                  <button
                    onClick={() => {
                      sfx.toggle();
                      setTrajStep(0);
                    }}
                    title="Reset to step 0"
                  >
                    ↺
                  </button>
                </div>

                {/* Speed Multiplier & Loop */}
                <div className="row" style={{ gap: 8, alignItems: "center" }}>
                  <span style={{ fontSize: 11, color: "var(--muted)" }}>Speed:</span>
                  {[0.5, 1, 2, 5].map((spd) => (
                    <button
                      key={spd}
                      onClick={() => {
                        sfx.click();
                        setTrajSpeed(spd);
                      }}
                      style={{
                        padding: "2px 8px",
                        fontSize: 11,
                        background: trajSpeed === spd ? "var(--panel2)" : "transparent",
                        borderColor: trajSpeed === spd ? "var(--accent)" : "var(--border)",
                        color: trajSpeed === spd ? "var(--accent)" : "var(--muted)",
                      }}
                    >
                      {spd}×
                    </button>
                  ))}
                  <label
                    style={{
                      fontSize: 11,
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                      cursor: "pointer",
                      color: "var(--muted)",
                      marginLeft: 6,
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={trajLoop}
                      onChange={(e) => setTrajLoop(e.target.checked)}
                    />
                    Loop
                  </label>
                </div>

                {/* Scrubber slider */}
                <div className="row" style={{ gap: 10, alignItems: "center" }}>
                  <input
                    type="range"
                    min={0}
                    max={trajectory.trajectory.length - 1}
                    value={trajStep}
                    onChange={(e) => {
                      sfx.step();
                      setTrajStep(Number(e.target.value));
                    }}
                    style={{ width: 140 }}
                  />
                  <span
                    style={{
                      fontFamily: "JetBrains Mono, monospace",
                      fontSize: 12,
                      minWidth: 80,
                      textAlign: "right",
                    }}
                  >
                    {trajStep} / {trajectory.trajectory.length - 1}
                  </span>
                </div>
              </div>

              {/* Real Physics Telemetry Cards */}
              <div className="metric-grid" style={{ marginBottom: 14 }}>
                <div>
                  <span>Simulation Step</span>
                  <strong style={{ color: "var(--accent)" }}>
                    #{currentTrajFrame?.step ?? trajStep} ·{" "}
                    {currentTrajFrame?.time_s !== undefined
                      ? `${currentTrajFrame.time_s.toFixed(2)}s`
                      : "0.00s"}
                  </strong>
                </div>
                <div>
                  <span>Forward Displacement</span>
                  <strong style={{ color: "var(--ok)" }}>
                    +{currentTrajFrame?.base_pos[0]?.toFixed(3) ?? "0.000"} m
                  </strong>
                </div>
                <div>
                  <span>Distance to Target</span>
                  <strong>
                    {currentTrajFrame?.distance_to_target?.toFixed(3) ??
                      trajectory.target_distance.toFixed(3)}{" "}
                    m
                  </strong>
                </div>
                <div>
                  <span>Active Motor Primitive</span>
                  <strong style={{ color: "var(--accent)" }}>
                    {currentTrajFrame
                      ? `${currentTrajFrame.action_name.toUpperCase()} (#${currentTrajFrame.action})`
                      : "—"}
                  </strong>
                </div>
                <div>
                  <span>Cumulative Reward</span>
                  <strong style={{ color: "var(--ok)" }}>
                    {currentTrajFrame?.cumulative_reward?.toFixed(2) ?? "0.00"}
                  </strong>
                </div>
                <div>
                  <span>Upright Stability</span>
                  <strong>
                    <span
                      className={`badge ${
                        currentTrajFrame?.upright ?? true ? "done" : "failed"
                      }`}
                    >
                      {currentTrajFrame?.upright ?? true ? "upright" : "tumbled"}
                    </span>
                  </strong>
                </div>
              </div>
            </div>
          )}

          {/* 3D VIEWPORT (Physics Replay or Kinematic Wave) */}
          {embodiedMode === "physics_replay" ? (
            <div style={{ marginBottom: 14 }}>
              <MorphologyCanvas3D
                body={plan.body}
                trajectory={trajectory}
                playbackStep={trajStep}
                isReplayMode={true}
              />
            </div>
          ) : embodiedMode === "schematic_3d" ? (
            <div style={{ marginBottom: 14 }}>
              <MorphologyCanvas3D body={plan.body} isReplayMode={false} />
            </div>
          ) : (
            <svg
              className="morphology-plan"
              viewBox={`0 0 ${segmentPositions.width} 220`}
              role="img"
              aria-label={`${plan.body.morphology} body plan with ${plan.body.joints.length} ${plan.body.joint_axis} joints`}
            >
              <line
                x1="24"
                y1={segmentPositions.y}
                x2={segmentPositions.width - 24}
                y2={segmentPositions.y}
                className="body-axis"
              />
              {plan.body.segments.map((segment) => (
                <rect
                  key={segment.index}
                  className="body-segment"
                  x={segmentPositions.at(segment.index) - 21}
                  y={segmentPositions.y - 14}
                  width="42"
                  height="28"
                  rx="14"
                />
              ))}
              {plan.body.joints.map((joint) => (
                <circle
                  key={joint.index}
                  className="body-joint"
                  cx={(segmentPositions.at(joint.index) + segmentPositions.at(joint.index + 1)) / 2}
                  cy={segmentPositions.y}
                  r="5"
                />
              ))}
              <text x="24" y="42" className="svg-label">
                head / +x
              </text>
              <text x="24" y="190" className="svg-label">
                low longitudinal grip {plan.body.longitudinal_friction.toFixed(2)}
              </text>
              <text x={segmentPositions.width - 210} y="190" className="svg-label">
                lateral grip {plan.body.lateral_friction.toFixed(2)}
              </text>
            </svg>
          )}

          {/* Persisted Morphology Parameters */}
          <div className="metric-grid">
            <div>
              <span>joint limit</span>
              <strong>{plan.body.joint_limit.toFixed(2)} rad</strong>
            </div>
            <div>
              <span>motor cap</span>
              <strong>{plan.body.joint_max_torque.toFixed(2)} N·m</strong>
            </div>
            <div>
              <span>wave amplitude</span>
              <strong>{plan.body.gait_amplitude.toFixed(2)}× limit</strong>
            </div>
            <div>
              <span>position gain</span>
              <strong>{plan.body.motor_position_gain.toFixed(2)}</strong>
            </div>
          </div>

          {/* Calibration Evidence */}
          <div className="calibration-callout">
            <strong>Calibration gate · {plan.calibration.status}</strong>
            <p>{plan.calibration.acceptance}</p>
            <code>{plan.calibration.command}</code>
          </div>
          <div className="calibration-callout" style={{ marginTop: 10 }}>
            <strong>Latest captured evidence · {evidence?.status ?? "checking"}</strong>
            {evidence?.available ? (
              <p>
                {evidence.message}
                {evidence.acceptance?.best_forward_gain_m !== null &&
                evidence.acceptance?.best_forward_gain_m !== undefined
                  ? ` Best gain: ${evidence.acceptance.best_forward_gain_m.toFixed(3)} m.`
                  : ""}
              </p>
            ) : (
              <p>{evidence?.message ?? "Checking the persisted calibration artifact…"}</p>
            )}
          </div>

          {plan.organism_morphology && (
            <p className="muted" style={{ marginTop: 12 }}>
              Stored organism morphology: {JSON.stringify(plan.organism_morphology)}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
