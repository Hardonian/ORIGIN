"use client";
import { useEffect, useState } from "react";
import { apiGet, ExperimentSummary, getArtifactFileUrl } from "@/lib/api";

interface Artifact {
  id: number;
  experiment_id: string;
  trial_id: string | null;
  kind: string;
  path: string;
  created_at: number;
}

export default function ArtifactsPage() {
  const [exps, setExps] = useState<ExperimentSummary[]>([]);
  const [expId, setExpId] = useState("");
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
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
    apiGet<Artifact[]>(`/api/artifacts?experiment=${expId}`)
      .then(setArtifacts)
      .catch((e) => setErr(String(e)));
  }, [expId]);

  const plots = artifacts.filter((a) => a.kind === "plot");

  return (
    <div>
      <h1>Research artifacts</h1>
      <p className="sub">
        Manifests, checkpoints, plots, exports and reproduction instructions produced by the
        run. Files are served from the experiment store, confined to its root.
      </p>
      {err && <p className="err">{err}</p>}

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
          <span className="muted">
            manifest: <code>{expId}/manifest.json</code> · summary:{" "}
            <code>{expId}/summary.json</code>
          </span>
        </div>
      </div>

      {plots.length > 0 && (
        <div className="panel">
          <h2>Figures</h2>
          <div className="row">
            {plots.map((p) => (
              <div key={p.id}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={getArtifactFileUrl(p.id)}
                  alt={p.path}
                  style={{ maxWidth: 420, border: "1px solid #222d3a", borderRadius: 6 }}
                />
                <div className="muted" style={{ fontSize: 12 }}>
                  {p.path.split("/").slice(-1)[0]}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="panel">
        <h2>All artifacts</h2>
        <table>
          <thead>
            <tr>
              <th>kind</th>
              <th>trial</th>
              <th>path</th>
              <th>download</th>
            </tr>
          </thead>
          <tbody>
            {artifacts.map((a) => (
              <tr key={a.id}>
                <td>{a.kind}</td>
                <td className="muted">{a.trial_id ?? "—"}</td>
                <td className="muted">{a.path}</td>
                <td>
                  <a href={getArtifactFileUrl(a.id)} target="_blank" rel="noreferrer">
                    open
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {artifacts.length === 0 && <p className="muted">No artifacts registered yet.</p>}
      </div>
    </div>
  );
}
