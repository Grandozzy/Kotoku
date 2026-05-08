import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getAuditLog,
  getVaultRecord,
  listVault,
  requestPdfExport,
  retryPdfExport,
} from "@/api/vault";
import { useSessionStore } from "@/store/sessionStore";

export function useVaultList() {
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  return useQuery({
    queryKey: ["vault"],
    queryFn: listVault,
    enabled: isAuthenticated,
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
      if (data.pdfStatus === "pending" || data.pdfStatus === "generating") return 5000;
      return false;
    },
  });
}

export function useRequestExport(agreementId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => requestPdfExport(agreementId),
    onSuccess: (updated) => {
      queryClient.setQueryData(["vault", agreementId], updated);
    },
  });
}

export function useRetryExport(agreementId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => retryPdfExport(agreementId),
    onSuccess: (updated) => {
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
