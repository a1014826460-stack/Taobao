export type User = { id: number; email: string; trial_successes_remaining: number; is_formal: boolean };
export type CredentialProfile = { id: number; name: string; platform: string; purpose: string | null; created_at: string };
export type ProxyProfile = { id: number; name: string; protocol: string; host: string; port: number; created_at: string };
export type Job = { id: number; crawler: string; status: "queued" | "running" | "succeeded" | "failed" | "cancelled"; error_code: string | null; error_message: string | null; created_at: string };

export class ApiError extends Error {
  constructor(public status: number, public code: string) { super(code); }
}

const jsonHeaders = { "Content-Type": "application/json" };

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers: { ...jsonHeaders, ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(response.status, body.detail || "REQUEST_FAILED");
  return body as T;
}

export const api = {
  register: (email: string, password: string) => request<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) => request<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  credentials: (token: string) => request<CredentialProfile[]>("/profiles/credentials", {}, token),
  proxies: (token: string) => request<ProxyProfile[]>("/profiles/proxies", {}, token),
  createCredential: (token: string, body: { name: string; platform: string; purpose?: string; cookie: string }) => request<CredentialProfile>("/profiles/credentials", { method: "POST", body: JSON.stringify(body) }, token),
  createProxy: (token: string, body: { name: string; protocol: string; host: string; port: number; username?: string; password?: string }) => request<ProxyProfile>("/profiles/proxies", { method: "POST", body: JSON.stringify(body) }, token),
  submit: (token: string, crawler: string, body: { input: Record<string, unknown>; credential_profile_id?: number; proxy_profile_id?: number }) => request<Job>(`/crawls/${crawler}`, { method: "POST", body: JSON.stringify(body) }, token),
  job: (token: string, id: number) => request<Job>(`/jobs/${id}`, {}, token),
  result: (token: string, id: number) => request<{ id: number; status: string; result: Record<string, unknown> }>(`/jobs/${id}/result`, {}, token),
};
