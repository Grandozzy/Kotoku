"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { authApi } from "@/api/auth";
import { isValidE164Phone } from "@/lib/phone";
import { useSessionStore } from "@/store/sessionStore";
import { KotokuLogo } from "@/components/brand/KotokuLogo";

export default function LoginPage() {
  const router = useRouter();
  const accessToken = useSessionStore((s) => s.accessToken);
  const hasHydrated = useSessionStore((s) => s.hasHydrated);
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  const isBootstrapping = useSessionStore((s) => s.isBootstrapping);
  const isRecoveringSession = hasHydrated && isAuthenticated && !accessToken;
  const [localDigits, setLocalDigits] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const normalizedPhone = `+233${localDigits}`;
  const isValidPhone = localDigits.length === 9 && isValidE164Phone(normalizedPhone);

  function handleDigitsChange(raw: string) {
    const d = raw.replace(/\D/g, "");
    // Accept paste of full number: 0XXXXXXXXX or 233XXXXXXXXX
    if (d.startsWith("233") && d.length >= 12) { setLocalDigits(d.slice(3, 12)); return; }
    if (d.startsWith("0") && d.length >= 10) { setLocalDigits(d.slice(1, 10)); return; }
    setLocalDigits(d.slice(0, 9));
  }

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
      setError("Enter your 9-digit Ghana number after the +233 prefix.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await authApi.requestOtp(normalizedPhone);
      router.push(`/verify?phone=${encodeURIComponent(normalizedPhone)}`);
    } catch {
      setError("Could not send OTP. Check the number and try again.");
    } finally {
      setLoading(false);
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
        <h1 className="text-2xl font-bold tracking-tight">Sign in</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Enter your phone number. We&apos;ll send you a one-time code.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <div>
            <label htmlFor="phone" className="text-sm font-medium text-neutral-700">
              Phone number
            </label>
            <div className="mt-1 flex rounded-lg border border-neutral-200 focus-within:ring-2 focus-within:ring-blue-500">
              <span className="flex items-center px-3 text-sm text-neutral-500 bg-neutral-50 border-r border-neutral-200 rounded-l-lg select-none whitespace-nowrap">
                🇬🇭 +233
              </span>
              <input
                id="phone"
                type="tel"
                placeholder="XX XXX XXXX"
                maxLength={9}
                value={localDigits}
                onChange={(e) => {
                  handleDigitsChange(e.target.value);
                  if (error) setError(null);
                }}
                required
                className="flex-1 px-4 py-2.5 text-sm focus:outline-none rounded-r-lg"
              />
            </div>
            <p className="mt-1 text-xs text-neutral-500">
              Use the same number linked to your Kotoku agreements.
            </p>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading || !isValidPhone}
            className="inline-flex items-center justify-center gap-1.5 w-full py-2.5 rounded-full bg-neutral-900 text-white font-medium text-sm disabled:opacity-50 hover:bg-neutral-700 transition-colors"
          >
            {loading ? "Sending…" : <><span>Send code</span><ArrowRight size={14} /></>}
          </button>
        </form>
      </div>

      {/* Trust line */}
      <p className="flex items-center gap-1.5 text-xs text-neutral-400">
        <ShieldCheck size={12} strokeWidth={2} />
        Recognised under Ghana&apos;s Electronic Transactions Act (Act 772)
      </p>
    </div>
  );
}
