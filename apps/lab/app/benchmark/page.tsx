"use client";
import { useEffect, useMemo, useState } from "react";
import { apiGet, Comparison, ExperimentSummary, fmt, getExportUrl } from "@/lib/api";
import { sfx } from "@/lib/sound";

export default function BenchmarkPage() {
  const [exps, setExps] = useState<ExperimentSummary[]>([]);
  const [expId, setExpId] = useState("");
  const [cmp, setCmp] = useState<Comparison | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
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

  const variants = useMemo(() => {
    const vars = new Set<string>();
    if (cmp) {
      Object.values(cmp.comparison).forEach((c) =>
        Object.keys(c.transfer).forEach((v) => vars.add(v))
      );
    }
    return vars;
  }, [cmp]);

  const algos = cmp ? Object.keys(cmp.comparison) : [];

  const filteredVariants = useMemo(() => {
    const list = [...variants].sort();
    if (!searchQuery.trim()) return list;
    const q = searchQuery.toLowerCase();
    return list.filter((v) => v.toLowerCase().includes(q));
  }, [variants, searchQuery]);

  // Compute adaptability scorecards
  const adaptabilityScores = useMemo(() => {
    if (!cmp) return {};
    const scores: Record<
      string,
      { meanGain: number; validCount: number; tier: string; tierClass: string }
    > = {};

    algos.forEach((a) => {
      let totalGain = 0;
      let count = 0;
      Object.values(cmp.comparison[a].transfer).forEach((t) => {
        if (t && t.adapted !== null) {
          totalGain += t.adapted - t.zero_shot;
          count++;
        }
      });
      const meanGain = count > 0 ? totalGain / count : 0;
      let tier = "B-Tier Stable";
      let tierClass = "tier-embryonic";
      if (meanGain >= 0.2) {
        tier = "S-Tier Dynamic Adapter 🚀";
        tierClass = "tier-apex";
      } else if (meanGain >= 0.05) {
        tier = "A-Tier Rapid Learner ⚡";
        tierClass = "tier-adaptive";
      } else if (meanGain < 0) {
        tier = "C-Tier Overfit Risk ⚠️";
        tierClass = "tier-embryonic";
      }
      scores[a] = { meanGain, validCount: count, tier, tierClass };
    });

    return scores;
  }, [cmp, algos]);

  return (
    <div>
      <div
        className="row"
        style={{
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 16,
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div>
          <h1>Benchmark analysis</h1>
          <p className="sub" style={{ margin: 0 }}>
            Method comparison across held-out evaluation and cross-morphology / perturbation
            transfer, with interaction budgets reported explicitly.
          </p>
        </div>
        {expId && (
          <a
            href={getExportUrl(expId, "csv")}
            target="_blank"
            rel="noreferrer"
            onClick={() => sfx.click()}
            style={{
              fontSize: 12,
              padding: "6px 12px",
              background: "var(--panel2)",
              border: "1px solid var(--accent)",
              borderRadius: 6,
              color: "var(--accent)",
              textDecoration: "none",
              boxShadow: "0 0 10px rgba(0, 240, 255, 0.15)",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <span>📥 Export Benchmark CSV</span>
          </a>
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
        </div>
      </div>

      {cmp && (
        <>
          {/* Adaptability Index Scorecards */}
          <div className="panel">
            <h2 style={{ marginTop: 0 }}>Adaptability Index &amp; Generalization Ratings</h2>
            <div className="podium-grid" style={{ marginBottom: 0 }}>
              {algos.map((a) => {
                const sc = adaptabilityScores[a];
                return (
                  <div key={a} className="podium-card">
                    <div className="row" style={{ justifyContent: "space-between", marginBottom: 6 }}>
                      <strong style={{ fontSize: 16 }}>{a}</strong>
                      {sc && <span className={`tier-badge ${sc.tierClass}`}>{sc.tier}</span>}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 8 }}>
                      Mean Adaptation Delta:{" "}
                      <strong
                        style={{
                          color: sc && sc.meanGain >= 0 ? "var(--ok)" : "var(--warn)",
                          fontFamily: "JetBrains Mono, monospace",
                        }}
                      >
                        {sc && sc.meanGain >= 0 ? "+" : ""}
                        {sc ? sc.meanGain.toFixed(3) : "0.000"}
                      </strong>
                    </div>
                    <div style={{ fontSize: 11, color: "var(--muted)" }}>
                      Evaluated on {sc ? sc.validCount : 0} transfer targets
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Held-out performance & compute */}
          <div className="panel">
            <h2>Held-out performance &amp; compute</h2>
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
                    <td>
                      <strong>{a}</strong>
                    </td>
                    <td>{c.n}</td>
                    <td style={{ color: "var(--accent)", fontFamily: "JetBrains Mono, monospace" }}>
                      {fmt(c.test_mean_reward)}
                    </td>
                    <td className="muted">±{fmt(c.test_std_reward)}</td>
                    <td style={{ fontFamily: "JetBrains Mono, monospace" }}>{fmt(c.train_mean_fitness)}</td>
                    <td style={{ fontFamily: "JetBrains Mono, monospace" }}>
                      {Math.round(c.mean_interactions).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Transfer Heatmap with search filter */}
          <div className="panel">
            <div
              className="row"
              style={{
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 12,
                flexWrap: "wrap",
                gap: 8,
              }}
            >
              <div>
                <h2 style={{ margin: 0 }}>Transfer Matrix Heatmap (zero-shot → adapted)</h2>
                <span className="muted" style={{ fontSize: 12 }}>
                  Showing {filteredVariants.length} of {variants.size} target environments
                </span>
              </div>
              <input
                type="text"
                placeholder="Filter variants..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{ width: 200, fontSize: 12 }}
              />
            </div>

            <table>
              <thead>
                <tr>
                  <th>variant target</th>
                  {algos.map((a) => (
                    <th key={a}>{a}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredVariants.map((v) => (
                  <tr key={v}>
                    <td>
                      <strong>{v}</strong>{" "}
                      <span className="muted" style={{ fontSize: 11 }}>
                        ({cmp.comparison[algos[0]].transfer[v]?.kind ?? ""})
                      </span>
                    </td>
                    {algos.map((a) => {
                      const t = cmp.comparison[a].transfer[v];
                      if (!t) return <td key={a} className="muted">—</td>;

                      const hasAdapted = t.adapted !== null;
                      const delta = hasAdapted ? (t.adapted as number) - t.zero_shot : null;
                      const cellClass =
                        delta === null
                          ? "cell-neutral"
                          : delta > 0.05
                          ? "cell-gain"
                          : delta < -0.05
                          ? "cell-loss"
                          : "cell-neutral";

                      return (
                        <td key={a} className={`heatmap-cell ${cellClass}`}>
                          <span>{fmt(t.zero_shot, 2)}</span>
                          {hasAdapted && (
                            <>
                              <span style={{ color: "var(--muted)", margin: "0 4px" }}>→</span>
                              <strong style={{ color: delta && delta > 0 ? "#34d399" : "#fb7185" }}>
                                {fmt(t.adapted, 2)}
                              </strong>
                              {delta !== null && (
                                <span
                                  style={{
                                    fontSize: 10,
                                    marginLeft: 6,
                                    opacity: 0.9,
                                    padding: "1px 4px",
                                    borderRadius: 3,
                                    background: delta >= 0 ? "rgba(16, 185, 129, 0.25)" : "rgba(244, 63, 94, 0.25)",
                                  }}
                                >
                                  {delta >= 0 ? "+" : ""}
                                  {fmt(delta, 2)}
                                </span>
                              )}
                            </>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted" style={{ marginTop: 12 }}>
              Zero-shot = performance with no further training; adapted = performance after a
              fixed interaction budget on the new morphology. Perturbations are evaluated
              zero-shot only. Color-coded indicators highlight adaptation gains (+green) or regression (-rose).
            </p>
          </div>
        </>
      )}
    </div>
  );
}

