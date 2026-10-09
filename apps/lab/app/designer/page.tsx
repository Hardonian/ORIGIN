"use client";
import { useEffect, useState } from "react";
import { apiGet, apiPost, LogResponse } from "@/lib/api";

interface Protocol {
  file: string;
  name: string;
  protocol: string;
  budget: number;
  description: string;
  config: Record<string, unknown>;
}

export default function DesignerPage() {
  const [protocols, setProtocols] = useState<Protocol[]>([]);
  const [sel, setSel] = useState(0);
  const [text, setText] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [showLogs, setShowLogs] = useState(false);
  const [pollingLogs, setPollingLogs] = useState(false);

  useEffect(() => {
    apiGet<Protocol[]>("/api/protocols")
      .then((p) => {
        setProtocols(p);
        if (p.length) setText(JSON.stringify(p[0].config, null, 2));
      })
      .catch((e) => setErr(String(e)));
  }, []);

  useEffect(() => {
    if (!pollingLogs) return;
    const fetchLogs = () => {
      apiGet<LogResponse>("/api/logs?file=launched.log&lines=60")
        .then((res) => {
          setLogLines(res.lines || []);
        })
        .catch(() => {
          /* ignore log read errors */
        });
    };
    fetchLogs();
    const interval = setInterval(fetchLogs, 2500);
    return () => clearInterval(interval);
  }, [pollingLogs]);

  function pick(i: number) {
    setSel(i);
    setText(JSON.stringify(protocols[i].config, null, 2));
    setMsg(null);
    setErr(null);
  }

  async function launch() {
    setBusy(true);
    setMsg(null);
    setErr(null);
    try {
      const cfg = JSON.parse(text);
      const res = await apiPost<{ launched: boolean; config: string; log: string }>(
        "/api/experiments",
        cfg
      );
      setMsg(`Launched. Config: ${res.config} · log: ${res.log}`);
      setShowLogs(true);
      setPollingLogs(true);
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Experiment designer</h1>
      <p className="sub">
        Select a research protocol, edit validated parameters, and launch a bounded
        experiment. The config is validated server-side (seed isolation, known algorithms,
        budget caps) before anything runs.
      </p>

      <div className="panel">
        <div className="row">
          <label>protocol</label>
          <select value={sel} onChange={(e) => pick(Number(e.target.value))}>
            {protocols.map((p, i) => (
              <option key={p.file} value={i}>
                {p.name} — {p.protocol} (budget {p.budget})
              </option>
            ))}
          </select>
          <button className="primary" onClick={launch} disabled={busy || !text}>
            {busy ? "launching…" : "Launch experiment"}
          </button>
          <button
            onClick={() => {
              setShowLogs((prev) => !prev);
              setPollingLogs((prev) => !prev);
            }}
          >
            {showLogs ? "Hide logs" : "View launched logs"}
          </button>
        </div>
        {protocols[sel] && <p className="muted" style={{ marginTop: 8 }}>{protocols[sel].description}</p>}
      </div>

      {msg && <div className="panel"><p>{msg}</p></div>}
      {err && <div className="panel"><p className="err">{err}</p></div>}

      {showLogs && (
        <div className="panel">
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
            <h2 style={{ margin: 0 }}>Live Execution Log (launched.log)</h2>
            <div className="row">
              <label style={{ fontSize: 12, display: "flex", alignItems: "center", gap: 6 }}>
                <input
                  type="checkbox"
                  checked={pollingLogs}
                  onChange={(e) => setPollingLogs(e.target.checked)}
                />
                Auto-refresh (2.5s)
              </label>
              <button
                style={{ fontSize: 12, padding: "2px 8px" }}
                onClick={() =>
                  apiGet<LogResponse>("/api/logs?file=launched.log&lines=60").then((r) =>
                    setLogLines(r.lines || [])
                  )
                }
              >
                Refresh
              </button>
            </div>
          </div>
          <div
            style={{
              background: "#080c10",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: 12,
              fontFamily: "monospace",
              fontSize: 12,
              maxHeight: 280,
              overflowY: "auto",
              whiteSpace: "pre-wrap",
              color: "#c9d1d9",
            }}
          >
            {logLines.length === 0
              ? "(No log entries recorded yet)"
              : logLines.map((line, idx) => <div key={idx}>{line}</div>)}
          </div>
        </div>
      )}

      <div className="panel">
        <h2>Configuration</h2>
        <textarea value={text} onChange={(e) => setText(e.target.value)} spellCheck={false} />
      </div>
      <p className="muted">
        Launches run in the background on the lab host under a 2-worker bound. Use
        Overview / Failures to observe progress.
      </p>
    </div>
  );
}
