import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getAuditLog,
  getVaultRecord,
  listVault,
  requestPdfExport,
} from "@/api/vault";

export function useVaultList() {
  return useQuery({
    queryKey: ["vault"],
    queryFn: listVault,
  });
}

export function useVaultRecord(agreementId: number) {
  return useQuery({
    queryKey: ["vault", agreementId],
    queryFn: () => getVaultRecord(agreementId),
    enabled: agreementId > 0,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      if (data.pdfStatus === "pending") return 5000;
      return false;
    },
  });
}

export function useRequestExport(agreementId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => requestPdfExport(agreementId),
    onSuccess: (updated) => {
      // Update the cache immediately; polling will pick up the rest
      queryClient.setQueryData(["vault", agreementId], updated);
    },
  });
}

export function useAuditLog(agreementId: number) {
  return useQuery({
    queryKey: ["audit-log", agreementId],
    queryFn: () => getAuditLog(agreementId),
    enabled: agreementId > 0,
  });
}
