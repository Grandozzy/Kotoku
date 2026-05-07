import axios from "axios";

import { API_BASE_URL } from "@/constants/config";
import { getToken, clearSession } from "@/lib/secureStore";

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  timeout: 30_000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach auth token to every request
apiClient.interceptors.request.use(async (config) => {
  const token = await getToken();
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

// Handle 401 — clear token and let the app redirect to auth
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      await clearSession();
    }
    return Promise.reject(error);
  }
);
