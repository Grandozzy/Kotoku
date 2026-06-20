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
  const setConsentState = useAgreementStore((s) => s.setConsentState);
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
      setConsentState("A", { otpSent: true, confirmed: false });
      setConsentState("B", { otpSent: true, confirmed: false });
    },
    onError: (error) => {
      if (
        partyA.phone && partyB.phone &&
        getApiErrorMessage(error).includes("already consented")
      ) {
        setConsentState("A", { otpSent: true, confirmed: true });
        setConsentState("B", { otpSent: true, confirmed: true });
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
  const setConsentState = useAgreementStore((s) => s.setConsentState);
  const query = useQuery({
    queryKey: ["consent", "status", agreementId],
    queryFn: () => getConsentStatus(agreementId),
    enabled: agreementId > 0,
    refetchInterval: (query) =>
      query.state.data?.allConsented ? false : 5000,
  });

  useEffect(() => {
    const records = query.data?.records ?? [];
    const latestRecords = [...records].sort((left, right) => {
      const leftCreatedAt = left.createdAt ? Date.parse(left.createdAt) : 0;
      const rightCreatedAt = right.createdAt ? Date.parse(right.createdAt) : 0;
      return rightCreatedAt - leftCreatedAt || right.id - left.id;
    });
    const partyARecord = latestRecords.find((record) => record.partyPhone === partyA.phone);
    const partyBRecord = latestRecords.find((record) => record.partyPhone === partyB.phone);

    if (partyARecord) {
      setConsentState("A", { otpSent: true, confirmed: partyARecord.granted });
    }
    if (partyBRecord) {
      setConsentState("B", { otpSent: true, confirmed: partyBRecord.granted });
    }
  }, [
    partyA.phone,
    partyB.phone,
    query.data?.records,
    setConsentState,
  ]);

  return query;
}

export { getApiErrorMessage };
