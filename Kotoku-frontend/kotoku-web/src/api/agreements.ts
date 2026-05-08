import { api } from "@/lib/apiClient";
import type { Agreement, AgreementCreate } from "@/types/agreement";

export const agreementsApi = {
  list: () => api.get<{ results: Agreement[] }>("/api/agreements/"),

  get: (id: number) => api.get<Agreement>(`/api/agreements/${id}/`),

  create: (data: AgreementCreate) =>
    api.post<Agreement>("/api/agreements/", data),

  update: (id: number, data: Partial<AgreementCreate>) =>
    api.patch<Agreement>(`/api/agreements/${id}/`, data),

  requestConsent: (id: number) =>
    api.post<{ detail: string }>(`/api/agreements/${id}/consent/request/`),

  confirmConsent: (id: number, otp_code: string) =>
    api.post<{ detail: string }>(`/api/agreements/${id}/consent/confirm/`, {
      otp_code,
    }),
};
