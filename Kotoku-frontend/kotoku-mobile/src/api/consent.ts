import { apiClient } from "@/api/client";
import type { ApiResponse } from "@/types/api";

export interface ConsentRecord {
  id: number;
  partyId: number;
  granted: boolean;
  expiresAt: string;
}

export async function requestOtp(
  agreementId: number,
  partyId: number,
): Promise<ConsentRecord> {
  const res = await apiClient.post<ApiResponse<ConsentRecord>>(
    `/agreements/${agreementId}/consent/request-otp/`,
    { party_id: partyId },
  );
  return res.data.data;
}

export async function confirmOtp(
  agreementId: number,
  consentRecordId: number,
  otpCode: string,
): Promise<ConsentRecord> {
  const res = await apiClient.post<ApiResponse<ConsentRecord>>(
    `/agreements/${agreementId}/consent/confirm/`,
    { consent_record_id: consentRecordId, otp_code: otpCode },
  );
  return res.data.data;
}

export async function getConsentStatus(
  agreementId: number,
): Promise<ConsentRecord[]> {
  const res = await apiClient.get<ApiResponse<ConsentRecord[]>>(
    `/agreements/${agreementId}/consent/`,
  );
  return res.data.data;
}
