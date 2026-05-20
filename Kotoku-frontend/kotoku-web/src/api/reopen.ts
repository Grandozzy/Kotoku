import { api } from "@/lib/apiClient";
import type { Agreement } from "@/types/agreement";

export const reopenApi = {
  request: (agreementId: number) =>
    api.post<{ agreement: Agreement }>(
      `/api/agreements/${agreementId}/reopen-request/`
    ),

  requestOtp: (agreementId: number) =>
    api.post<{ detail: string }>(
      `/api/agreements/${agreementId}/reopen-consent/request-otp/`
    ),

  confirm: (agreementId: number, phone: string, otp_code: string) =>
    api.post<{ granted: boolean; agreement_status: string }>(
      `/api/agreements/${agreementId}/reopen-consent/confirm/`,
      { phone, otp_code }
    ),
};
