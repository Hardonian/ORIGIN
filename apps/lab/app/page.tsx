"use client";
import { useEffect, useState } from "react";
import {
  API_BASE,
  apiGet,
  ExperimentSummary,
  Comparison,
  fmt,
} from "@/lib/api";

export default function OverviewPage() {
  const [exps, setExps] = useState<ExperimentSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [cmp, setCmp] = useState<Comparison | null>(null);

  useEffect(() => {
    apiGet<ExperimentSummary[]>("/api/experiments")
      .then((d) => {
        setExps(d);
        if (d.length && !sel) setSel(d[0].id);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  useEffect(() => {
    if (!sel) return;
    setCmp(null);
    apiGet<Comparison>(`/api/compare?experiment=${sel}`)
      .then(setCmp)
      .catch((e) => setErr(String(e)));
  }, [sel]);

  if (err)
    return (
      <div className="panel">
        <h1>Research overview</h1>
        <p className="err">Cannot reach the ORIGIN API at {API_BASE}.</p>
        <p className="muted">
          Start it with: <code>.venv/bin/origin-api --store runs --port 8788</code>
        </p>
        <p className="muted">{err}</p>
      </div>
    );

  return (
    <div>
      <h1>Research overview</h1>
      <p className="sub">
        Active and completed experiments, method comparison and resource utilisation.
        Every value is read from the persisted experiment store.
      </p>

      <div className="panel">
        <h2>Experiments</h2>
        {!exps && <p className="muted">loading…</p>}
        {exps && exps.length === 0 && (
          <p className="muted">
            No experiments yet. Run <code>origin-run --config configs/pilot.json --store runs</code>.
          </p>
        )}
        {exps && exps.length > 0 && (
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
              {exps.map((e) => (
                <tr key={e.id} className={e.id === sel ? "sel" : ""} onClick={() => setSel(e.id)} style={{ cursor: "pointer" }}>
                  <td>{e.id}</td>
                  <td>{e.name}</td>
                  <td className="muted">{e.protocol}</td>
                  <td>
                    <span className={`badge ${e.summary?.n_failed ? "failed" : "done"}`}>{e.status}</span>
                  </td>
                  <td>{e.summary?.n_trials ?? "—"}</td>
                  <td>{e.summary?.n_done ?? "—"}</td>
                  <td className={e.summary?.n_failed ? "err" : ""}>{e.summary?.n_failed ?? "—"}</td>
                  <td className="muted">{(e.git_sha || "").slice(0, 7) || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {cmp && (
        <div className="panel">
          <h2>Method comparison — {cmp.experiment_id} ({cmp.n_done} trials)</h2>
          <table>
            <thead>
              <tr>
                <th>method</th>
                <th>n</th>
                <th>held-out reward</th>
                <th>± std</th>
                <th>train fitness</th>
                <th>mean interactions</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(cmp.comparison).map(([algo, c]) => (
                <tr key={algo}>
                  <td>{algo}</td>
                  <td>{c.n}</td>
                  <td>{fmt(c.test_mean_reward)}</td>
                  <td className="muted">±{fmt(c.test_std_reward)}</td>
                  <td>{fmt(c.train_mean_fitness)}</td>
                  <td>{Math.round(c.mean_interactions).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted" style={{ marginTop: 10 }}>
            Held-out reward is measured on seed sets disjoint from training. The scripted
            heuristic is a privileged reference, not a like-for-like competitor.
          </p>
        </div>
      )}
    </div>
  );
}
