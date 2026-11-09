// Thin client for the FastAPI backend.
// NEXT_PUBLIC_API_URL is inlined at build time, so set it before `npm run build`.

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number | null, // null = request never reached the server
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(`Could not reach the API at ${API_URL}`, null);
  }

  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body && typeof body.detail === "string" ? body.detail : res.statusText;
    throw new ApiError(detail, res.status);
  }
  return body as T;
}

export type HealthResponse = { status: "ok" };
export type DbHealthResponse = { status: "ok"; database: "reachable" };

export const api = {
  health: () => request<HealthResponse>("/health"),
  dbHealth: () => request<DbHealthResponse>("/health/db"),
};