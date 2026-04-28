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
    // Poll every 5s while PDF is still pending so UI updates when ready
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.pdfStatus === "pending" ? 5000 : false;
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
