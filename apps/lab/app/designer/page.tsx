"use client";
import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost, LogResponse } from "@/lib/api";
import { sfx } from "@/lib/sound";
import { showToast } from "@/lib/toast";

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

  // Real-time JSON validation
  const validationStatus = useMemo(() => {
    if (!text.trim()) {
      return { valid: false, error: "Empty configuration", keys: 0 };
    }
    try {
      const obj = JSON.parse(text);
      if (typeof obj !== "object" || obj === null || Array.isArray(obj)) {
        return { valid: false, error: "Root must be a JSON object", keys: 0 };
      }
      return { valid: true, error: null, keys: Object.keys(obj).length };
    } catch (e: unknown) {
      return { valid: false, error: e instanceof Error ? e.message : String(e), keys: 0 };
    }
  }, [text]);

  function pick(i: number) {
    sfx.blip();
    setSel(i);
    setText(JSON.stringify(protocols[i].config, null, 2));
    setMsg(null);
    setErr(null);
  }

  function copyConfig() {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      sfx.blip();
      showToast("Configuration copied to clipboard!", "success");
    }
  }

  function resetPreset() {
    sfx.toggle();
    if (protocols[sel]) {
      setText(JSON.stringify(protocols[sel].config, null, 2));
      showToast("Reset configuration to protocol defaults.");
    }
  }

  async function launch() {
    if (!validationStatus.valid) {
      sfx.error();
      showToast(`Invalid JSON configuration: ${validationStatus.error}`, "error");
      return;
    }

    sfx.laser();
    setBusy(true);
    setMsg(null);
    setErr(null);
    try {
      const cfg = JSON.parse(text);
      const res = await apiPost<{ launched: boolean; config: string; log: string }>(
        "/api/experiments",
        cfg
      );
      sfx.tierUp();
      const successMsg = `Launched. Config: ${res.config} · log: ${res.log}`;
      setMsg(successMsg);
      showToast("Experiment launched! Streaming logs...", "success");
      setShowLogs(true);
      setPollingLogs(true);
    } catch (e: unknown) {
      sfx.error();
      const errMsg = e instanceof Error ? e.message : String(e);
      setErr(errMsg);
      showToast(`Launch failed: ${errMsg}`, "error");
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
        <div className="row" style={{ flexWrap: "wrap", gap: 10 }}>
          <label>protocol</label>
          <select value={sel} onChange={(e) => pick(Number(e.target.value))}>
            {protocols.map((p, i) => (
              <option key={p.file} value={i}>
                {p.name} — {p.protocol} (budget {p.budget})
              </option>
            ))}
          </select>
          <button
            className="primary"
            onClick={launch}
            disabled={busy || !validationStatus.valid}
          >
            {busy ? "launching…" : "🚀 Launch experiment"}
          </button>
          <button
            onClick={() => {
              sfx.toggle();
              setShowLogs((prev) => !prev);
              setPollingLogs((prev) => !prev);
            }}
          >
            {showLogs ? "Hide logs" : "View launched logs"}
          </button>
        </div>
        {protocols[sel] && <p className="muted" style={{ marginTop: 8 }}>{protocols[sel].description}</p>}
      </div>

      {msg && <div className="panel" style={{ borderColor: "var(--ok)" }}><p>{msg}</p></div>}
      {err && <div className="panel" style={{ borderColor: "var(--err)" }}><p className="err">{err}</p></div>}

      {showLogs && (
        <div className="panel">
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
            <div className="row" style={{ gap: 8, alignItems: "center" }}>
              <h2 style={{ margin: 0 }}>Live Execution Log (launched.log)</h2>
              <span className="pulse-dot" style={{ width: 6, height: 6 }} />
            </div>
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
                onClick={() => {
                  sfx.click();
                  apiGet<LogResponse>("/api/logs?file=launched.log&lines=60").then((r) =>
                    setLogLines(r.lines || [])
                  );
                }}
              >
                Refresh
              </button>
            </div>
          </div>
          <div
            style={{
              background: "#05090f",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: 12,
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 12,
              maxHeight: 280,
              overflowY: "auto",
              whiteSpace: "pre-wrap",
              color: "#38bdf8",
              boxShadow: "inset 0 0 16px rgba(0, 0, 0, 0.8)",
            }}
          >
            {logLines.length === 0
              ? "(No log entries recorded yet)"
              : logLines.map((line, idx) => <div key={idx}>{line}</div>)}
          </div>
        </div>
      )}

      <div className="panel">
        <div className="row" style={{ justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <div className="row" style={{ gap: 8, alignItems: "center" }}>
            <h2 style={{ margin: 0 }}>Configuration (JSON)</h2>
            {validationStatus.valid ? (
              <span className="badge done">
                ✓ Valid JSON ({validationStatus.keys} root properties)
              </span>
            ) : (
              <span className="badge failed">
                ⚠ {validationStatus.error}
              </span>
            )}
          </div>
          <div className="row" style={{ gap: 6 }}>
            <button onClick={copyConfig} style={{ fontSize: 11, padding: "3px 8px" }}>
              📋 Copy JSON
            </button>
            <button onClick={resetPreset} style={{ fontSize: 11, padding: "3px 8px" }}>
              ↺ Reset
            </button>
          </div>
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          spellCheck={false}
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 13,
            borderColor: validationStatus.valid ? "var(--border)" : "rgba(244, 63, 94, 0.6)",
          }}
        />
      </div>
      <p className="muted">
        Launches run in the background on the lab host under a 2-worker bound. Use
        Overview / Failures to observe progress.
      </p>
    </div>
  );
}

