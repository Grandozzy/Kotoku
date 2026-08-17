import { api } from "@/lib/apiClient";
import type { Party, PartyInput } from "@/types/party";

export const partiesApi = {
  list: (agreementId: number) =>
    api
      .get<{ parties: Party[] }>(`/api/agreements/${agreementId}/parties/`)
      .then((r) => r.parties),

  set: (agreementId: number, parties: PartyInput[]) =>
    api
      .post<{ parties: Party[] }>(`/api/agreements/${agreementId}/parties/`, { parties })
      .then((r) => r.parties),

  patch: (agreementId: number, parties: Partial<PartyInput>[]) =>
    api
      .patch<{ parties: Party[] }>(`/api/agreements/${agreementId}/parties/`, { parties })
      .then((r) => r.parties),

  sendInvite: (agreementId: number, role: string) =>
    api.post<void>(`/api/agreements/${agreementId}/parties/invite/${role}/`),
};
