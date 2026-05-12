"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ShieldCheck } from "lucide-react";
import { authApi } from "@/api/auth";

export default function LoginPage() {
  const router = useRouter();
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.SyntheticEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await authApi.requestOtp(phone);
      router.push(`/verify?phone=${encodeURIComponent(phone)}`);
    } catch {
      setError("Could not send OTP. Check the number and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 bg-neutral-50 gap-6">
      {/* Brand */}
      <Link href="/" className="flex items-center gap-2 group">
        <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
          <ShieldCheck size={18} className="text-white" strokeWidth={2} />
        </div>
        <span className="text-xl font-bold tracking-tight text-neutral-900 group-hover:text-neutral-700 transition-colors">
          Kotoku
        </span>
      </Link>

      {/* Card */}
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-sm border border-neutral-100 p-8">
        <h1 className="text-2xl font-bold tracking-tight">Sign in</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Enter your phone number. We&apos;ll send you a one-time code.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <div>
            <label htmlFor="phone" className="text-sm font-medium text-neutral-700">
              Phone number
            </label>
            <input
              id="phone"
              type="tel"
              placeholder="+233 XX XXX XXXX"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
              className="mt-1 w-full rounded-lg border border-neutral-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading || !phone}
            className="w-full py-2.5 rounded-full bg-neutral-900 text-white font-medium text-sm disabled:opacity-50 hover:bg-neutral-700 transition-colors"
          >
            {loading ? "Sending…" : "Send code →"}
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
