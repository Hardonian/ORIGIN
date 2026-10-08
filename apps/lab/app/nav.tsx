"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { getAuthToken, setAuthToken } from "@/lib/api";

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

export default function Nav() {
  const path = usePathname();
  const [token, setToken] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [inputToken, setInputToken] = useState("");

  useEffect(() => {
    const cur = getAuthToken();
    setToken(cur);
    const handleAuthChange = () => setToken(getAuthToken());
    window.addEventListener("origin_auth_changed", handleAuthChange);
    return () => window.removeEventListener("origin_auth_changed", handleAuthChange);
  }, []);

  const handleSave = () => {
    setAuthToken(inputToken.trim() || null);
    setIsModalOpen(false);
  };

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
      <nav style={{ display: "flex", gap: 14, flexWrap: "wrap", alignItems: "center" }}>
        {LINKS.map(([href, label]) => (
          <Link key={href} href={href} className={path === href ? "active" : ""}>
            {label}
          </Link>
        ))}
      </nav>

      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
        <button
          onClick={() => {
            setInputToken(token);
            setIsModalOpen(true);
          }}
          style={{
            fontSize: 12,
            padding: "3px 8px",
            background: token ? "#132b1e" : "var(--panel2)",
            borderColor: token ? "var(--ok)" : "var(--border)",
            color: token ? "var(--ok)" : "var(--muted)",
          }}
          title="Configure API Token"
        >
          {token ? "🔒 Authenticated" : "🔓 Open / Local"}
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
            background: "rgba(0,0,0,0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
          }}
          onClick={() => setIsModalOpen(false)}
        >
          <div
            className="panel"
            style={{ width: 440, maxWidth: "90%", background: "var(--panel)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 style={{ marginTop: 0 }}>API Authentication Token</h2>
            <p className="sub">
              Enter your <code>ORIGIN_API_KEY</code> if connecting to a remote or secured ORIGIN instance.
            </p>
            <input
              type="password"
              placeholder="Paste secret token..."
              value={inputToken}
              onChange={(e) => setInputToken(e.target.value)}
              style={{ width: "100%", marginBottom: 14 }}
              autoFocus
            />
            <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}>
              {token && (
                <button
                  onClick={() => {
                    setAuthToken(null);
                    setIsModalOpen(false);
                  }}
                  style={{ color: "var(--err)" }}
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
