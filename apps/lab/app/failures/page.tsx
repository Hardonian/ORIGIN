"use client";
import { useEffect, useMemo, useState } from "react";
import { apiGet, Trial } from "@/lib/api";
import { sfx } from "@/lib/sound";
import { toast } from "@/lib/toast";

export default function FailuresPage() {
  const [failures, setFailures] = useState<Trial[]>([]);
  const [search, setSearch] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    apiGet<Trial[]>("/api/failures")
      .then((d) => {
        setFailures(d);
        setLoaded(true);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  const filtered = useMemo(() => {
    if (!search.trim()) return failures;
    const q = search.toLowerCase();
    return failures.filter(
      (f) =>
        f.id.toLowerCase().includes(q) ||
        f.experiment_id.toLowerCase().includes(q) ||
        f.algorithm.toLowerCase().includes(q) ||
        (f.error && f.error.toLowerCase().includes(q))
    );
  }, [failures, search]);

  const copyError = (errorText: string | null) => {
    if (!errorText) return;
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(errorText);
      sfx.blip();
      toast.info("Error trace copied to clipboard.");
    }
  };

  return (
    <div>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div>
          <h1>Failure inspector</h1>
          <p className="sub" style={{ margin: 0 }}>
            Failed trials with diagnostic information. Failures are recorded, never silently
            dropped from benchmark summaries.
          </p>
        </div>
        {failures.length > 0 && (
          <input
            type="text"
            placeholder="Search failures..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 200, fontSize: 12 }}
          />
        )}
      </div>

      {err && <p className="err">{err}</p>}

      {loaded && failures.length === 0 && (
        <div
          className="panel"
          style={{
            borderColor: "rgba(16, 185, 129, 0.4)",
            background: "linear-gradient(135deg, rgba(16, 185, 129, 0.08), transparent)",
            padding: 24,
            textAlign: "center",
          }}
        >
          <div style={{ fontSize: 32, marginBottom: 8 }}>🛡️</div>
          <h2 style={{ margin: "0 0 6px 0", color: "#34d399" }}>Zero Failures Recorded</h2>
          <p className="muted" style={{ margin: 0 }}>
            No failed trials. All executed trials across active experiments completed nominally without runtime halts or timeouts.
          </p>
        </div>
      )}

      {failures.length > 0 && (
        <div className="panel">
          <table>
            <thead>
              <tr>
                <th>trial</th>
                <th>experiment</th>
                <th>algorithm</th>
                <th>seed</th>
                <th>diagnostic error</th>
                <th>action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((t) => (
                <tr key={t.id}>
                  <td>
                    <code>{t.id}</code>
                  </td>
                  <td className="muted">{t.experiment_id}</td>
                  <td>
                    <strong>{t.algorithm}</strong>
                  </td>
                  <td>seed {t.seed}</td>
                  <td className="err" style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 12 }}>
                    {t.error}
                  </td>
                  <td>
                    <button
                      onClick={() => copyError(t.error)}
                      style={{ fontSize: 11, padding: "2px 8px" }}
                      title="Copy error trace"
                    >
                      Copy Trace
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

