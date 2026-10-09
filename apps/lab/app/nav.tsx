"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { API_BASE, getAuthToken, setAuthToken } from "@/lib/api";
import { sfx } from "@/lib/sound";
import { showToast } from "@/lib/toast";

const LINKS = [
  ["/", "Overview"],
  ["/world", "World & Body"],
  ["/evolution", "Evolution"],
  ["/designer", "Designer"],
  ["/benchmark", "Benchmark"],
  ["/workers", "Workers & Cluster"],
  ["/artifacts", "Artifacts"],
  ["/failures", "Failures"],
] as const;

function subscribeToSoundChanges(onChange: () => void) {
  window.addEventListener("origin_sfx_changed", onChange);
  return () => window.removeEventListener("origin_sfx_changed", onChange);
}

function soundEnabledSnapshot() {
  return sfx.isEnabled();
}

export default function Nav() {
  const path = usePathname();
  const [token, setToken] = useState(() => (typeof window !== "undefined" ? getAuthToken() : ""));
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [inputToken, setInputToken] = useState("");
  const soundEnabled = useSyncExternalStore(subscribeToSoundChanges, soundEnabledSnapshot, () => false);
  const [isOnline, setIsOnline] = useState<boolean | null>(null);

  useEffect(() => {
    const handleAuthChange = () => setToken(getAuthToken());

    window.addEventListener("origin_auth_changed", handleAuthChange);

    // Initial and periodic health ping
    const checkPing = () => {
      fetch(`${API_BASE}/api/health`)
        .then((r) => setIsOnline(r.ok))
        .catch(() => setIsOnline(false));
    };
    checkPing();
    const interval = setInterval(checkPing, 10000);

    return () => {
      window.removeEventListener("origin_auth_changed", handleAuthChange);
      clearInterval(interval);
    };
  }, []);

  const handleSave = () => {
    setAuthToken(inputToken.trim() || null);
    setIsModalOpen(false);
    sfx.success();
    showToast(inputToken.trim() ? "API token saved" : "API token cleared", "success");
  };

  const toggleSound = () => {
    const next = !soundEnabled;
    sfx.setEnabled(next);
    if (next) sfx.success();
    showToast(next ? "Sound FX Enabled" : "Sound FX Muted", "info");
  };

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
      <nav style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        {LINKS.map(([href, label]) => (
          <Link
            key={href}
            href={href}
            className={path === href ? "active" : ""}
            aria-current={path === href ? "page" : undefined}
            onClick={() => sfx.click()}
          >
            {label}
          </Link>
        ))}
      </nav>

      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
        {/* Live cluster status ping */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 12,
            color: isOnline ? "var(--ok)" : isOnline === false ? "var(--err)" : "var(--muted)",
            background: "rgba(0, 0, 0, 0.2)",
            padding: "3px 8px",
            borderRadius: 6,
            border: "1px solid var(--border)",
          }}
          title={isOnline ? "Connected to backend API" : "Backend offline or unreachable"}
          role="status"
          aria-live="polite"
        >
          <span
            aria-hidden="true"
            className={isOnline ? "pulse-dot" : ""}
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: isOnline ? "var(--ok)" : isOnline === false ? "var(--err)" : "var(--muted)",
            }}
          />
          <span>{isOnline ? "LIVE" : isOnline === false ? "OFFLINE" : "CONNECTING"}</span>
        </div>

        {/* SFX audio toggle */}
        <button
          onClick={toggleSound}
          aria-pressed={soundEnabled}
          aria-label={soundEnabled ? "Mute interactive audio effects" : "Enable interactive sound effects"}
          style={{
            fontSize: 13,
            padding: "4px 8px",
            background: soundEnabled ? "rgba(0, 240, 255, 0.12)" : "var(--panel2)",
            borderColor: soundEnabled ? "var(--accent)" : "var(--border)",
            color: soundEnabled ? "var(--accent)" : "var(--muted)",
          }}
          title={soundEnabled ? "Mute interactive audio effects" : "Enable interactive sound effects"}
        >
          {soundEnabled ? "🔊 SFX" : "🔇 SFX"}
        </button>

        {/* Auth status trigger */}
        <button
          onClick={() => {
            setInputToken(token);
            setIsModalOpen(true);
            sfx.click();
          }}
          style={{
            fontSize: 12,
            padding: "4px 10px",
            background: token ? "rgba(16, 185, 129, 0.12)" : "var(--panel2)",
            borderColor: token ? "var(--ok)" : "var(--border)",
            color: token ? "var(--ok)" : "var(--muted)",
          }}
          title="Configure API Token"
          aria-haspopup="dialog"
          aria-expanded={isModalOpen}
        >
          {token ? "🔒 Auth Token" : "🔓 Open"}
        </button>
      </div>

      {isModalOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
          }}
          onClick={() => setIsModalOpen(false)}
          role="presentation"
        >
          <div
            className="panel panel-glow"
            style={{ width: 460, maxWidth: "90%", background: "var(--panel)" }}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="api-auth-title"
          >
            <h2 id="api-auth-title" style={{ marginTop: 0, color: "#fff" }}>API Authentication Token</h2>
            <p className="sub">
              Enter your <code>ORIGIN_API_KEY</code> if connecting to a remote or secured ORIGIN instance.
            </p>
            <input
              type="password"
              placeholder="Paste secret token..."
              aria-label="API authentication token"
              value={inputToken}
              onChange={(e) => setInputToken(e.target.value)}
              style={{ width: "100%", marginBottom: 16 }}
              autoFocus
            />
            <div className="row" style={{ justifyContent: "flex-end", gap: 10 }}>
              {token && (
                <button
                  onClick={() => {
                    setAuthToken(null);
                    setIsModalOpen(false);
                    showToast("Token cleared", "info");
                  }}
                  style={{ color: "var(--err)", borderColor: "rgba(244, 63, 94, 0.4)" }}
                  aria-label="Clear saved API token"
                >
                  Clear Token
                </button>
              )}
              <button onClick={() => setIsModalOpen(false)}>Cancel</button>
              <button className="primary" onClick={handleSave}>
                Save Token
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
