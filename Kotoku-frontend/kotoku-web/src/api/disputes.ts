import { api } from "@/lib/apiClient";
import type { Dispute, DisputeCreate } from "@/types/dispute";

export const disputesApi = {
  listAll: () =>
    api
      .get<{ disputes: Dispute[] }>("/api/disputes/")
      .then((r) => r.disputes),

  list: (agreementId: number) =>
    api
      .get<{ disputes: Dispute[] }>(`/api/agreements/${agreementId}/disputes/`)
      .then((r) => r.disputes),

  create: (agreementId: number, data: DisputeCreate) =>
    api
      .post<{ dispute: Dispute }>(`/api/agreements/${agreementId}/disputes/`, data)
      .then((r) => r.dispute),
};
