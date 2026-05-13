import { useSessionStore } from "@/store/sessionStore";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Mutex: if a refresh is already in flight, queue behind it instead of
// firing duplicate refresh requests.
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const { refreshToken, setAccessToken, clearSession } = useSessionStore.getState();
    if (!refreshToken) {
      clearSession();
      return null;
    }
    try {
      const res = await fetch(`${BASE_URL}/api/auth/token/refresh/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: refreshToken }),
      });
      if (!res.ok) {
        clearSession();
        return null;
      }
      const body = await res.json();
      // simplejwt with ROTATE_REFRESH_TOKENS returns a new access + refresh
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
    ...(options.headers as Record<string, string> ?? {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

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
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: "POST", body: data ? JSON.stringify(data) : undefined }),
  patch: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(data) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
