import { api } from "@/lib/apiClient";
import type { Party, PartyInput } from "@/types/party";

export const partiesApi = {
  list: (agreementId: number) =>
    api.get<Party[]>(`/api/agreements/${agreementId}/parties/`),

  set: (agreementId: number, parties: PartyInput[]) =>
    api.post<Party[]>(`/api/agreements/${agreementId}/parties/`, { parties }),

  patch: (agreementId: number, parties: Partial<PartyInput>[]) =>
    api.patch<Party[]>(`/api/agreements/${agreementId}/parties/`, { parties }),
};
