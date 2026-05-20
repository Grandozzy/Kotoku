import { api } from "@/lib/apiClient";

interface VerifyOtpResponse {
  access: string;
  user: {
    id: number;
    phone: string;
    pin_configured: boolean;
    account_id: number | null;
  };
}

export const authApi = {
  requestOtp: (phone: string) =>
    api.post<{ message: string; expires_in_seconds: number }>("/api/auth/send-otp/", {
      phone,
    }),

  verifyOtp: (phone: string, code: string) =>
    api.post<VerifyOtpResponse>(
      "/api/auth/verify-otp/",
      { phone, otp_code: code }
    ),
};
