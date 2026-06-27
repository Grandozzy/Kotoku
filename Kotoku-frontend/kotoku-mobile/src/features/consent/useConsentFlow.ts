import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { confirmOtp, getConsentStatus, requestOtp } from "@/api/consent";
import { validateAgreement } from "@/api/agreements";
import { useAgreementStore } from "@/features/agreements/agreementStore";
import { getApiErrorMessage } from "@/lib/errorHandler";
import { feedbackSuccess } from "@/lib/feedback";
import { isSamePhone, normalizePhoneToE164 } from "@/lib/phone";
import { useSessionStore } from "@/store/sessionStore";
import type { ConsentStatus } from "@/api/consent";

function formatValidationErrors(errors: { field: string; message: string }[]) {
  if (errors.length === 0) return "Agreement is not ready for consent.";
  return errors
    .slice(0, 4)
    .map((e) => `${e.field}: ${e.message}`)
    .join(" ");
}

export function useRequestOtp(agreementId: number) {
  const setConsentState = useAgreementStore((s) => s.setConsentState);
  const resetConsentState = useAgreementStore((s) => s.resetConsentState);
  const queryClient = useQueryClient();
  const partyA = useAgreementStore((s) => s.partyA);
  const partyB = useAgreementStore((s) => s.partyB);

  return useMutation({
    mutationFn: async (options?: { validateBeforeRequest?: boolean }) => {
      resetConsentState();
      if (options?.validateBeforeRequest !== false) {
        const validation = await validateAgreement(agreementId);
        if (!validation.valid) {
          throw new Error(formatValidationErrors(validation.errors));
        }
      }
      return requestOtp(agreementId);
    },
    onSuccess: (data) => {
      feedbackSuccess();
      queryClient.setQueryData<ConsentStatus>(
        ["consent", "status", agreementId],
        {
          agreementId,
          allConsented: false,
          records: data.consentRecords,
        },
      );
      const partyARecord = data.consentRecords.find((record) =>
        isSamePhone(record.partyPhone, partyA.phone),
      );
      const partyBRecord = data.consentRecords.find((record) =>
        isSamePhone(record.partyPhone, partyB.phone),
      );

      setConsentState("A", {
        otpSent: Boolean(partyARecord),
        confirmed: partyARecord?.granted ?? false,
      });
      setConsentState("B", {
        otpSent: Boolean(partyBRecord),
        confirmed: partyBRecord?.granted ?? false,
      });
      queryClient.invalidateQueries({ queryKey: ["consent", "status", agreementId] });
    },
  });
}

export function useConfirmOtp(agreementId: number) {
  const setConsentConfirmed = useAgreementStore((s) => s.setConsentConfirmed);
  const queryClient = useQueryClient();
  const authenticatedPhone = useSessionStore((s) => s.phone);

  return useMutation({
    mutationFn: ({
      party: _party,
      otpCode,
    }: {
      party: "A" | "B";
      otpCode: string;
    }) => {
      if (!authenticatedPhone) {
        throw new Error("Sign in with the phone that received the OTP.");
      }
      return confirmOtp(agreementId, normalizePhoneToE164(authenticatedPhone), otpCode);
    },
    onSuccess: (data, { party }) => {
      feedbackSuccess();
      setConsentConfirmed(party);
      queryClient.setQueryData<ConsentStatus>(
        ["consent", "status", agreementId],
        (current) => {
          if (!current) return current;
          const records = current.records.map((record) =>
            record.id === data.id ? data : record,
          );
          const nextRecords = records.some((record) => record.id === data.id)
            ? records
            : [data, ...records];
          return {
            ...current,
            records: nextRecords,
            allConsented: current.allConsented,
          };
        },
      );
      queryClient.invalidateQueries({ queryKey: ["consent", "status", agreementId] });
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
    staleTime: 0,
    refetchOnMount: "always",
    refetchOnReconnect: true,
    refetchOnWindowFocus: true,
    refetchIntervalInBackground: true,
    refetchInterval: (query) =>
      query.state.data?.allConsented ? false : 5000,
  });

  useEffect(() => {
    if (!query.isSuccess) return;

    const records = query.data?.records ?? [];
    const latestRecords = [...records].sort((left, right) => {
      const leftCreatedAt = left.createdAt ? Date.parse(left.createdAt) : 0;
      const rightCreatedAt = right.createdAt ? Date.parse(right.createdAt) : 0;
      return rightCreatedAt - leftCreatedAt || right.id - left.id;
    });
    const partyARecord = latestRecords.find((record) => isSamePhone(record.partyPhone, partyA.phone));
    const partyBRecord = latestRecords.find((record) => isSamePhone(record.partyPhone, partyB.phone));

    setConsentState("A", {
      otpSent: Boolean(partyARecord),
      confirmed: partyARecord?.granted ?? false,
    });
    setConsentState("B", {
      otpSent: Boolean(partyBRecord),
      confirmed: partyBRecord?.granted ?? false,
    });
  }, [
    partyA.phone,
    partyB.phone,
    query.data?.records,
    query.isSuccess,
    setConsentState,
  ]);

  return query;
}

export { getApiErrorMessage };
