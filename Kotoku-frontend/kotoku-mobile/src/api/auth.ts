import { apiClient } from "@/api/client";
import type { ApiResponse } from "@/types/api";

// ---------- Payloads & results ----------

export interface SendOtpPayload {
  phone: string;
}

export interface SendOtpResult {
  message: string;
}

export interface VerifyOtpPayload {
  phone: string;
  code: string;
}

export interface VerifyOtpResult {
  token: string;
  account_id: number;
}

export interface MeResult {
  id: number;
  phone: string;
  email: string | null;
  full_name: string | null;
  member_since: string | null;
}

export interface UpdateProfilePayload {
  full_name?: string;
  email?: string;
}

// ---------- API functions ----------

export async function sendOtp(payload: SendOtpPayload): Promise<SendOtpResult> {
  const res = await apiClient.post<ApiResponse<SendOtpResult>>(
    "/auth/send-otp/",
    payload,
  );
  return res.data.data;
}

export async function verifyOtp(
  payload: VerifyOtpPayload,
): Promise<VerifyOtpResult> {
  const res = await apiClient.post<ApiResponse<VerifyOtpResult>>(
    "/auth/verify-otp/",
    { phone: payload.phone, otp_code: payload.code },
  );
  return res.data.data;
}

export async function fetchMe(): Promise<MeResult> {
  const res = await apiClient.get<ApiResponse<MeResult>>("/me/");
  return res.data.data;
}

export async function updateProfile(payload: UpdateProfilePayload): Promise<MeResult> {
  const res = await apiClient.patch<ApiResponse<MeResult>>("/me/", payload);
  return res.data.data;
}
