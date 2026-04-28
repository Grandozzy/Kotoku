import { useMutation } from "@tanstack/react-query";

import { confirmOtp, requestOtp } from "@/api/consent";
import { useAgreementStore } from "@/features/agreements/agreementStore";
import { getApiErrorMessage } from "@/lib/errorHandler";

export function useRequestOtp(agreementId: number) {
  const setConsentSent = useAgreementStore((s) => s.setConsentSent);

  return useMutation({
    mutationFn: ({
      party,
      partyId,
    }: {
      party: "A" | "B";
      partyId: number;
    }) => requestOtp(agreementId, partyId).then((record) => ({ record, party })),
    onSuccess: ({ record, party }) => {
      setConsentSent(party, record.id);
    },
  });
}

export function useConfirmOtp(agreementId: number) {
  const setConsentConfirmed = useAgreementStore((s) => s.setConsentConfirmed);

  return useMutation({
    mutationFn: ({
      party,
      consentRecordId,
      otpCode,
    }: {
      party: "A" | "B";
      consentRecordId: number;
      otpCode: string;
    }) =>
      confirmOtp(agreementId, consentRecordId, otpCode).then((record) => ({
        record,
        party,
      })),
    onSuccess: ({ party }) => {
      setConsentConfirmed(party);
    },
  });
}

export { getApiErrorMessage };
