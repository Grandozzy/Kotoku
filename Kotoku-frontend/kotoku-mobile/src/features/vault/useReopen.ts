import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  confirmReopenOtp,
  requestReopen,
  requestReopenOtp,
} from "@/api/reopen";
import { getVaultRecord } from "@/api/vault";

export function useRequestReopen(agreementId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      await requestReopen(agreementId);
      return getVaultRecord(agreementId);
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(["vault", agreementId], updated);
    },
  });
}

export function useResendReopenOtp(agreementId: number) {
  return useMutation({
    mutationFn: () => requestReopenOtp(agreementId),
  });
}

export function useConfirmReopen(agreementId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ phone, otpCode }: { phone: string; otpCode: string }) =>
      confirmReopenOtp(agreementId, phone, otpCode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vault", agreementId] });
      queryClient.invalidateQueries({ queryKey: ["pending-actions"] });
    },
  });
}