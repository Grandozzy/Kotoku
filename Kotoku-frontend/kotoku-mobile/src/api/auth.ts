import { apiClient } from "@/api/client";
import type { ApiResponse } from "@/types/api";

// ---------- Shared auth result shape ----------

export interface AuthUser {
  id: number;
  phone: string;
  pin_configured: boolean;
  account_id: number;
}

export interface AuthResult {
  access: string;
  refresh: string;
  session_id: string;
  user: AuthUser;
}

// ---------- OTP ----------

export interface SendOtpPayload {
  phone: string;
}

export interface SendOtpResult {
  message: string;
  expires_in_seconds: number;
}

export interface VerifyOtpPayload {
  phone: string;
  code: string;
}

// ---------- Token refresh ----------

export interface RefreshPayload {
  refresh: string;
}

// ---------- PIN ----------

export interface PinSetupResult {
  pin_configured: boolean;
}

export interface PinVerifyPayload {
  phone: string;
  pin: string;
}

export interface PinVerifyError {
  force_otp?: boolean;
  detail?: string;
}

// ---------- Profile ----------

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
  const res = await apiClient.post<ApiResponse<SendOtpResult>>("/auth/send-otp/", payload);
  return res.data.data;
}

export async function verifyOtp(payload: VerifyOtpPayload): Promise<AuthResult> {
  const res = await apiClient.post<ApiResponse<AuthResult>>(
    "/auth/verify-otp/",
    { phone: payload.phone, otp_code: payload.code },
  );
  return res.data.data;
}

export async function refreshTokens(payload: RefreshPayload): Promise<AuthResult> {
  const res = await apiClient.post<ApiResponse<AuthResult>>(
    "/auth/token/refresh/",
    payload,
  );
  return res.data.data;
}

export async function setupPin(pin: string): Promise<PinSetupResult> {
  const res = await apiClient.post<ApiResponse<PinSetupResult>>("/auth/pin/setup/", { pin });
  return res.data.data;
}

export async function verifyPin(payload: PinVerifyPayload): Promise<AuthResult> {
  const res = await apiClient.post<ApiResponse<AuthResult>>("/auth/pin/verify/", payload);
  return res.data.data;
}

export async function signOut(): Promise<void> {
  await apiClient.post("/auth/signout/", {});
}

export async function signOutAll(): Promise<void> {
  await apiClient.post("/auth/signout-all/", {});
}

export async function fetchMe(): Promise<MeResult> {
  const res = await apiClient.get<ApiResponse<MeResult>>("/me/");
  return res.data.data;
}

export async function updateProfile(payload: UpdateProfilePayload): Promise<MeResult> {
  const res = await apiClient.patch<ApiResponse<MeResult>>("/me/", payload);
  return res.data.data;
}
