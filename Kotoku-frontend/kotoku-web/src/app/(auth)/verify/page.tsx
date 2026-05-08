"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authApi } from "@/api/auth";
import { useSessionStore } from "@/store/sessionStore";

function VerifyForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const phone = searchParams.get("phone") ?? "";
  const setSession = useSessionStore((s) => s.setSession);

  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await authApi.verifyOtp(phone, code);
      setSession(res.account_id, phone);
      router.replace("/dashboard");
    } catch {
      setError("Invalid or expired code. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-neutral-50">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-sm border border-neutral-100 p-8">
        <h1 className="text-2xl font-bold tracking-tight">Enter your code</h1>
        <p className="mt-1 text-sm text-neutral-500">
          We sent a 6-digit code to <strong>{phone}</strong>.
        </p>
        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            placeholder="000000"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            required
            className="w-full rounded-lg border border-neutral-200 px-4 py-2.5 text-center text-2xl tracking-widest font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading || code.length < 4}
            className="w-full py-2.5 rounded-full bg-neutral-900 text-white font-medium text-sm disabled:opacity-50 hover:bg-neutral-700 transition-colors"
          >
            {loading ? "Verifying…" : "Confirm →"}
          </button>
        </form>
        <button
          onClick={() => router.back()}
          className="mt-4 w-full text-center text-sm text-neutral-400 hover:text-neutral-600"
        >
          ← Use a different number
        </button>
      </div>
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
