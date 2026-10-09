"use client";
import { useEffect, useMemo, useState } from "react";
import { apiGet, ExperimentSummary, getArtifactFileUrl } from "@/lib/api";
import { sfx } from "@/lib/sound";
import { toast } from "@/lib/toast";

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
  const [search, setSearch] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiGet<ExperimentSummary[]>("/api/experiments")
      .then((d) => {
        if (cancelled) return;
        setExps(d);
        setErr(null);
        if (d.length) setExpId(d[0].id);
      })
      .catch((e) => {
        if (!cancelled) setErr(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!expId) return;
    let cancelled = false;
    apiGet<Artifact[]>(`/api/artifacts?experiment=${expId}`)
      .then((d) => {
        if (cancelled) return;
        setArtifacts(d);
        setErr(null);
      })
      .catch((e) => {
        if (!cancelled) setErr(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [expId]);

  const plots = artifacts.filter((a) => a.kind === "plot");

  const filteredArtifacts = useMemo(() => {
    if (!search.trim()) return artifacts;
    const q = search.toLowerCase();
    return artifacts.filter(
      (a) => a.kind.toLowerCase().includes(q) || a.path.toLowerCase().includes(q)
    );
  }, [artifacts, search]);

  const copyPath = (path: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(path);
      sfx.blip();
      toast.info("Path copied to clipboard.");
    }
  };

  return (
    <div>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <h1>Research artifacts</h1>
          <p className="sub" style={{ margin: 0 }}>
            Manifests, checkpoints, plots, exports and reproduction instructions produced by the
            run. Files are served from the experiment store, confined to its root.
          </p>
        </div>
        {artifacts.length > 0 && (
          <input
            type="text"
            placeholder="Filter artifacts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 200, fontSize: 12 }}
          />
        )}
      </div>

      {err && <p className="err">{err}</p>}

      <div className="panel">
        <div className="row">
          <label>experiment</label>
          <select
            value={expId}
            onChange={(e) => {
              sfx.blip();
              setExpId(e.target.value);
            }}
          >
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
          <h2>Figures &amp; Visualizations</h2>
          <div className="row" style={{ flexWrap: "wrap", gap: 16 }}>
            {plots.map((p) => (
              <div
                key={p.id}
                style={{
                  background: "var(--panel2)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  padding: 10,
                  transition: "transform 0.2s ease, border-color 0.2s ease",
                }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={getArtifactFileUrl(p.id)}
                  alt={p.path}
                  style={{
                    maxWidth: 420,
                    borderRadius: 6,
                    display: "block",
                    border: "1px solid #1a2330",
                  }}
                />
                <div
                  className="row"
                  style={{ justifyContent: "space-between", alignItems: "center", marginTop: 8 }}
                >
                  <span className="muted" style={{ fontSize: 12, fontFamily: "monospace" }}>
                    {p.path.split("/").slice(-1)[0]}
                  </span>
                  <a
                    href={getArtifactFileUrl(p.id)}
                    target="_blank"
                    rel="noreferrer"
                    onClick={() => sfx.click()}
                    style={{ fontSize: 11 }}
                  >
                    view full
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="panel">
        <h2>All artifacts ({filteredArtifacts.length})</h2>
        <table>
          <thead>
            <tr>
              <th>kind</th>
              <th>trial</th>
              <th>path</th>
              <th>actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredArtifacts.map((a) => (
              <tr key={a.id}>
                <td>
                  <span className="badge done">{a.kind}</span>
                </td>
                <td className="muted">{a.trial_id ?? "—"}</td>
                <td className="muted" style={{ fontFamily: "monospace", fontSize: 12 }}>
                  {a.path}
                </td>
                <td>
                  <div className="row" style={{ gap: 6 }}>
                    <a
                      href={getArtifactFileUrl(a.id)}
                      target="_blank"
                      rel="noreferrer"
                      onClick={() => sfx.click()}
                      style={{ fontSize: 12 }}
                    >
                      open
                    </a>
                    <button
                      onClick={() => copyPath(a.path)}
                      style={{ fontSize: 10, padding: "2px 6px" }}
                      title="Copy artifact path"
                    >
                      copy
                    </button>
                  </div>
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

