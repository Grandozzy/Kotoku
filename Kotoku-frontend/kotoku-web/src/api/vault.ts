import { api } from "@/lib/apiClient";
import type { VaultEntry } from "@/types/vault";

export const vaultApi = {
  list: () => api.get<{ results: VaultEntry[] }>("/api/vault/"),

  get: (id: number) => api.get<VaultEntry>(`/api/vault/${id}/`),

  requestExport: (id: number) =>
    api.post<{ detail: string }>(`/api/vault/${id}/export/`),

  retryExport: (id: number) =>
    api.post<{ detail: string }>(`/api/vault/${id}/retry-export/`),
};
