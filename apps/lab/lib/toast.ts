// Global toast notification event bus and state helper

export type ToastType = "success" | "error" | "info" | "warn";

export interface ToastMessage {
  id: string;
  message: string;
  type: ToastType;
}

export function showToast(message: string, type: ToastType = "info"): void {
  if (typeof window !== "undefined") {
    const event = new CustomEvent<ToastMessage>("origin_toast", {
      detail: {
        id: Math.random().toString(36).slice(2, 9),
        message,
        type,
      },
    });
    window.dispatchEvent(event);
  }
}
