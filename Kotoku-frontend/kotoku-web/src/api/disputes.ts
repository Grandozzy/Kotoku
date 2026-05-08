import { api } from "@/lib/apiClient";
import type { Dispute, DisputeCreate } from "@/types/dispute";

export const disputesApi = {
  list: (agreementId: number) =>
    api.get<{ results: Dispute[] }>(`/api/agreements/${agreementId}/disputes/`),

  create: (agreementId: number, data: DisputeCreate) =>
    api.post<Dispute>(`/api/agreements/${agreementId}/disputes/`, data),
};
