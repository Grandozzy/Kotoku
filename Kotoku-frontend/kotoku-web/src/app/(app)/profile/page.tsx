"use client";

import { useRouter } from "next/navigation";
import { useSessionStore } from "@/store/sessionStore";
import { api } from "@/lib/apiClient";

export default function ProfilePage() {
  const router = useRouter();
  const { phone, accountId, clearSession } = useSessionStore();

  async function handleSignOut() {
    try {
      await api.post("/api/auth/logout/");
    } catch {
      // best effort
    } finally {
      clearSession();
      router.replace("/login");
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-sm">
      <h1 className="text-2xl font-bold tracking-tight">Profile</h1>

      <div className="rounded-2xl border border-neutral-100 divide-y divide-neutral-50 overflow-hidden">
        <div className="flex justify-between items-center px-4 py-3">
          <span className="text-sm text-neutral-500">Phone</span>
          <span className="text-sm font-medium">{phone ?? "—"}</span>
        </div>
        <div className="flex justify-between items-center px-4 py-3">
          <span className="text-sm text-neutral-500">Account ID</span>
          <span className="text-sm font-mono text-neutral-400">{accountId ?? "—"}</span>
        </div>
      </div>

      <div className="rounded-2xl border border-neutral-100 p-5 flex flex-col gap-3">
        <p className="text-sm font-semibold">Legal</p>
        <div className="flex flex-col gap-1 text-sm text-neutral-500">
          <a href="/legal" className="hover:text-emerald-600">
            Ghana Digital Evidence Law reference →
          </a>
          <a href="/how-it-works" className="hover:text-emerald-600">
            How Kotoku works →
          </a>
        </div>
      </div>

      <div className="rounded-2xl border border-neutral-100 p-5">
        <p className="text-sm text-neutral-500 mb-3">
          Signing out will end your session. Your agreements and vault remain
          accessible when you sign back in.
        </p>
        <button
          onClick={handleSignOut}
          className="px-5 py-2.5 rounded-full border border-neutral-200 text-sm font-medium text-neutral-700 hover:bg-neutral-50 hover:border-neutral-300 transition-colors"
        >
          Sign out
        </button>
      </div>

      <p className="text-xs text-center text-neutral-300">
        &ldquo;Keep all your agreements in Kotoku. Take them out tomorrow if you need to.&rdquo;
      </p>
    </div>
  );
}
