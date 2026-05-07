import { apiClient } from "@/api/client";
import type { ApiResponse } from "@/types/api";

export interface ConsentRecord {
  id: number;
  partyId: number;
  partyPhone: string;
  granted: boolean;
  grantedAt: string | null;
  expiresAt: string;
}

export interface RequestOtpResponse {
  consentRecords: ConsentRecord[];
  partiesCount: number;
}

export async function requestOtp(
  agreementId: number,
): Promise<RequestOtpResponse> {
  const res = await apiClient.post<ApiResponse<RequestOtpResponse>>(
    `/agreements/${agreementId}/consent/request-otp/`,
  );
  return res.data.data;
}

export async function confirmOtp(
  agreementId: number,
  partyPhone: string,
  otpCode: string,
): Promise<ConsentRecord> {
  const res = await apiClient.post<ApiResponse<{ consentRecord: ConsentRecord }>>(
    `/agreements/${agreementId}/consent/confirm/`,
    { party_phone: partyPhone, otp_code: otpCode },
  );
  return res.data.data.consentRecord;
}

export interface ConsentStatus {
  agreementId: number;
  allConsented: boolean;
  records: ConsentRecord[];
}

export async function getConsentStatus(
  agreementId: number,
): Promise<ConsentStatus> {
  const res = await apiClient.get<ApiResponse<ConsentStatus>>(
    `/agreements/${agreementId}/consent/status/`,
  );
  return res.data.data;
}
