"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { agreementsApi } from "@/api/agreements";
import { consentApi } from "@/api/consent";

export default function ConsentPage() {
  const { id } = useParams<{ id: string }>();
  const agreementId = Number(id);
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: agreement } = useQuery({
    queryKey: ["agreements", agreementId],
    queryFn: () => agreementsApi.get(agreementId),
  });

  const { data: consentStatus, refetch: refetchStatus } = useQuery({
    queryKey: ["consent-status", agreementId],
    queryFn: () => consentApi.status(agreementId),
    enabled: !!agreement && agreement.parties.length >= 2,
    refetchInterval: 8000, // poll while waiting for counterparty
  });

  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [requestSent, setRequestSent] = useState(false);

  const requestMutation = useMutation({
    mutationFn: () => consentApi.requestOtps(agreementId),
    onSuccess: () => {
      setRequestSent(true);
      refetchStatus();
    },
  });

  const confirmMutation = useMutation({
    mutationFn: () => consentApi.confirm(agreementId, phone, otp),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agreements", agreementId] });
      queryClient.invalidateQueries({ queryKey: ["consent-status", agreementId] });
      refetchStatus();
      setOtp("");
    },
  });

  if (!agreement) return null;

  const parties = agreement.parties;
  const isSealed = agreement.status === "sealed";
  const canRequest =
    parties.length >= 2 && ["draft", "active"].includes(agreement.status);

  // When all_consented → agreement gets sealed, redirect
  if (isSealed) {
    router.replace(`/agreements/${agreementId}/sealed`);
    return null;
  }

  const records = consentStatus?.records ?? [];
  const allConsented = consentStatus?.all_consented ?? false;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-bold tracking-tight">Consent</h1>
      <p className="text-sm text-neutral-500">
        Both parties must confirm via SMS OTP before the agreement can be sealed.
        No one can seal alone.
      </p>

      {parties.length < 2 && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          Add at least 2 parties before requesting consent.
        </div>
      )}

      {/* Consent status table */}
      {records.length > 0 && (
        <div className="rounded-2xl border border-neutral-100 overflow-hidden">
          <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-100">
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
              Consent status
            </p>
          </div>
          <div className="divide-y divide-neutral-50">
            {records.map((r) => {
              const party = parties.find((p) => p.phone === r.party_phone);
              return (
                <div key={r.id} className="flex items-center justify-between px-4 py-3">
                  <div>
                    <p className="text-sm font-medium">
                      {party?.display_name ?? r.party_phone}
                    </p>
                    <p className="text-xs text-neutral-400 mt-0.5">{r.party_phone}</p>
                  </div>
                  {r.granted ? (
                    <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700">
                      ✓ Confirmed
                      {r.granted_at && (
                        <> · {new Date(r.granted_at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}</>
                      )}
                    </span>
                  ) : (
                    <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-amber-50 text-amber-600">
                      Pending
                    </span>
                  )}
                </div>
              );
            })}
          </div>
          {allConsented && (
            <div className="px-4 py-3 bg-emerald-50 border-t border-emerald-100 text-sm text-emerald-700 font-medium">
              ✓ All parties confirmed — sealing agreement…
            </div>
          )}
        </div>
      )}

      {/* Step 1: Request OTPs */}
      {canRequest && !requestSent && (
        <div className="rounded-2xl border border-neutral-100 p-5 flex flex-col gap-3">
          <p className="text-sm font-semibold">Step 1 — Send OTPs to all parties</p>
          <p className="text-xs text-neutral-500">
            This sends an SMS OTP to each party&apos;s phone number. Each party must
            confirm independently.
          </p>
          <button
            onClick={() => requestMutation.mutate()}
            disabled={requestMutation.isPending}
            className="px-5 py-2.5 rounded-full bg-neutral-900 text-white text-sm font-medium disabled:opacity-50 hover:bg-neutral-700 transition-colors w-fit"
          >
            {requestMutation.isPending ? "Sending…" : "Send OTPs to all parties"}
          </button>
          {requestMutation.isError && (
            <p className="text-sm text-red-600">
              Could not send OTPs. Make sure all parties have valid phone numbers.
            </p>
          )}
        </div>
      )}

      {/* Step 2: Confirm your own OTP */}
      {(requestSent || records.length > 0) && !allConsented && (
        <div className="rounded-2xl border border-neutral-100 p-5 flex flex-col gap-4">
          <p className="text-sm font-semibold">Step 2 — Confirm your OTP</p>
          <p className="text-xs text-neutral-500">
            Each party enters their phone number and the 6-digit code from their
            SMS. Counterparties can confirm on their own device.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-neutral-600">Your phone number</label>
              <input
                type="tel"
                placeholder="+233XXXXXXXXX"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-neutral-600">OTP code</label>
              <input
                type="text"
                inputMode="numeric"
                maxLength={8}
                placeholder="123456"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                className="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm font-mono tracking-widest text-center focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>
          <div className="flex gap-3 items-center">
            <button
              onClick={() => confirmMutation.mutate()}
              disabled={confirmMutation.isPending || !phone || otp.length < 4}
              className="px-5 py-2.5 rounded-full bg-neutral-900 text-white text-sm font-medium disabled:opacity-50 hover:bg-neutral-700 transition-colors"
            >
              {confirmMutation.isPending ? "Confirming…" : "Confirm consent"}
            </button>
            <button
              onClick={() => requestMutation.mutate()}
              disabled={requestMutation.isPending}
              className="text-sm text-neutral-400 hover:text-neutral-600"
            >
              Resend OTPs
            </button>
          </div>
          {confirmMutation.isError && (
            <p className="text-sm text-red-600">
              Invalid or expired code. Check the phone number and code, then try again.
            </p>
          )}
          {confirmMutation.isSuccess && (
            <p className="text-sm text-emerald-600">✓ Consent confirmed.</p>
          )}
        </div>
      )}

      {/* Waiting for counterparty */}
      {requestSent && !allConsented && records.some((r) => r.granted) && (
        <div className="rounded-xl bg-blue-50 px-4 py-3 text-sm text-blue-700">
          Waiting for the other party to confirm on their device. This page checks
          automatically every few seconds.
        </div>
      )}
    </div>
  );
}
