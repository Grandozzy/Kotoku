import { api } from "@/lib/apiClient";
import type { ConsentStatus } from "@/types/consent";

export const consentApi = {
  requestOtps: (agreementId: number) =>
    api.post<{ consent_records: ConsentStatus["records"]; parties_count: number }>(
      `/api/agreements/${agreementId}/consent/request-otp/`
    ),

  confirm: (agreementId: number, party_phone: string, otp_code: string) =>
    api.post<{ consent_record: ConsentStatus["records"][number] }>(
      `/api/agreements/${agreementId}/consent/confirm/`,
      {
        party_phone,
        otp_code,
      }
    ),

  status: (agreementId: number) =>
    api.get<ConsentStatus>(`/api/agreements/${agreementId}/consent/status/`),
};
