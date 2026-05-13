import axios from "axios";

import { API_BASE_URL } from "@/constants/config";
import {
  clearSession,
  getRefreshToken,
  getToken,
  saveAccessToken,
} from "@/lib/secureStore";
import { useSessionStore } from "@/store/sessionStore";

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30_000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach JWT access token to every request
apiClient.interceptors.request.use(async (config) => {
  const token = await getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Mutex: prevents multiple concurrent 401s from each firing their own refresh
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refreshToken = await getRefreshToken();
    if (!refreshToken) return null;
    try {
      const res = await axios.post(`${API_BASE_URL}/api/auth/token/refresh/`, {
        refresh: refreshToken,
      });
      const newAccess: string = res.data?.data?.access ?? res.data?.access;
      await saveAccessToken(newAccess);
      // Keep in-memory store in sync
      useSessionStore.getState().setSession(newAccess, useSessionStore.getState().phone!, useSessionStore.getState().accountId!);
      return newAccess;
    } catch {
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

// On 401: try to refresh the access token and retry once. If refresh also
// fails, clear the session and let the router redirect to auth.
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retried) {
      originalRequest._retried = true;
      const newToken = await refreshAccessToken();
      if (newToken) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      }
      // Refresh failed — clear everything and force re-auth
      await clearSession();
      useSessionStore.getState().clearSession();
    }
    return Promise.reject(error);
  },
);
