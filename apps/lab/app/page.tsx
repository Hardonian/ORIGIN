"use client";
import { useEffect, useState } from "react";
import {
  API_BASE,
  apiGet,
  ExperimentSummary,
  Comparison,
  fmt,
  getExportUrl,
} from "@/lib/api";
import { sfx } from "@/lib/sound";
import { showToast } from "@/lib/toast";

export default function OverviewPage() {
  const [exps, setExps] = useState<ExperimentSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [cmp, setCmp] = useState<Comparison | null>(null);
  const [live, setLive] = useState(false);
  const [tick, setTick] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");

  const reload = () => {
    sfx.click();
    setTick((t) => t + 1);
  };

  useEffect(() => {
    apiGet<ExperimentSummary[]>("/api/experiments")
      .then((d) => {
        setExps(d);
        if (d.length) setSel((cur) => cur ?? d[0].id);
      })
      .catch((e) => setErr(String(e)));
  }, [tick]);

  useEffect(() => {
    if (!sel) return;
    apiGet<Comparison>(`/api/compare?experiment=${sel}`)
      .then(setCmp)
      .catch((e) => setErr(String(e)));
  }, [sel, tick]);

  useEffect(() => {
    if (!live) return;
    const interval = setInterval(() => setTick((t) => t + 1), 3000);
    return () => clearInterval(interval);
  }, [live]);

  if (err)
    return (
      <div className="panel" style={{ borderColor: "var(--err)" }}>
        <h1>Research overview</h1>
        <p className="err">Cannot reach the ORIGIN API at {API_BASE}.</p>
        <p className="muted">
          Start it with: <code>origin-api --store runs --port 8788</code>
        </p>
        <p className="muted">{err}</p>
      </div>
    );

  // Compute leaderboard podium for selected experiment
  const rankedMethods = cmp
    ? Object.entries(cmp.comparison)
        .map(([algo, data]) => ({ algo, ...data }))
        .sort((a, b) => (b.test_mean_reward ?? -999) - (a.test_mean_reward ?? -999))
    : [];

  const totalTrials = exps?.reduce((acc, e) => acc + (e.summary?.n_done ?? 0), 0) ?? 0;
  const filteredExps = exps?.filter((e) =>
    e.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    e.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    e.protocol.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div>
      {/* Header & Global Stats */}
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", marginBottom: 18 }}>
        <div>
          <h1>Research overview</h1>
          <p className="sub" style={{ margin: 0 }}>
            Evolutionary intelligence benchmark, real-time campaign telemetry, and held-out evaluation.
          </p>
        </div>
        <div className="row">
          <label style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={live}
              onChange={(e) => {
                setLive(e.target.checked);
                sfx.click();
                showToast(e.target.checked ? "Live telemetry enabled" : "Live telemetry paused", "info");
              }}
            />
            Live Telemetry (3s)
          </label>
          <button style={{ fontSize: 13, padding: "5px 12px" }} onClick={reload}>
            ⟳ Refresh
          </button>
          {sel && (
            <a
              href={getExportUrl(sel, "csv")}
              target="_blank"
              rel="noreferrer"
              onClick={() => {
                sfx.click();
                showToast("Downloading trials CSV export...", "success");
              }}
              style={{
                fontSize: 13,
                padding: "5px 12px",
                background: "rgba(0, 240, 255, 0.1)",
                border: "1px solid rgba(0, 240, 255, 0.4)",
                borderRadius: 6,
                color: "var(--accent)",
                fontWeight: 600,
              }}
            >
              📥 Export Trials CSV
            </a>
          )}
        </div>
      </div>

      {/* High-level telemetry chips */}
      <div className="metric-grid" style={{ marginBottom: 20 }}>
        <div>
          <span>Campaigns Stored</span>
          <strong style={{ fontSize: 20, color: "var(--accent)" }}>{exps?.length ?? 0}</strong>
        </div>
        <div>
          <span>Total Trials Solved</span>
          <strong style={{ fontSize: 20, color: "var(--ok)" }}>{totalTrials.toLocaleString()}</strong>
        </div>
        <div>
          <span>Active Selection</span>
          <strong style={{ fontSize: 16, color: "#fff" }}>{sel ?? "None"}</strong>
        </div>
        <div>
          <span>Apex Controller</span>
          <strong style={{ fontSize: 16, color: "var(--gold)" }}>
            {rankedMethods[0]?.algo ?? "Awaiting Data"}
          </strong>
        </div>
      </div>

      {/* Gamified Leaderboard Podium for Selected Experiment */}
      {cmp && cmp.experiment_id === sel && rankedMethods.length >= 2 && (
        <div style={{ marginBottom: 22 }}>
          <h2>🏆 Performance Podium — {cmp.experiment_id}</h2>
          <div className="podium-grid">
            {rankedMethods.slice(0, 3).map((item, idx) => {
              const rankClass = idx === 0 ? "rank-1" : idx === 1 ? "rank-2" : "rank-3";
              const trophy = idx === 0 ? "🥇 1ST PLACE" : idx === 1 ? "🥈 2ND PLACE" : "🥉 3RD PLACE";
              const badgeKind = idx === 0 ? "gold" : idx === 1 ? "silver" : "bronze";

              return (
                <div key={item.algo} className={`podium-card ${rankClass}`}>
                  <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
                    <span className={`badge ${badgeKind}`}>{trophy}</span>
                    <span className="muted" style={{ fontSize: 11 }}>{item.n} trials</span>
                  </div>
                  <h3 style={{ margin: "4px 0 10px", fontSize: 18, color: "#fff" }}>{item.algo}</h3>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <span className="muted">Held-Out Reward:</span>
                    <strong style={{ fontSize: 18, color: idx === 0 ? "var(--accent)" : "#f0f4f8" }}>
                      {fmt(item.test_mean_reward)}
                    </strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontSize: 12 }}>
                    <span className="muted">Interactions:</span>
                    <span>{Math.round(item.mean_interactions).toLocaleString()}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Experiments Explorer Table */}
      <div className="panel">
        <div className="row" style={{ justifyContent: "space-between", marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Experiments &amp; Campaigns</h2>
          <input
            type="text"
            placeholder="Search experiments..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: 220, fontSize: 12, padding: "4px 8px" }}
          />
        </div>
        {!exps && <p className="muted">Loading experiments…</p>}
        {exps && exps.length === 0 && (
          <p className="muted">
            No experiments yet. Run <code>origin-run --config configs/pilot.json --store runs</code>.
          </p>
        )}
        {filteredExps && filteredExps.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>id</th>
                <th>name</th>
                <th>protocol</th>
                <th>status</th>
                <th>trials</th>
                <th>done</th>
                <th>failed</th>
                <th>git</th>
              </tr>
            </thead>
            <tbody>
              {filteredExps.map((e) => (
                <tr
                  key={e.id}
                  className={e.id === sel ? "sel" : ""}
                  onClick={() => {
                    sfx.click();
                    setSel(e.id);
                  }}
                  style={{ cursor: "pointer" }}
                >
                  <td>
                    <strong>{e.id}</strong>
                  </td>
                  <td>{e.name}</td>
                  <td className="muted">{e.protocol}</td>
                  <td>
                    <span className={`badge ${e.summary?.n_failed ? "failed" : "done"}`}>
                      {e.status}
                    </span>
                  </td>
                  <td>{e.summary?.n_trials ?? "—"}</td>
                  <td>
                    <strong style={{ color: "var(--ok)" }}>{e.summary?.n_done ?? "—"}</strong>
                  </td>
                  <td className={e.summary?.n_failed ? "err" : "muted"}>
                    {e.summary?.n_failed ?? "—"}
                  </td>
                  <td className="muted mono">{(e.git_sha || "").slice(0, 7) || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Detailed Method Comparison Table */}
      {cmp && cmp.experiment_id === sel && (
        <div className="panel panel-glow">
          <h2>📊 Method Comparison — {cmp.experiment_id} ({cmp.n_done} trials)</h2>
          <table>
            <thead>
              <tr>
                <th>rank</th>
                <th>method</th>
                <th>n</th>
                <th>held-out reward</th>
                <th>± std</th>
                <th>train fitness</th>
                <th>mean interactions</th>
              </tr>
            </thead>
            <tbody>
              {rankedMethods.map((c, index) => (
                <tr key={c.algo}>
                  <td>
                    <span className={`badge ${index === 0 ? "gold" : index === 1 ? "silver" : index === 2 ? "bronze" : ""}`}>
                      #{index + 1}
                    </span>
                  </td>
                  <td>
                    <strong>{c.algo}</strong>
                  </td>
                  <td>{c.n}</td>
                  <td>
                    <strong style={{ color: index === 0 ? "var(--accent)" : "inherit" }}>
                      {fmt(c.test_mean_reward)}
                    </strong>
                  </td>
                  <td className="muted">±{fmt(c.test_std_reward)}</td>
                  <td>{fmt(c.train_mean_fitness)}</td>
                  <td>{Math.round(c.mean_interactions).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted" style={{ marginTop: 12, fontSize: 12 }}>
            Held-out reward is measured on seed sets disjoint from training. The scripted
            heuristic is a privileged global reference, not a like-for-like competitor.
          </p>
        </div>
      )}
    </div>
  );
}
