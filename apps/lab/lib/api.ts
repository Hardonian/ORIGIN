// Thin client for the ORIGIN read API. The lab UI talks to the local Python
// service over loopback; every number shown comes from a persisted trial.

export const API_BASE =
  process.env.NEXT_PUBLIC_ORIGIN_API || "http://127.0.0.1:8788";

const AUTH_STORAGE_KEY = "origin_api_key";
const API_TIMEOUT_MS = 15_000;

/** Structured request failure used by views that need to distinguish auth,
 * server, and connectivity failures without parsing an error string. */
export class ApiError extends Error {
  readonly status: number | null;
  readonly path: string;
  readonly detail: unknown;

  constructor(path: string, status: number | null, detail: unknown, message: string) {
    super(message);
    this.name = "ApiError";
    this.path = path;
    this.status = status;
    this.detail = detail;
  }

  get isUnauthorized(): boolean {
    return this.status === 401 || this.status === 403;
  }

  get isConnectivityFailure(): boolean {
    return this.status === null;
  }
}

export function getAuthToken(): string {
  if (typeof window !== "undefined") {
    const stored = window.localStorage.getItem(AUTH_STORAGE_KEY);
    if (stored) return stored;
  }
  return process.env.NEXT_PUBLIC_ORIGIN_API_KEY || "";
}

export function setAuthToken(token: string | null): void {
  if (typeof window !== "undefined") {
    if (token) {
      window.localStorage.setItem(AUTH_STORAGE_KEY, token);
    } else {
      window.localStorage.removeItem(AUTH_STORAGE_KEY);
    }
    window.dispatchEvent(new Event("origin_auth_changed"));
  }
}

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
      ...init,
      headers: {
        ...authHeaders(),
        ...init.headers,
      },
      signal: init.signal ?? controller.signal,
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      throw new ApiError(path, res.status, data, `API ${path} -> ${res.status} ${JSON.stringify(data ?? {})}`);
    }
    return data as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    const timedOut = error instanceof Error && error.name === "AbortError";
    const message = timedOut
      ? `API ${path} timed out after ${API_TIMEOUT_MS / 1000}s`
      : `API ${path} is unreachable`;
    throw new ApiError(path, null, error, message);
  } finally {
    clearTimeout(timeout);
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getExportUrl(experimentId?: string, format: "csv" | "json" = "csv"): string {
  const token = getAuthToken();
  const q = new URLSearchParams();
  if (experimentId) q.set("experiment", experimentId);
  q.set("format", format);
  if (token) q.set("token", token);
  return `${API_BASE}/api/export?${q.toString()}`;
}

export function getArtifactFileUrl(artifactId: number): string {
  const token = getAuthToken();
  const q = new URLSearchParams({ id: String(artifactId) });
  if (token) q.set("token", token);
  return `${API_BASE}/api/artifact-file?${q.toString()}`;
}

export interface LogResponse {
  file: string;
  lines: string[];
  total_lines: number;
}

export interface WorkerInfo {
  id: string;
  host: string;
  pid: number;
  started_at: number;
  last_heartbeat: number;
  heartbeat_age_seconds: number;
  status: string;
}

export interface WorkerReport {
  store: string;
  trial_counts: Record<string, number>;
  workers: WorkerInfo[];
}

export interface SystemCapabilities {
  version: string;
  status: string;
  auth_enabled: boolean;
  auth_required: boolean;
  simulators: string[];
  embodied_available: boolean;
  platform: string;
  python: string;
  cpus: number;
  store: string;
}

export interface CalibrationEvidence {
  available: boolean;
  valid: boolean;
  status: "not_run" | "unavailable" | "failed" | "passed" | "invalid";
  passed: boolean;
  file: string;
  message: string;
  command?: string;
  config_hash?: string | null;
  acceptance?: {
    minimum_forward_gain_m: number | null;
    duration_seconds: number | null;
    best_forward_gain_m: number | null;
  };
  gaits?: { program?: string; x_gain_m?: number; upright?: boolean }[];
  runtime?: Record<string, unknown>;
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

export interface RecordedTrajectoryFrame {
  step: number;
  time_s: number;
  base_pos: [number, number, number];
  base_orn: [number, number, number, number];
  joint_angles: number[];
  action: number;
  action_name: string;
  reward: number;
  cumulative_reward: number;
  distance_to_target: number;
  upright: boolean;
  success: boolean;
}

export interface RecordedTrajectory {
  experiment_id: string;
  trial_id: string;
  seed: number;
  morphology: string;
  n_links: number;
  link_length: number;
  link_radius: number;
  joint_axis: [number, number, number];
  target_distance: number;
  steps: number;
  total_reward: number;
  total_displacement_m: number;
  final_upright: boolean;
  success: boolean;
  trajectory: RecordedTrajectoryFrame[];
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
