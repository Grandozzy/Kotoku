import { apiClient } from "@/api/client";
import type { ApiResponse } from "@/types/api";

export interface ConsentRecord {
  id: number;
  partyId: number;
  partyPhone: string;
  channel?: string;
  granted: boolean;
  grantedAt: string | null;
  expiresAt: string;
  createdAt?: string;
}

interface RawConsentRecord {
  id: number;
  party_id: number;
  party_phone: string;
  channel?: string;
  granted: boolean;
  granted_at: string | null;
  expires_at: string;
  created_at?: string;
}

function mapConsentRecord(raw: RawConsentRecord): ConsentRecord {
  return {
    id: raw.id,
    partyId: raw.party_id,
    partyPhone: raw.party_phone,
    channel: raw.channel,
    granted: raw.granted,
    grantedAt: raw.granted_at,
    expiresAt: raw.expires_at,
    createdAt: raw.created_at,
  };
}

export interface RequestOtpResponse {
  consentRecords: ConsentRecord[];
  partiesCount: number;
}

export async function requestOtp(
  agreementId: number,
): Promise<RequestOtpResponse> {
  const res = await apiClient.post<ApiResponse<{
    consent_records: RawConsentRecord[];
    parties_count: number;
  }>>(
    `/agreements/${agreementId}/consent/request-otp/`,
  );
  return {
    consentRecords: res.data.data.consent_records.map(mapConsentRecord),
    partiesCount: res.data.data.parties_count,
  };
}

export async function confirmOtp(
  agreementId: number,
  partyPhone: string,
  otpCode: string,
): Promise<ConsentRecord> {
  const res = await apiClient.post<ApiResponse<{ consent_record: RawConsentRecord }>>(
    `/agreements/${agreementId}/consent/confirm/`,
    { party_phone: partyPhone, otp_code: otpCode },
  );
  return mapConsentRecord(res.data.data.consent_record);
}

export interface ConsentStatus {
  agreementId: number;
  allConsented: boolean;
  records: ConsentRecord[];
}

export async function getConsentStatus(
  agreementId: number,
): Promise<ConsentStatus> {
  const res = await apiClient.get<ApiResponse<{
    agreement_id: number;
    all_consented: boolean;
    records: RawConsentRecord[];
  }>>(
    `/agreements/${agreementId}/consent/status/`,
  );
  return {
    agreementId: res.data.data.agreement_id,
    allConsented: res.data.data.all_consented,
    records: res.data.data.records.map(mapConsentRecord),
  };
}
