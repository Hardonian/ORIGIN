// Thin client for the ORIGIN read API. The lab UI talks to the local Python
// service over loopback; every number shown comes from a persisted trial.

export const API_BASE =
  process.env.NEXT_PUBLIC_ORIGIN_API || "http://127.0.0.1:8788";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    let detail = "";
    try {
      detail = JSON.stringify(await res.json());
    } catch {
      /* ignore */
    }
    throw new Error(`API ${path} -> ${res.status} ${detail}`);
  }
  return (await res.json()) as T;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`API ${path} -> ${res.status} ${JSON.stringify(data)}`);
  return data as T;
}

export interface ExperimentSummary {
  id: string;
  name: string;
  protocol: string;
  status: string;
  created_at: number;
  git_sha?: string;
  summary: { n_trials: number; n_done: number; n_failed: number };
}

export interface Trial {
  id: string;
  experiment_id: string;
  algorithm: string;
  seed: number;
  status: string;
  interactions: number;
  budget: number;
  best_fitness: number | null;
  train_fitness: number | null;
  metrics_json: string | null;
  transfer_json: string | null;
  error: string | null;
}

export interface Comparison {
  experiment_id: string;
  n_done: number;
  comparison: Record<
    string,
    {
      n: number;
      test_mean_reward: number | null;
      test_std_reward: number;
      train_mean_fitness: number | null;
      mean_interactions: number;
      transfer: Record<
        string,
        { kind: string; zero_shot: number; adapted: number | null; adaptation_gain: number | null }
      >;
    }
  >;
}

export function parseJson<T>(s: string | null | undefined, fallback: T): T {
  if (!s) return fallback;
  try {
    return JSON.parse(s) as T;
  } catch {
    return fallback;
  }
}

export function fmt(x: number | null | undefined, digits = 3): string {
  return x === null || x === undefined || Number.isNaN(x) ? "—" : x.toFixed(digits);
}
