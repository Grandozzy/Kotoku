import { api } from "@/lib/apiClient";

export const authApi = {
  requestOtp: (phone: string) =>
    api.post<{ detail: string }>("/api/auth/otp/request/", { phone }),

  verifyOtp: (phone: string, code: string) =>
    api.post<{ token: string; account_id: number }>(
      "/api/auth/otp/verify/",
      { phone, code }
    ),
};
