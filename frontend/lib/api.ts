// Typed client for the FastAPI backend.
// NEXT_PUBLIC_API_URL is inlined at build time, so set it before `npm run build`.

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

// ---------- auth token ----------

const TOKEN_KEY = "sws_token";
export const LOGOUT_EVENT = "sws:logout";

// The token lives in localStorage and is sent as a Bearer header. Cookies won't work
// here: the frontend (Vercel) and API (Render) are different sites, and browsers
// block third-party cookies.
export const tokenStore = {
  get(): string | null {
    try {
      return window.localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string) {
    try {
      window.localStorage.setItem(TOKEN_KEY, token);
    } catch {
      // storage blocked (private mode): the session just won't survive a reload
    }
  },
  clear() {
    try {
      window.localStorage.removeItem(TOKEN_KEY);
    } catch {
      // ignore
    }
  },
};

// ---------- errors ----------

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number | null, // null = request never reached the server
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type ValidationItem = { loc?: (string | number)[]; msg?: string };

function errorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      // FastAPI 422: [{loc: ["body", "url"], msg: "..."}]
      const first = detail[0] as ValidationItem;
      const where = (first.loc ?? []).filter((p) => p !== "body").join(".");
      const msg = (first.msg ?? "Invalid input").replace(/^Value error, /, "");
      return where ? `${where}: ${msg}` : msg;
    }
  }
  return fallback;
}

// ---------- core request ----------

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && typeof init.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(`Could not reach the API at ${API_URL}`, null);
  }

  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && token) {
      tokenStore.clear();
      window.dispatchEvent(new Event(LOGOUT_EVENT));
    }
    throw new ApiError(errorMessage(body, res.statusText || `HTTP ${res.status}`), res.status);
  }
  return body as T;
}

const json = (method: string, data: unknown): RequestInit => ({ method, body: JSON.stringify(data) });

// ---------- types (mirror the backend's Pydantic schemas) ----------

export type HealthResponse = { status: "ok" };
export type DbHealthResponse = { status: "ok"; database: "reachable" };
export type WorkerHealthResponse = { status: "ok"; worker: "running" | "disabled"; queued: number };

export type User = {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
};

export const FIELD_TYPES = ["string", "number", "integer", "boolean", "string_list"] as const;
export type FieldType = (typeof FIELD_TYPES)[number];
export type FieldSpec = { type: FieldType; description: string };
export type Fields = Record<string, FieldSpec>;

export type Schema = {
  id: string;
  name: string;
  description: string | null;
  fields: Fields;
  version: number;
  created_at: string;
  updated_at: string;
};

export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export type JobSummary = {
  id: string;
  url: string;
  status: JobStatus;
  schema_id: string | null;
  render_js: boolean;
  attempts: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type JobResult = {
  data: Record<string, unknown>;
  is_valid: boolean;
  validation_errors: string[] | null;
  llm_model: string | null;
  final_url: string | null;
  page_title: string | null;
  fetch_method: "http" | "browser" | null;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number | null;
  created_at: string;
};

export type Job = JobSummary & { fields: Fields; result: JobResult | null };
export type JobPage = { items: JobSummary[]; total: number };
export type ModelUsage = {
  model: string;
  calls: number;
  failed_calls: number;
  input_tokens: number;
  output_tokens: number;
  avg_latency_ms: number;
};
export type UsageSummary = {
  jobs_by_status: Partial<Record<JobStatus, number>>;
  llm_calls: number;
  failed_llm_calls: number;
  input_tokens: number;
  output_tokens: number;
  fallback_used: number;
  by_model: ModelUsage[];
};
export type ActivityItem = {
  id: string;
  action: string;
  target_type: string | null;
  target_id: string | null;
  ip_address: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
};

export type NewJob = ({ url: string; schema_id: string } | { url: string; fields: Fields }) & { render_js?: boolean };

// ---------- endpoints ----------

export const api = {
  health: () => request<HealthResponse>("/health"),
  dbHealth: () => request<DbHealthResponse>("/health/db"),
  workerHealth: () => request<WorkerHealthResponse>("/health/worker"),

  register: (email: string, password: string, fullName?: string) =>
    request<User>("/auth/register", json("POST", { email, password, full_name: fullName || null })),

  async login(email: string, password: string): Promise<void> {
    // OAuth2 password flow: a form, with the email in the "username" field.
    const form = new URLSearchParams({ username: email, password });
    const { access_token } = await request<{ access_token: string }>("/auth/login", { method: "POST", body: form });
    tokenStore.set(access_token);
  },
  me: () => request<User>("/auth/me"),
  logout() {
    tokenStore.clear();
    window.dispatchEvent(new Event(LOGOUT_EVENT));
  },

  listSchemas: () => request<Schema[]>("/schemas"),
  createSchema: (body: { name: string; description?: string | null; fields: Fields }) =>
    request<Schema>("/schemas", json("POST", body)),
  updateSchema: (id: string, body: { name: string; description?: string | null; fields: Fields }) =>
    request<Schema>(`/schemas/${id}`, json("PUT", body)),
  deleteSchema: (id: string) => request<void>(`/schemas/${id}`, { method: "DELETE" }),

  createJob: (body: NewJob) => request<Job>("/jobs", json("POST", body)),
  listJobs: (limit = 20, offset = 0) => request<JobPage>(`/jobs?limit=${limit}&offset=${offset}`),
  getJob: (id: string) => request<Job>(`/jobs/${id}`),
  retryJob: (id: string) => request<Job>(`/jobs/${id}/retry`, { method: "POST" }),
  deleteJob: (id: string) => request<void>(`/jobs/${id}`, { method: "DELETE" }),

  usage: () => request<UsageSummary>("/usage"),
  activity: (limit = 50) => request<ActivityItem[]>(`/activity?limit=${limit}`),
};
