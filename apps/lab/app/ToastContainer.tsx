"use client";

import { useEffect, useState } from "react";
import { ToastMessage } from "@/lib/toast";

export default function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    const handleToast = (e: Event) => {
      const customEvent = e as CustomEvent<ToastMessage>;
      if (!customEvent.detail) return;
      const newToast = customEvent.detail;
      setToasts((prev) => [...prev, newToast]);

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== newToast.id));
      }, 3500);
    };

    window.addEventListener("origin_toast", handleToast);
    return () => window.removeEventListener("origin_toast", handleToast);
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div
      style={{
        position: "fixed",
        bottom: 24,
        right: 24,
        zIndex: 99999,
        display: "flex",
        flexDirection: "column",
        gap: 8,
        maxWidth: 380,
      }}
    >
      {toasts.map((t) => {
        const bg =
          t.type === "success"
            ? "rgba(16, 185, 129, 0.15)"
            : t.type === "error"
            ? "rgba(244, 63, 94, 0.15)"
            : t.type === "warn"
            ? "rgba(245, 158, 11, 0.15)"
            : "rgba(79, 156, 249, 0.15)";
        const border =
          t.type === "success"
            ? "rgba(16, 185, 129, 0.4)"
            : t.type === "error"
            ? "rgba(244, 63, 94, 0.4)"
            : t.type === "warn"
            ? "rgba(245, 158, 11, 0.4)"
            : "rgba(79, 156, 249, 0.4)";
        const color =
          t.type === "success"
            ? "#34d399"
            : t.type === "error"
            ? "#fb7185"
            : t.type === "warn"
            ? "#fbbf24"
            : "#60a5fa";
        const icon =
          t.type === "success" ? "✓" : t.type === "error" ? "✕" : t.type === "warn" ? "⚠" : "ℹ";

        return (
          <div
            key={t.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "10px 14px",
              background: bg,
              backdropFilter: "blur(12px)",
              border: `1px solid ${border}`,
              borderRadius: 8,
              color: "#f3f4f6",
              fontSize: 13,
              boxShadow: "0 8px 32px rgba(0, 0, 0, 0.35)",
              animation: "toast-in 0.25s ease-out forwards",
            }}
          >
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 20,
                height: 20,
                borderRadius: "50%",
                background: border,
                color,
                fontWeight: "bold",
                fontSize: 12,
              }}
            >
              {icon}
            </span>
            <span style={{ flex: 1 }}>{t.message}</span>
            <button
              onClick={() => setToasts((prev) => prev.filter((item) => item.id !== t.id))}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--muted)",
                cursor: "pointer",
                padding: "0 4px",
                fontSize: 14,
              }}
            >
              ✕
            </button>
          </div>
        );
      })}
    </div>
  );
}
