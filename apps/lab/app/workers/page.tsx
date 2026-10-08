"use client";

import { useEffect, useState } from "react";
import {
  apiGet,
  apiPost,
  SystemCapabilities,
  WorkerInfo,
  WorkerReport,
} from "@/lib/api";

export default function WorkersPage() {
  const [report, setReport] = useState<WorkerReport | null>(null);
  const [caps, setCaps] = useState<SystemCapabilities | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reapMessage, setReapMessage] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      apiGet<WorkerReport>("/api/workers"),
      apiGet<SystemCapabilities>("/api/capabilities"),
    ])
      .then(([wRep, cRep]) => {
        if (cancelled) return;
        setReport(wRep);
        setCaps(cRep);
        setError(null);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
        setLoading(false);
      });

    if (!autoRefresh) {
      return () => {
        cancelled = true;
      };
    }
    const interval = setInterval(() => {
      setRefreshTrigger((prev) => prev + 1);
    }, 3000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [autoRefresh, refreshTrigger]);

  const handleRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleReap = async () => {
    try {
      const res = await apiPost<{ reaped: boolean; dead_workers: string[]; recovered_trials: string[] }>(
        "/api/workers/reap",
        { stale_after: 120.0 }
      );
      setReapMessage(
        `Reaped ${res.dead_workers.length} dead worker(s); reclaimed ${res.recovered_trials.length} trial(s) back to queue.`
      );
      handleRefresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const workers = report?.workers ?? [];
  const trialCounts = report?.trial_counts ?? {};

  const activeWorkers = workers.filter(
    (w) => w.status === "running" && w.heartbeat_age_seconds <= 120
  );
  const staleWorkers = workers.filter(
    (w) => w.status === "running" && w.heartbeat_age_seconds > 120
  );

  return (
    <div>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1>Cluster &amp; Compute Workers</h1>
          <p className="sub">
            Real-time monitor for local and distributed worker processes. Trials are claimed
            atomically from the shared SQLite store.
          </p>
        </div>
        <div className="row">
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (3s)
          </label>
          <button onClick={handleRefresh}>Refresh</button>
          <button className="primary" onClick={handleReap}>
            Reap Stale Workers
          </button>
        </div>
      </div>

      {reapMessage && (
        <div className="panel" style={{ borderColor: "var(--ok)", background: "#102316" }}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <span>{reapMessage}</span>
            <button onClick={() => setReapMessage(null)} style={{ padding: "2px 8px" }}>
              ✕
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="panel" style={{ borderColor: "var(--err)" }}>
          <p className="err">{error}</p>
        </div>
      )}

      {/* Cluster Overview Cards */}
      <div className="metric-grid" style={{ marginBottom: 16 }}>
        <div>
          <span>Active Workers</span>
          <strong style={{ fontSize: 20, color: "var(--ok)" }}>{activeWorkers.length}</strong>
        </div>
        <div>
          <span>Stale / Orphaned</span>
          <strong style={{ fontSize: 20, color: staleWorkers.length > 0 ? "var(--warn)" : "var(--muted)" }}>
            {staleWorkers.length}
          </strong>
        </div>
        <div>
          <span>Trials Completed</span>
          <strong style={{ fontSize: 20 }}>{trialCounts.done ?? 0}</strong>
        </div>
        <div>
          <span>Trials In-Flight</span>
          <strong style={{ fontSize: 20, color: "var(--accent)" }}>{trialCounts.running ?? 0}</strong>
        </div>
        <div>
          <span>Trials Pending</span>
          <strong style={{ fontSize: 20 }}>{trialCounts.pending ?? 0}</strong>
        </div>
        <div>
          <span>Trials Failed</span>
          <strong style={{ fontSize: 20, color: trialCounts.failed ? "var(--err)" : "inherit" }}>
            {trialCounts.failed ?? 0}
          </strong>
        </div>
      </div>

      {/* Platform & Simulators capability card */}
      {caps && (
        <div className="panel" style={{ marginBottom: 16 }}>
          <h2 style={{ marginTop: 0, fontSize: 14 }}>Host &amp; Compute Capabilities</h2>
          <div className="row" style={{ gap: 24, fontSize: 13 }}>
            <div>
              <span className="muted">Platform:</span> <strong>{caps.platform}</strong> ({caps.cpus} CPUs)
            </div>
            <div>
              <span className="muted">Python:</span> <strong>v{caps.python}</strong>
            </div>
            <div>
              <span className="muted">Simulators:</span>{" "}
              {caps.simulators.map((s) => (
                <span key={s} className="badge done" style={{ marginRight: 6 }}>
                  {s}
                </span>
              ))}
            </div>
            <div>
              <span className="muted">Embodied PyBullet:</span>{" "}
              <span className={`badge ${caps.embodied_available ? "done" : "running"}`}>
                {caps.embodied_available ? "available" : "calibration/mock"}
              </span>
            </div>
            <div>
              <span className="muted">API Security:</span>{" "}
              <span className={`badge ${caps.auth_enabled ? "done" : ""}`}>
                {caps.auth_enabled ? "token protected" : "loopback open"}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Workers table */}
      <div className="panel">
        <h2 style={{ marginTop: 0 }}>Registered Workers ({workers.length})</h2>
        {loading && !report ? (
          <p className="muted">Loading workers…</p>
        ) : workers.length === 0 ? (
          <p className="muted">
            No workers currently registered. Start workers with:
            <br />
            <code>origin-worker --config configs/pilot.json --store runs</code>
          </p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Worker ID</th>
                <th>Host</th>
                <th>PID</th>
                <th>Status</th>
                <th>Heartbeat Age</th>
                <th>Started At</th>
              </tr>
            </thead>
            <tbody>
              {workers.map((w: WorkerInfo) => {
                const isLive = w.status === "running" && w.heartbeat_age_seconds <= 120;
                const isStale = w.status === "running" && w.heartbeat_age_seconds > 120;
                return (
                  <tr key={w.id}>
                    <td>
                      <code>{w.id}</code>
                    </td>
                    <td>{w.host}</td>
                    <td>{w.pid}</td>
                    <td>
                      <span className={`badge ${isLive ? "done" : isStale ? "running" : "failed"}`}>
                        {isLive ? "active" : isStale ? "stale" : w.status}
                      </span>
                    </td>
                    <td>
                      {w.heartbeat_age_seconds < 60
                        ? `${Math.round(w.heartbeat_age_seconds)}s ago`
                        : `${(w.heartbeat_age_seconds / 60).toFixed(1)}m ago`}
                    </td>
                    <td>{new Date(w.started_at * 1000).toLocaleTimeString()}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
