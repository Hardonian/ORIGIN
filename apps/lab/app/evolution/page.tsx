"use client";
import { useEffect, useState } from "react";
import { apiGet, ExperimentSummary, parseJson, Trial } from "@/lib/api";

interface Metrics {
  descriptor_spread?: number;
  n_generations?: number;
  history?: Record<string, number>[];
  algorithm_extra?: Record<string, unknown>;
}

export default function EvolutionPage() {
  const [exps, setExps] = useState<ExperimentSummary[]>([]);
  const [expId, setExpId] = useState("");
  const [trials, setTrials] = useState<Trial[]>([]);
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
    apiGet<{ trials: Trial[] }>(`/api/experiments/${expId}`)
      .then((d) => setTrials(d.trials.filter((t) => t.status === "done")))
      .catch((e) => setErr(String(e)));
  }, [expId]);

  const byAlgo: Record<string, Trial[]> = {};
  trials.forEach((t) => {
    (byAlgo[t.algorithm] ||= []).push(t);
  });
  const maxFit = Math.max(1e-9, ...trials.map((t) => t.best_fitness ?? 0));

  return (
    <div>
      <h1>Evolution explorer</h1>
      <p className="sub">
        Fitness distributions across independent seeds and behavioural-descriptor spread per
        method. Populations are summarised from stored per-trial metrics.
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
        </div>
      </div>

      {Object.entries(byAlgo).map(([algo, ts]) => {
        const fits = ts.map((t) => t.best_fitness ?? 0);
        const mean = fits.reduce((a, b) => a + b, 0) / Math.max(1, fits.length);
        const spread = ts
          .map((t) => parseJson<Metrics>(t.metrics_json, {}).descriptor_spread ?? 0)
          .reduce((a, b) => a + b, 0) / Math.max(1, ts.length);
        const gens = ts.map((t) => parseJson<Metrics>(t.metrics_json, {}).n_generations ?? 0);
        return (
          <div className="panel" key={algo}>
            <h2>{algo}</h2>
            <table>
              <thead>
                <tr>
                  <th>seed</th>
                  <th>best fitness</th>
                  <th>generations</th>
                  <th>interactions</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {ts.map((t, i) => (
                  <tr key={t.id}>
                    <td>{t.seed}</td>
                    <td>{(t.best_fitness ?? 0).toFixed(3)}</td>
                    <td>{gens[i]}</td>
                    <td>{(t.interactions ?? 0).toLocaleString()}</td>
                    <td style={{ width: "40%" }}>
                      <div className="bar" style={{ width: `${(Math.max(0, t.best_fitness ?? 0) / maxFit) * 100}%` }} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted" style={{ marginTop: 8 }}>
              mean best fitness {mean.toFixed(3)} · mean descriptor spread {spread.toFixed(4)}
            </p>
          </div>
        );
      })}
    </div>
  );
}
