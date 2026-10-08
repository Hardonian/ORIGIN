"use client";
import { useEffect, useState } from "react";
import { apiGet, Trial } from "@/lib/api";

export default function FailuresPage() {
  const [failures, setFailures] = useState<Trial[]>([]);
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

  return (
    <div>
      <h1>Failure inspector</h1>
      <p className="sub">
        Failed trials with diagnostic information. Failures are recorded, never silently
        dropped from benchmark summaries.
      </p>
      {err && <p className="err">{err}</p>}
      {loaded && failures.length === 0 && (
        <div className="panel">
          <p>No failed trials. Every recorded trial completed.</p>
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
                <th>error</th>
              </tr>
            </thead>
            <tbody>
              {failures.map((t) => (
                <tr key={t.id}>
                  <td>{t.id}</td>
                  <td className="muted">{t.experiment_id}</td>
                  <td>{t.algorithm}</td>
                  <td>{t.seed}</td>
                  <td className="err">{t.error}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
