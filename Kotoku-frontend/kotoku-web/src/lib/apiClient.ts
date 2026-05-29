import { useSessionStore } from "@/store/sessionStore";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
type ApiEnvelope<T> = { status: "ok"; data: T };

// Enforce HTTPS in production. If the env var is misconfigured as http://,
// tokens would flow in plaintext — fail loudly rather than silently.
if (
  process.env.NODE_ENV === "production" &&
  BASE_URL.startsWith("http://")
) {
  throw new Error(
    `[Kotoku] NEXT_PUBLIC_API_URL must use https:// in production.\n` +
    `Current value: "${BASE_URL}"`
  );
}

// Mutex: if a refresh is already in flight, queue behind it instead of
// firing duplicate refresh requests.
let refreshPromise: Promise<string | null> | null = null;

export async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const { setAccessToken, clearSession } = useSessionStore.getState();
    try {
      const res = await fetch(`${BASE_URL}/api/auth/token/refresh/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });
      if (!res.ok) {
        clearSession();
        return null;
      }
      const body = await res.json();
      const newAccess: string = body.data?.access ?? body.access;
      setAccessToken(newAccess);
      return newAccess;
    } catch {
      clearSession();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  _retry = true,
): Promise<T> {
  const token = useSessionStore.getState().accessToken;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Client-Type": "web",
    ...(options.headers as Record<string, string> ?? {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (res.status === 401 && _retry) {
    const newToken = await refreshAccessToken();
    if (newToken) return request<T>(path, options, false);
    // clearSession already called — let callers handle redirect
    throw Object.assign(new Error("Session expired"), { status: 401 });
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw Object.assign(
      new Error(body?.message ?? body?.detail ?? `HTTP ${res.status}`),
      { status: res.status, body },
    );
  }

  if (res.status === 204) return undefined as unknown as T;
  const body = (await res.json()) as T | ApiEnvelope<T>;
  if (
    body &&
    typeof body === "object" &&
    "status" in body &&
    "data" in body &&
    body.status === "ok"
  ) {
    return body.data;
  }
  return body as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: "POST", body: data ? JSON.stringify(data) : undefined }),
  patch: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(data) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
