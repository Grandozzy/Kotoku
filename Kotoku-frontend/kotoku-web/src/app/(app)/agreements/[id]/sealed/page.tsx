"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { agreementsApi } from "@/api/agreements";
import { vaultApi } from "@/api/vault";
import { reopenApi } from "@/api/reopen";
import { useSessionStore } from "@/store/sessionStore";

export default function SealedPage() {
  const { id } = useParams<{ id: string }>();
  const agreementId = Number(id);
  const router = useRouter();
  const queryClient = useQueryClient();
  const authenticatedPhone = useSessionStore((s) => s.phone);

  const { data: agreement } = useQuery({
    queryKey: ["agreements", agreementId],
    queryFn: () => agreementsApi.get(agreementId),
  });

  // Find the vault entry for this agreement
  const { data: vaultList } = useQuery({
    queryKey: ["vault"],
    queryFn: () => vaultApi.list(),
    enabled: !!agreement?.sealed_at,
  });

  const vaultEntry = vaultList?.results.find((v) => v.agreement === agreementId);

  // Reopen flow state
  const [showReopenForm, setShowReopenForm] = useState(false);
  const [reopenOtp, setReopenOtp] = useState("");
  const [reopenOtpSent, setReopenOtpSent] = useState(false);

  const requestReopenMutation = useMutation({
    mutationFn: () => reopenApi.request(agreementId),
    onSuccess: () => {
      setReopenOtpSent(true);
      queryClient.invalidateQueries({ queryKey: ["agreements", agreementId] });
      queryClient.invalidateQueries({ queryKey: ["vault"] });
    },
  });

  const confirmReopenMutation = useMutation({
    mutationFn: () => {
      if (!authenticatedPhone) {
        throw new Error("Sign in again before confirming reopen.");
      }
      return reopenApi.confirm(agreementId, authenticatedPhone, reopenOtp);
    },
    onSuccess: () => {
      setShowReopenForm(false);
      setReopenOtpSent(false);
      setReopenOtp("");
      queryClient.invalidateQueries({ queryKey: ["agreements", agreementId] });
      queryClient.invalidateQueries({ queryKey: ["vault"] });
    },
  });

  if (!agreement) return null;

  if (!agreement.sealed_at && agreement.status !== "reopen_requested") {
    router.replace(`/agreements/${agreementId}/consent`);
    return null;
  }

  const isReopenRequested = agreement.status === "reopen_requested";

  return (
    <div className="flex flex-col gap-6 max-w-xl">
      {/* Seal confirmation */}
      <div className="rounded-2xl bg-emerald-50 border border-emerald-100 px-5 py-5">
        <p className="text-emerald-700 font-semibold text-base">
          ✓ Agreement sealed
        </p>
        {agreement.sealed_at && (
          <p className="text-emerald-600 text-xs mt-1">
            {new Date(agreement.sealed_at).toLocaleString("en-GB", {
              day: "numeric",
              month: "long",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}{" "}UTC
          </p>
        )}
      </div>

      {/* Seal hash */}
      {agreement.seal_hash && (
        <div className="rounded-2xl border border-neutral-100 p-5">
          <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
            Seal hash (SHA-256)
          </p>
          <p className="font-mono text-xs break-all text-neutral-700 leading-relaxed">
            {agreement.seal_hash}
          </p>
          <p className="mt-3 text-xs text-neutral-400">
            This hash uniquely identifies the sealed state of this agreement. Any
            change would produce a different hash, making tampering detectable.
          </p>
        </div>
      )}

      {/* Parties summary */}
      <div className="rounded-2xl border border-neutral-100 overflow-hidden">
        <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-100">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Parties who consented
          </p>
        </div>
        <div className="divide-y divide-neutral-50">
          {agreement.parties.map((p) => (
            <div key={p.id} className="flex items-center gap-3 px-4 py-3">
              <div className="w-7 h-7 rounded-full bg-emerald-100 flex items-center justify-center text-xs font-bold text-emerald-700">
                {p.display_name.charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="text-sm font-medium">{p.display_name}</p>
                <p className="text-xs text-neutral-400">
                  {p.role} · {p.phone}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Vault link */}
      {vaultEntry ? (
        <div className="rounded-2xl border border-neutral-100 p-5 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold">PDF Export</p>
            <p className="text-xs text-neutral-500 mt-0.5">
              {vaultEntry.pdf_status === "ready"
                ? "Your sealed PDF is ready."
                : vaultEntry.pdf_status === "generating"
                ? "Generating PDF…"
                : vaultEntry.pdf_status === "failed"
                ? "Export failed — retry in vault."
                : "PDF pending."}
            </p>
          </div>
          <Link
            href={`/vault/${vaultEntry.agreement}`}
            className="px-4 py-2 rounded-full bg-neutral-900 text-white text-xs font-medium hover:bg-neutral-700 transition-colors"
          >
            Open in vault →
          </Link>
        </div>
      ) : (
        <div className="rounded-xl bg-neutral-50 px-4 py-3 text-sm text-neutral-500">
          Vault entry is being created. Check the{" "}
          <Link href="/vault" className="text-emerald-600 underline">
            vault
          </Link>{" "}
          shortly.
        </div>
      )}

      {/* Reopen section */}
      {!isReopenRequested && agreement.sealed_at && (
        <div className="rounded-2xl border border-neutral-100 p-5">
          <p className="text-sm font-semibold">Need to make a change?</p>
          <p className="text-xs text-neutral-500 mt-1">
            Reopening requires both parties to confirm again. The original sealed
            record is preserved as a revision.
          </p>
          <p className="mt-2 rounded-xl border border-amber-100 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            Each party must confirm reopen from the account tied to their own phone.
            The counterparty should sign in on their device or invite link and enter
            only the OTP sent to their phone.
          </p>
          {!showReopenForm ? (
            <button
              onClick={() => setShowReopenForm(true)}
              className="mt-3 px-4 py-2 rounded-full border border-neutral-200 text-sm font-medium hover:bg-neutral-50"
            >
              Request reopen
            </button>
          ) : (
            <div className="mt-4 flex flex-col gap-3">
              {!reopenOtpSent ? (
                <>
                  <p className="text-xs text-neutral-500">
                    This will send reopen OTPs to all parties. Each party must
                    confirm with the phone/account that received their OTP.
                  </p>
                  <div className="flex gap-3">
                    <button
                      onClick={() => requestReopenMutation.mutate()}
                      disabled={requestReopenMutation.isPending}
                      className="px-4 py-2 rounded-full bg-amber-600 text-white text-sm font-medium disabled:opacity-50 hover:bg-amber-700"
                    >
                      {requestReopenMutation.isPending ? "Requesting…" : "Send reopen OTPs"}
                    </button>
                    <button
                      onClick={() => setShowReopenForm(false)}
                      className="px-4 py-2 rounded-full border border-neutral-200 text-sm font-medium"
                    >
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <p className="text-xs text-neutral-500">
                    Enter your phone and the OTP you received to confirm your
                    consent to reopen. Do not enter the counterparty&apos;s phone or code.
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <input
                      type="tel"
                      placeholder="+233XXXXXXXXX"
                      value={authenticatedPhone ?? ""}
                      readOnly
                      className="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-500"
                    />
                    <input
                      type="text"
                      inputMode="numeric"
                      maxLength={8}
                      placeholder="OTP"
                      value={reopenOtp}
                      onChange={(e) => setReopenOtp(e.target.value.replace(/\D/g, ""))}
                      className="rounded-lg border border-neutral-200 px-3 py-2 text-sm font-mono tracking-widest text-center focus:outline-none focus:ring-2 focus:ring-amber-400"
                    />
                  </div>
                  <button
                    onClick={() => confirmReopenMutation.mutate()}
                    disabled={
                      confirmReopenMutation.isPending ||
                      !authenticatedPhone ||
                      reopenOtp.length < 4
                    }
                    className="px-4 py-2 rounded-full bg-amber-600 text-white text-sm font-medium disabled:opacity-50 w-fit"
                  >
                    {confirmReopenMutation.isPending ? "Confirming…" : "Confirm reopen"}
                  </button>
                </>
              )}
              {requestReopenMutation.isError && (
                <p className="text-sm text-red-600">Could not request reopen.</p>
              )}
              {confirmReopenMutation.isError && (
                <p className="text-sm text-red-600">
                  Invalid code, expired code, or this account does not match the
                  party phone. Sign in with the phone that received the OTP.
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {isReopenRequested && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-700">
          <p className="font-semibold">Reopen requested</p>
          <p className="mt-1 text-xs">
            Waiting for both parties to confirm. Once confirmed, the agreement
            will return to Active status for editing.
          </p>
        </div>
      )}
    </div>
  );
}
