"use client";
import { useEffect, useState } from "react";
import { apiGet, ExperimentSummary, parseJson, Trial } from "@/lib/api";
import { sfx } from "@/lib/sound";

interface Metrics {
  descriptor_spread?: number;
  n_generations?: number;
  history?: Record<string, number>[];
  algorithm_extra?: Record<string, unknown>;
}

interface TierInfo {
  name: string;
  badgeClass: string;
  icon: string;
}

function getTier(fitness: number, maxFit: number): TierInfo {
  if (maxFit <= 0) {
    return { name: "Embryonic Mutator", badgeClass: "tier-embryonic", icon: "🧬" };
  }
  const ratio = fitness / maxFit;
  if (ratio >= 0.75) {
    return { name: "Apex Controller", badgeClass: "tier-apex", icon: "👑" };
  }
  if (ratio >= 0.4) {
    return { name: "Adaptive Specialist", badgeClass: "tier-adaptive", icon: "⚡" };
  }
  return { name: "Embryonic Mutator", badgeClass: "tier-embryonic", icon: "🧬" };
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

  const handleExpChange = (newId: string) => {
    sfx.blip();
    setExpId(newId);
  };

  const byAlgo: Record<string, Trial[]> = {};
  trials.forEach((t) => {
    (byAlgo[t.algorithm] ||= []).push(t);
  });
  const maxFit = Math.max(1e-9, ...trials.map((t) => t.best_fitness ?? 0));

  // Determine top champion algorithm
  let bestAlgo = "";
  let bestAlgoMean = -Infinity;
  Object.entries(byAlgo).forEach(([algo, ts]) => {
    const fits = ts.map((t) => t.best_fitness ?? 0);
    const mean = fits.reduce((a, b) => a + b, 0) / Math.max(1, fits.length);
    if (mean > bestAlgoMean) {
      bestAlgoMean = mean;
      bestAlgo = algo;
    }
  });

  return (
    <div>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
        <div>
          <h1>Evolution explorer</h1>
          <p className="sub" style={{ margin: 0 }}>
            Fitness distributions across independent seeds and behavioural-descriptor spread per
            method. Populations are categorised into evolutionary tiers based on optimization depth.
          </p>
        </div>
      </div>
      {err && <p className="err">{err}</p>}

      <div className="panel">
        <div className="row">
          <label>experiment</label>
          <select value={expId} onChange={(e) => handleExpChange(e.target.value)}>
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
        const spread =
          ts
            .map((t) => parseJson<Metrics>(t.metrics_json, {}).descriptor_spread ?? 0)
            .reduce((a, b) => a + b, 0) / Math.max(1, ts.length);
        const gens = ts.map((t) => parseJson<Metrics>(t.metrics_json, {}).n_generations ?? 0);
        const meanGens = Math.round(gens.reduce((a, b) => a + b, 0) / Math.max(1, gens.length));
        const totalInteractions = ts.reduce((a, b) => a + (b.interactions ?? 0), 0);
        const meanInteractions = totalInteractions / Math.max(1, ts.length);
        const evoVelocity =
          meanInteractions > 0 ? ((mean / meanInteractions) * 1000).toFixed(4) : "0.0000";

        const isChampion = algo === bestAlgo && ts.length > 0;

        return (
          <div
            className="panel"
            key={algo}
            style={{
              borderColor: isChampion ? "rgba(245, 158, 11, 0.45)" : "var(--border)",
              boxShadow: isChampion ? "0 0 20px rgba(245, 158, 11, 0.08)" : "none",
            }}
          >
            <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div className="row" style={{ gap: 10, alignItems: "center" }}>
                <h2 style={{ margin: 0 }}>{algo}</h2>
                {isChampion && (
                  <span className="tier-badge tier-apex">
                    👑 Top Algorithm Champion
                  </span>
                )}
              </div>
              <span className="muted" style={{ fontSize: 12 }}>
                {ts.length} completed {ts.length === 1 ? "trial" : "trials"}
              </span>
            </div>

            {/* Algorithm Telemetry Scorecard */}
            <div className="metric-grid" style={{ marginBottom: 14 }}>
              <div>
                <span>Mean Fitness</span>
                <strong style={{ color: "var(--accent)", fontSize: 16 }}>{mean.toFixed(3)}</strong>
              </div>
              <div>
                <span>Behavioral Diversity</span>
                <strong style={{ color: "var(--ok)", fontSize: 16 }}>{spread.toFixed(4)}</strong>
              </div>
              <div>
                <span>Mean Generations</span>
                <strong style={{ fontSize: 16 }}>{meanGens}</strong>
              </div>
              <div>
                <span>Evo Velocity (Fit/1k)</span>
                <strong style={{ color: "#c084fc", fontSize: 16 }}>{evoVelocity}</strong>
              </div>
            </div>

            <table>
              <thead>
                <tr>
                  <th>seed</th>
                  <th>evolutionary tier</th>
                  <th>best fitness</th>
                  <th>generations</th>
                  <th>interactions</th>
                  <th>fitness spectrum</th>
                </tr>
              </thead>
              <tbody>
                {ts.map((t, i) => {
                  const fit = t.best_fitness ?? 0;
                  const tier = getTier(fit, maxFit);
                  const barWidth = `${(Math.max(0, fit) / maxFit) * 100}%`;

                  return (
                    <tr key={t.id}>
                      <td>
                        <code>seed {t.seed}</code>
                      </td>
                      <td>
                        <span className={`tier-badge ${tier.badgeClass}`}>
                          {tier.icon} {tier.name}
                        </span>
                      </td>
                      <td style={{ fontFamily: "JetBrains Mono, monospace", fontWeight: 600 }}>
                        {fit.toFixed(3)}
                      </td>
                      <td>{gens[i]}</td>
                      <td style={{ fontFamily: "JetBrains Mono, monospace" }}>
                        {(t.interactions ?? 0).toLocaleString()}
                      </td>
                      <td style={{ width: "35%" }}>
                        <div
                          style={{
                            background: "rgba(255, 255, 255, 0.08)",
                            borderRadius: 4,
                            overflow: "hidden",
                            height: 10,
                          }}
                        >
                          <div
                            style={{
                              width: barWidth,
                              height: "100%",
                              background:
                                fit >= 0.75 * maxFit
                                  ? "linear-gradient(90deg, #f59e0b, #fbbf24)"
                                  : fit >= 0.4 * maxFit
                                  ? "linear-gradient(90deg, #8b5cf6, #00f0ff)"
                                  : "linear-gradient(90deg, #0ea5e9, #38bdf8)",
                              boxShadow:
                                fit >= 0.75 * maxFit
                                  ? "0 0 8px rgba(245, 158, 11, 0.5)"
                                  : "0 0 6px rgba(0, 240, 255, 0.3)",
                              transition: "width 0.4s ease",
                            }}
                          />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}

