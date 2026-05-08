import { api } from "@/lib/apiClient";
import type { ConsentStatus } from "@/types/consent";

export const consentApi = {
  requestOtps: (agreementId: number) =>
    api.post<{ detail: string }>(`/api/agreements/${agreementId}/consent/request/`),

  confirm: (agreementId: number, party_phone: string, otp_code: string) =>
    api.post<{ detail: string }>(`/api/agreements/${agreementId}/consent/confirm/`, {
      party_phone,
      otp_code,
    }),

  status: (agreementId: number) =>
    api.get<ConsentStatus>(`/api/agreements/${agreementId}/consent/status/`),
};
