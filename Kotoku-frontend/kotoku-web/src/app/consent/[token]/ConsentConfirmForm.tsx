"use client";

import { useState } from "react";
import { CheckCircle, Loader2 } from "lucide-react";

import { confirmPublicConsent } from "@/api/publicConsent";

export function ConsentConfirmForm({
  alreadyGranted,
  token,
}: {
  alreadyGranted: boolean;
  token: string;
}) {
  const [otpCode, setOtpCode] = useState("");
  const [confirmed, setConfirmed] = useState(alreadyGranted);
  const [allConsented, setAllConsented] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await confirmPublicConsent(token, otpCode);
      setConfirmed(result.consent_record.granted);
      setAllConsented(result.all_consented);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not confirm consent.");
    } finally {
      setSubmitting(false);
    }
  };

  if (confirmed) {
    return (
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 text-emerald-800">
        <div className="flex items-center gap-2 font-semibold">
          <CheckCircle size={18} />
          Consent confirmed
        </div>
        <p className="mt-2 text-sm">
          {allConsented
            ? "Both parties have now confirmed. The agreement creator can seal the agreement."
            : "Your consent is recorded. The agreement will be ready to seal after every party confirms."}
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
      <label className="block text-sm font-semibold text-neutral-900" htmlFor="otp-code">
        Enter the OTP sent to your phone
      </label>
      <input
        id="otp-code"
        inputMode="numeric"
        autoComplete="one-time-code"
        value={otpCode}
        onChange={(event) => setOtpCode(event.target.value.replace(/\D/g, "").slice(0, 4))}
        className="mt-3 w-full rounded-xl border border-neutral-300 px-3 py-3 text-center text-xl tracking-[0.5em] outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 sm:px-4 sm:text-2xl sm:tracking-[0.6em]"
        placeholder="••••"
      />
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={otpCode.length < 4 || submitting}
        className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-full bg-neutral-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-neutral-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting && <Loader2 size={16} className="animate-spin" />}
        I consent to this agreement
      </button>
    </form>
  );
}
