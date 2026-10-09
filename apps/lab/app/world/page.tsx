"use client";

import { useEffect, useMemo, useState } from "react";
import { API_BASE, apiGet, ExperimentSummary, Trial } from "@/lib/api";
import MorphologyCanvas3D from "./MorphologyCanvas3D";

interface WorldData {
  experiment_id: string;
  trial_id: string;
  seed: number;
  config: Record<string, number | string>;
  grid: number[][];
  trajectory: { agent: number[]; action: number; reward: number; collected: number; energy: number }[];
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

const COLORS: Record<number, string> = {
  0: "#121821",
  1: "#3b4657",
  2: "#3fb950",
  3: "#f85149",
  4: "#4f9cf9",
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
  const [step, setStep] = useState(0);
  const [viewerTab, setViewerTab] = useState<"3d" | "2d">("3d");
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
    const request =
      envKind === "embodied"
        ? apiGet<MorphologyPlan>(`/api/morphology?experiment=${expId}&trial=${trialId}`)
        : apiGet<WorldData>(`/api/world?experiment=${expId}&trial=${trialId}&seed=${seed}`);
    request
      .then((data) => {
        if (cancelled) return;
        if (envKind === "embodied") {
          setPlan(data as MorphologyPlan);
        } else {
          setWorld(data as WorldData);
          setStep(0);
        }
      })
      .catch((e) => !cancelled && setErr(String(e)));
    return () => {
      cancelled = true;
    };
  }, [envKind, expId, resolvedExpId, trialId, seed]);

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
    if (world.trajectory.length > 0) {
      const pos = step === 0 ? null : world.trajectory[step - 1].agent;
      if (pos) replay[pos[0]][pos[1]] = 4;
    }
    return replay;
  }, [world, step]);

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
        persisted body specification and calibration gate; no physics trajectory is displayed
        until the crawler passes its PyBullet acceptance probe.
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
            <span className="badge running">physics calibration required</span>
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

      {!stale && grid && world && envKind === "gridworld" && (
        <div className="panel">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <div>
              <strong>step {step}</strong> / {world.trajectory.length} · total reward{" "}
              {world.total_reward.toFixed(2)} · {world.terminated ? "terminated" : "ended"}
            </div>
            <div className="row">
              <button onClick={() => setStep((s) => Math.max(0, s - 1))}>◀</button>
              <input
                type="range"
                min={0}
                max={world.trajectory.length}
                value={step}
                onChange={(e) => setStep(Number(e.target.value))}
              />
              <button onClick={() => setStep((s) => Math.min(world.trajectory.length, s + 1))}>▶</button>
            </div>
          </div>
          <div className="grid" style={{ gridTemplateColumns: `repeat(${world.grid[0].length}, 16px)`, marginTop: 12 }}>
            {grid.map((row, r) =>
              row.map((cell, c) => (
                <div key={`${r}-${c}`} className="cell" style={{ background: COLORS[cell] }} title={`${r},${c}`} />
              ))
            )}
          </div>
          <div className="legend">
            <span><span className="swatch" style={{ background: COLORS[0], border: "1px solid #333" }} />empty</span>
            <span><span className="swatch" style={{ background: COLORS[1] }} />obstacle</span>
            <span><span className="swatch" style={{ background: COLORS[2] }} />resource</span>
            <span><span className="swatch" style={{ background: COLORS[3] }} />hazard</span>
            <span><span className="swatch" style={{ background: COLORS[4] }} />agent</span>
          </div>
          <p className="muted" style={{ marginTop: 10 }}>
            morphology: {JSON.stringify(world.morphology)} · obs mode {String(world.config.obs_mode)}
          </p>
        </div>
      )}

      {!stale && plan && envKind === "embodied" && (
        <div className="panel">
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
            <div>
              <strong>{plan.body.morphology}</strong> · {plan.body.segments.length} capsules ·{" "}
              {plan.body.joints.length} {plan.body.joint_axis} joints
            </div>
            <div className="row">
              <button
                className={viewerTab === "3d" ? "primary" : ""}
                onClick={() => setViewerTab("3d")}
                style={{ padding: "3px 10px", fontSize: 12 }}
              >
                3D Articulated Kinematics
              </button>
              <button
                className={viewerTab === "2d" ? "primary" : ""}
                onClick={() => setViewerTab("2d")}
                style={{ padding: "3px 10px", fontSize: 12 }}
              >
                2D Blueprint Schematic
              </button>
            </div>
          </div>

          {viewerTab === "3d" ? (
            <div style={{ marginBottom: 14 }}>
              <MorphologyCanvas3D body={plan.body} />
            </div>
          ) : (
            <svg
              className="morphology-plan"
              viewBox={`0 0 ${segmentPositions.width} 220`}
              role="img"
              aria-label={`${plan.body.morphology} body plan with ${plan.body.joints.length} ${plan.body.joint_axis} joints`}
            >
              <line x1="24" y1={segmentPositions.y} x2={segmentPositions.width - 24} y2={segmentPositions.y} className="body-axis" />
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
              <text x="24" y="42" className="svg-label">head / +x</text>
              <text x="24" y="190" className="svg-label">low longitudinal grip {plan.body.longitudinal_friction.toFixed(2)}</text>
              <text x={segmentPositions.width - 210} y="190" className="svg-label">lateral grip {plan.body.lateral_friction.toFixed(2)}</text>
            </svg>
          )}
          <div className="metric-grid">
            <div><span>joint limit</span><strong>{plan.body.joint_limit.toFixed(2)} rad</strong></div>
            <div><span>motor cap</span><strong>{plan.body.joint_max_torque.toFixed(2)} N·m</strong></div>
            <div><span>wave amplitude</span><strong>{plan.body.gait_amplitude.toFixed(2)}× limit</strong></div>
            <div><span>position gain</span><strong>{plan.body.motor_position_gain.toFixed(2)}</strong></div>
          </div>
          <div className="calibration-callout">
            <strong>Calibration gate · {plan.calibration.status}</strong>
            <p>{plan.calibration.acceptance}</p>
            <code>{plan.calibration.command}</code>
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
