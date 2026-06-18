import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { confirmOtp, getConsentStatus, requestOtp } from "@/api/consent";
import { validateAgreement } from "@/api/agreements";
import { useAgreementStore } from "@/features/agreements/agreementStore";
import { getApiErrorMessage } from "@/lib/errorHandler";

function formatValidationErrors(errors: { field: string; message: string }[]) {
  if (errors.length === 0) return "Agreement is not ready for consent.";
  return errors
    .slice(0, 4)
    .map((e) => `${e.field}: ${e.message}`)
    .join(" ");
}

export function useRequestOtp(agreementId: number) {
  const setConsentSent = useAgreementStore((s) => s.setConsentSent);
  const partyA = useAgreementStore((s) => s.partyA);
  const partyB = useAgreementStore((s) => s.partyB);

  return useMutation({
    mutationFn: async () => {
      const validation = await validateAgreement(agreementId);
      if (!validation.valid) {
        throw new Error(formatValidationErrors(validation.errors));
      }
      return requestOtp(agreementId);
    },
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

export function useConsentStatus(agreementId: number) {
  const partyA = useAgreementStore((s) => s.partyA);
  const partyB = useAgreementStore((s) => s.partyB);
  const setConsentSent = useAgreementStore((s) => s.setConsentSent);
  const setConsentConfirmed = useAgreementStore((s) => s.setConsentConfirmed);
  const query = useQuery({
    queryKey: ["consent", "status", agreementId],
    queryFn: () => getConsentStatus(agreementId),
    enabled: agreementId > 0,
    refetchInterval: (query) =>
      query.state.data?.allConsented ? false : 5000,
  });

  useEffect(() => {
    const records = query.data?.records ?? [];
    const partyARecord = records.find((record) => record.partyPhone === partyA.phone);
    const partyBRecord = records.find((record) => record.partyPhone === partyB.phone);

    if (partyARecord) {
      setConsentSent("A");
      if (partyARecord.granted) setConsentConfirmed("A");
    }
    if (partyBRecord) {
      setConsentSent("B");
      if (partyBRecord.granted) setConsentConfirmed("B");
    }
  }, [
    partyA.phone,
    partyB.phone,
    query.data?.records,
    setConsentConfirmed,
    setConsentSent,
  ]);

  return query;
}

export { getApiErrorMessage };
