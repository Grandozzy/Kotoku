import { apiClient } from "@/api/client";
import type { ApiResponse } from "@/types/api";

interface ReopenResponse {
  agreement_status: string;
}

export async function requestReopen(agreementId: number): Promise<ReopenResponse> {
  const res = await apiClient.post<ApiResponse<ReopenResponse>>(
    `/agreements/${agreementId}/reopen-request/`,
  );
  return res.data.data;
}

export async function requestReopenOtp(agreementId: number): Promise<void> {
  await apiClient.post(
    `/agreements/${agreementId}/reopen-consent/request-otp/`,
  );
}

interface ConfirmReopenResponse {
  granted: boolean;
  agreement_status: string;
}

export async function confirmReopenOtp(
  agreementId: number,
  phone: string,
  otpCode: string,
): Promise<ConfirmReopenResponse> {
  const res = await apiClient.post<ApiResponse<ConfirmReopenResponse>>(
    `/agreements/${agreementId}/reopen-consent/confirm/`,
    { phone, otp_code: otpCode },
  );
  return res.data.data;
}
