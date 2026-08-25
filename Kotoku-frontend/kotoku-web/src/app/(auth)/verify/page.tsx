"use client";

import { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, ArrowRight, CheckCircle2, ShieldCheck } from "lucide-react";
import { authApi } from "@/api/auth";
import { isValidE164Phone } from "@/lib/phone";
import { useSessionStore } from "@/store/sessionStore";
import { KotokuLogo } from "@/components/brand/KotokuLogo";

function VerifyForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const phone = (searchParams.get("phone") ?? "").trim();
  const accessToken = useSessionStore((s) => s.accessToken);
  const hasHydrated = useSessionStore((s) => s.hasHydrated);
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  const isBootstrapping = useSessionStore((s) => s.isBootstrapping);
  const setSession = useSessionStore((s) => s.setSession);
  const isRecoveringSession = hasHydrated && isAuthenticated && !accessToken;

  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const isValidPhone = isValidE164Phone(phone);

  useEffect(() => {
    if (!hasHydrated || isBootstrapping || isRecoveringSession) return;
    if (isAuthenticated) router.replace("/dashboard");
  }, [hasHydrated, isAuthenticated, isBootstrapping, isRecoveringSession, router]);

  if (!hasHydrated || isBootstrapping || isRecoveringSession || isAuthenticated) {
    return null;
  }

  async function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!isValidPhone) {
      setError("Go back and enter a valid phone number in international format.");
      return;
    }
    setError(null);
    setResendSuccess(false);
    setLoading(true);
    try {
      const res = await authApi.verifyOtp(phone, code);
      if (!res.user.account_id) {
        throw new Error("Account not linked to verified user.");
      }
      setSession(res.access, res.user.account_id, res.user.phone);
      router.replace("/dashboard");
    } catch {
      setError("Invalid or expired code. Try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    if (!isValidPhone) {
      setError("Go back and enter a valid phone number in international format.");
      return;
    }
    setCode("");
    setError(null);
    setResendSuccess(false);
    setResendLoading(true);
    try {
      await authApi.requestOtp(phone);
      setResendSuccess(true);
    } catch {
      setError("Could not resend OTP. Check the number and try again.");
    } finally {
      setResendLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 bg-neutral-50 gap-6">
      {/* Brand */}
      <Link href="/" className="flex items-center">
        <KotokuLogo variant="stacked" color="navy" size={64} />
      </Link>

      {/* Card */}
      <div className="w-full max-w-sm rounded-2xl border border-neutral-100 bg-white p-6 shadow-sm sm:p-8">
        <h1 className="text-2xl font-bold tracking-tight">Enter your code</h1>
        <p className="mt-1 text-sm text-neutral-500">
          We sent a 6-digit code to{" "}
          <span className="font-semibold text-neutral-700">{phone}</span>.
          {" "}It expires in 10 minutes.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            placeholder="000000"
            value={code}
            onChange={(e) => {
              setCode(e.target.value.replace(/\D/g, "").slice(0, 6));
              if (error) setError(null);
            }}
            required
            className="form-control px-3 py-3 text-center font-mono text-xl tracking-[0.25em] sm:px-4 sm:text-2xl sm:tracking-[0.4em]"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading || resendLoading || code.length < 6}
            className="btn-primary w-full"
          >
            {loading ? "Verifying…" : <><span>Confirm</span><ArrowRight size={14} /></>}
          </button>
        </form>

        <div className="mt-4 flex flex-col items-center gap-2">
          <p className="text-sm text-neutral-500">Didn&apos;t receive a code?</p>
          <button
            type="button"
            onClick={handleResend}
            disabled={loading || resendLoading}
            className="inline-flex items-center justify-center gap-1 text-sm font-medium text-blue-600 disabled:text-neutral-400"
          >
            {resendSuccess ? (
              <>
                <CheckCircle2 size={14} />
                Code sent
              </>
            ) : resendLoading ? (
              "Sending…"
            ) : (
              "Resend code"
            )}
          </button>
        </div>

        <button
          onClick={() => router.back()}
          className="mt-4 w-full inline-flex items-center justify-center gap-1 text-sm text-neutral-400 hover:text-neutral-600 transition-colors"
        >
          <ArrowLeft size={14} /> Use a different number
        </button>
      </div>

      {/* Trust line */}
      <p className="flex items-center gap-1.5 text-xs text-neutral-400">
        <ShieldCheck size={12} strokeWidth={2} />
        Recognised under Ghana&apos;s Electronic Transactions Act (Act 772)
      </p>
    </div>
  );
}

export default function VerifyPage() {
  return (
    <Suspense>
      <VerifyForm />
    </Suspense>
  );
}
