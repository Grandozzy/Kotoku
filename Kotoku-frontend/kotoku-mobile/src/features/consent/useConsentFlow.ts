import { useMutation, useQueryClient } from "@tanstack/react-query";

import { confirmOtp, requestOtp } from "@/api/consent";
import { useAgreementStore } from "@/features/agreements/agreementStore";
import { getApiErrorMessage } from "@/lib/errorHandler";

export function useRequestOtp(agreementId: number) {
  const setConsentSent = useAgreementStore((s) => s.setConsentSent);
  const partyA = useAgreementStore((s) => s.partyA);
  const partyB = useAgreementStore((s) => s.partyB);

  return useMutation({
    mutationFn: () => requestOtp(agreementId),
    onSuccess: () => {
      setConsentSent("A");
      setConsentSent("B");
    },
    onError: (error) => {
      if (
        partyA.phone && partyB.phone &&
        getApiErrorMessage(error).includes("already consented")
      ) {
        setConsentSent("A");
        setConsentSent("B");
      }
    },
  });
}

export function useConfirmOtp(agreementId: number) {
  const setConsentConfirmed = useAgreementStore((s) => s.setConsentConfirmed);
  const queryClient = useQueryClient();
  const partyA = useAgreementStore((s) => s.partyA);
  const partyB = useAgreementStore((s) => s.partyB);

  return useMutation({
    mutationFn: ({
      party,
      otpCode,
    }: {
      party: "A" | "B";
      otpCode: string;
    }) => {
      const phone = party === "A" ? partyA.phone : partyB.phone;
      return confirmOtp(agreementId, phone, otpCode);
    },
    onSuccess: (_data, { party }) => {
      setConsentConfirmed(party);
      queryClient.invalidateQueries({ queryKey: ["agreement", agreementId] });
    },
  });
}

export { getApiErrorMessage };
