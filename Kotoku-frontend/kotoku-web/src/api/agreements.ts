import { api } from "@/lib/apiClient";
import type { Agreement, AgreementCreate, AgreementUpdate } from "@/types/agreement";

export interface ValidationError {
  code: string;
  message: string;
  field: string;
}

export interface ValidateAgreementResponse {
  valid: boolean;
  errors: ValidationError[];
}

export const agreementsApi = {
  list: () => api.get<{ results: Agreement[]; count: number }>("/api/agreements/"),

  // Backend wraps detail in {agreement: ...}
  get: (id: number) =>
    api.get<{ agreement: Agreement }>(`/api/agreements/${id}/`).then((r) => r.agreement),

  create: (data: AgreementCreate) =>
    api.post<{ agreement: Agreement }>("/api/agreements/", data).then((r) => r.agreement),

  update: (id: number, data: AgreementUpdate) =>
    api.patch<{ agreement: Agreement }>(`/api/agreements/${id}/`, data).then((r) => r.agreement),

  validate: (id: number) =>
    api.post<ValidateAgreementResponse>(`/api/agreements/${id}/validate/`),

  deleteDraft: (id: number) => api.delete<void>(`/api/agreements/${id}/`),
};
