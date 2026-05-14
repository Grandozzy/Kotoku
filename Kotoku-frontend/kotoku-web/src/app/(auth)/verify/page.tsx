"use client";

import { useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ShieldCheck } from "lucide-react";
import { authApi } from "@/api/auth";
import { useSessionStore } from "@/store/sessionStore";
import { KotokuLogo } from "@/components/brand/KotokuLogo";

function VerifyForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const phone = searchParams.get("phone") ?? "";
  const setSession = useSessionStore((s) => s.setSession);

  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await authApi.verifyOtp(phone, code);
      setSession(res.access, res.refresh, res.account_id, phone);
      router.replace("/dashboard");
    } catch {
      setError("Invalid or expired code. Try again.");
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
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-sm border border-neutral-100 p-8">
        <h1 className="text-2xl font-bold tracking-tight">Enter your code</h1>
        <p className="mt-1 text-sm text-neutral-500">
          We sent an 8-digit code to{" "}
          <span className="font-semibold text-neutral-700">{phone}</span>.
          {" "}It expires in 10 minutes.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <input
            type="text"
            inputMode="numeric"
            maxLength={8}
            placeholder="00000000"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            required
            className="w-full rounded-lg border border-neutral-200 px-4 py-3 text-center text-2xl tracking-[0.4em] font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading || code.length < 8}
            className="w-full py-2.5 rounded-full bg-neutral-900 text-white font-medium text-sm disabled:opacity-50 hover:bg-neutral-700 transition-colors"
          >
            {loading ? "Verifying…" : "Confirm →"}
          </button>
        </form>

        <button
          onClick={() => router.back()}
          className="mt-4 w-full text-center text-sm text-neutral-400 hover:text-neutral-600 transition-colors"
        >
          ← Use a different number
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
