import * as Application from "expo-application";
import * as Crypto from "expo-crypto";
import * as Device from "expo-device";
import axios from "axios";
import { Platform } from "react-native";

import { API_BASE_URL } from "@/constants/config";
import {
  clearSession,
  getRefreshToken,
  getSessionId,
  saveTokens,
} from "@/lib/secureStore";
import { getToken } from "@/lib/secureStore";
import { useSessionStore } from "@/store/sessionStore";

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30_000,
  headers: {
    "Content-Type": "application/json",
    "X-Client-Type": "mobile",
  },
});

// ── Device fingerprint ────────────────────────────────────────────────────────

let _cachedFingerprint: string | null = null;
let _cachedDeviceName: string | null = null;

async function getDeviceFingerprint(): Promise<string> {
  if (_cachedFingerprint) return _cachedFingerprint;

  let androidId = "";
  if (Platform.OS === "android") {
    try {
      androidId = Application.getAndroidId() ?? "";
    } catch {
      androidId = "";
    }
  } else if (Platform.OS === "ios") {
    try {
      androidId = (await Application.getIosIdForVendorAsync()) ?? "";
    } catch {
      androidId = "";
    }
  }

  const raw = [
    Device.modelName ?? "",
    Device.osName ?? "",
    Device.osVersion ?? "",
    String(Device.deviceType ?? ""),
    Platform.OS,
    androidId,
  ].join("|");

  _cachedFingerprint = await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    raw,
  );
  return _cachedFingerprint;
}

async function getDeviceName(): Promise<string> {
  if (_cachedDeviceName) return _cachedDeviceName;
  _cachedDeviceName = [Device.modelName, Device.osName, Device.osVersion]
    .filter(Boolean)
    .join(" ");
  return _cachedDeviceName;
}

// ── Request interceptor — attach auth + device headers ────────────────────────

apiClient.interceptors.request.use(async (config) => {
  const token = await getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  try {
    const [fingerprint, deviceName] = await Promise.all([
      getDeviceFingerprint(),
      getDeviceName(),
    ]);
    config.headers["X-Device-Fingerprint"] = fingerprint;
    config.headers["X-Device-Name"] = deviceName;
  } catch {
    // Non-fatal: fingerprint enrichment should never block requests.
  }
  return config;
});

// ── Mutex refresh-on-401 ──────────────────────────────────────────────────────

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const [refreshToken, sessionId] = await Promise.all([
      getRefreshToken(),
      getSessionId(),
    ]);
    if (!refreshToken) return null;
    try {
      const res = await axios.post(
        `${API_BASE_URL}/api/auth/token/refresh/`,
        { refresh: refreshToken },
        {
          headers: {
            "Content-Type": "application/json",
            "X-Client-Type": "mobile",
          },
        },
      );
      const data = res.data?.data ?? res.data;
      const newAccess: string = data.access;
      const newRefresh: string = data.refresh;
      const newSessionId: string = data.session_id ?? sessionId ?? "";

      await saveTokens(newAccess, newRefresh, newSessionId);
      const store = useSessionStore.getState();
      store.setSession(newAccess, store.phone!, store.accountId!, store.pinConfigured);
      return newAccess;
    } catch {
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

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
      await clearSession();
      useSessionStore.getState().clearSession();
    }
    return Promise.reject(error);
  },
);
