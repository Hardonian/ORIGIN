"use client";
import { useEffect, useState } from "react";
import { apiGet, apiPost, Comparison, ExperimentSummary, fmt } from "@/lib/api";

export default function BenchmarkPage() {
  const [exps, setExps] = useState<ExperimentSummary[]>([]);
  const [expId, setExpId] = useState("");
  const [cmp, setCmp] = useState<Comparison | null>(null);
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
    apiGet<Comparison>(`/api/compare?experiment=${expId}`)
      .then(setCmp)
      .catch((e) => setErr(String(e)));
  }, [expId]);

  const variants = new Set<string>();
  if (cmp) Object.values(cmp.comparison).forEach((c) => Object.keys(c.transfer).forEach((v) => variants.add(v)));
  const algos = cmp ? Object.keys(cmp.comparison) : [];

  return (
    <div>
      <h1>Benchmark analysis</h1>
      <p className="sub">
        Method comparison across held-out evaluation and cross-morphology / perturbation
        transfer, with interaction budgets reported explicitly.
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

      {cmp && (
        <>
          <div className="panel">
            <h2>Held-out performance & compute</h2>
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
                {Object.entries(cmp.comparison).map(([a, c]) => (
                  <tr key={a}>
                    <td>{a}</td>
                    <td>{c.n}</td>
                    <td>{fmt(c.test_mean_reward)}</td>
                    <td className="muted">±{fmt(c.test_std_reward)}</td>
                    <td>{fmt(c.train_mean_fitness)}</td>
                    <td>{Math.round(c.mean_interactions).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="panel">
            <h2>Transfer (zero-shot → adapted)</h2>
            <table>
              <thead>
                <tr>
                  <th>variant</th>
                  {algos.map((a) => (
                    <th key={a}>{a}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[...variants].sort().map((v) => (
                  <tr key={v}>
                    <td>
                      {v} <span className="muted">({cmp.comparison[algos[0]].transfer[v]?.kind ?? ""})</span>
                    </td>
                    {algos.map((a) => {
                      const t = cmp.comparison[a].transfer[v];
                      if (!t) return <td key={a} className="muted">—</td>;
                      return (
                        <td key={a}>
                          {fmt(t.zero_shot, 2)}
                          {t.adapted !== null && <span className="muted"> → {fmt(t.adapted, 2)}</span>}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted" style={{ marginTop: 10 }}>
              Zero-shot = performance with no further training; adapted = performance after a
              fixed interaction budget on the new morphology. Perturbations are evaluated
              zero-shot only.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
