"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, ChevronRight, LogOut, Pencil, ShieldCheck, TrendingUp, X } from "lucide-react";
import { useSessionStore } from "@/store/sessionStore";
import { usePlan } from "@/hooks/usePlan";
import { api } from "@/lib/apiClient";

// ── API ───────────────────────────────────────────────────────────────────────

interface MeData {
  id: number;
  phone: string;
  email: string;
  full_name: string;
  member_since: string;
}

function fetchMe() {
  return api
    .get<{ status: string; data: MeData }>("/api/me/")
    .then((r) => r.data);
}

function patchMe(payload: { full_name?: string; email?: string }) {
  return api
    .patch<{ status: string; data: MeData }>("/api/me/", payload)
    .then((r) => r.data);
}

// ── Inline editable row ───────────────────────────────────────────────────────

function EditableField({
  label,
  value,
  placeholder,
  onSave,
  type = "text",
}: {
  label: string;
  value: string;
  placeholder: string;
  onSave: (v: string) => void;
  type?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);

  const save = () => { onSave(draft.trim()); setEditing(false); };
  const cancel = () => { setDraft(value); setEditing(false); };

  return (
    <div className="flex items-center justify-between px-4 py-3 gap-4">
      <span className="text-sm text-neutral-500 w-32 shrink-0">{label}</span>
      {editing ? (
        <div className="flex items-center gap-2 flex-1">
          <input
            autoFocus
            type={type}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") cancel(); }}
            className="flex-1 text-sm border border-blue-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={save}
            className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center hover:bg-blue-700 transition-colors"
          >
            <Check size={13} className="text-white" strokeWidth={2.5} />
          </button>
          <button
            onClick={cancel}
            className="w-7 h-7 rounded-lg border border-neutral-200 flex items-center justify-center hover:bg-neutral-50 transition-colors"
          >
            <X size={13} className="text-neutral-500" strokeWidth={2} />
          </button>
        </div>
      ) : (
        <button
          onClick={() => { setDraft(value); setEditing(true); }}
          className="flex items-center gap-2 flex-1 justify-end group text-right"
        >
          <span className={`text-sm font-medium ${value ? "text-neutral-800" : "text-neutral-400"}`}>
            {value || placeholder}
          </span>
          <Pencil size={13} className="text-neutral-300 group-hover:text-neutral-500 transition-colors shrink-0" strokeWidth={2} />
        </button>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ProfilePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { clearSession } = useSessionStore();
  const { data: plan } = usePlan();

  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
  });

  const updateMutation = useMutation({
    mutationFn: patchMe,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  });

  const fullName = me?.full_name ?? "";
  const email = me?.email?.endsWith("@kotoku.app") ? "" : (me?.email ?? "");
  const phone = me?.phone ?? "—";
  const memberSince = me?.member_since ?? "";

  const initials = fullName
    ? fullName.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : phone.slice(-2);

  async function handleSignOut() {
    try { await api.post("/api/auth/logout/"); } catch { /* best effort */ }
    clearSession();
    router.replace("/login");
  }

  // Plan display
  const planName = plan?.plan.name ?? "Personal Basic";
  const usage = plan?.usage;
  const showUsage = plan && plan.flags.is_personal && usage;

  return (
    <div className="flex flex-col gap-6 max-w-lg">
      <h1 className="text-2xl font-bold tracking-tight">Profile</h1>

      {/* Identity card */}
      <div className="rounded-2xl border border-neutral-100 overflow-hidden">
        {/* Avatar row */}
        <div className="flex items-center gap-4 px-4 py-5 border-b border-neutral-50">
          <div className="w-12 h-12 rounded-full bg-blue-600 flex items-center justify-center shrink-0">
            <span className="text-white font-bold text-base">{initials}</span>
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-neutral-900 truncate">
              {fullName || "Add your name"}
            </p>
            <p className="text-sm text-neutral-400">{phone}</p>
            {memberSince && (
              <p className="text-xs text-neutral-400 mt-0.5">Member since {memberSince}</p>
            )}
          </div>
        </div>

        {/* Editable fields */}
        <div className="divide-y divide-neutral-50">
          <EditableField
            label="Full name"
            value={fullName}
            placeholder="Add your name"
            onSave={(v) => updateMutation.mutate({ full_name: v })}
          />
          <EditableField
            label="Email"
            value={email}
            placeholder="Add email (optional)"
            type="email"
            onSave={(v) => updateMutation.mutate({ email: v })}
          />
        </div>

        {updateMutation.isError && (
          <p className="text-xs text-red-500 text-center px-4 pb-3">
            Could not save changes. Please try again.
          </p>
        )}
      </div>

      {/* Plan card */}
      <div className="rounded-2xl border border-neutral-100 overflow-hidden">
        <div className="px-4 py-3 bg-neutral-50 border-b border-neutral-100">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Plan</p>
        </div>
        <div className="divide-y divide-neutral-50">
          <div className="flex items-center justify-between px-4 py-3">
            <div className="flex items-center gap-2">
              <ShieldCheck size={15} className="text-blue-600" strokeWidth={2} />
              <span className="text-sm font-medium text-neutral-800">{planName}</span>
            </div>
            <Link
              href="/pricing"
              className="text-xs text-blue-600 font-medium hover:underline"
            >
              View plans
            </Link>
          </div>

          {showUsage && (
            <div className="flex items-center justify-between px-4 py-3">
              <span className="text-sm text-neutral-500">Seals this month</span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-1.5 rounded-full bg-neutral-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      usage.is_cap_reached
                        ? "bg-red-500"
                        : usage.is_near_cap
                        ? "bg-amber-400"
                        : "bg-blue-500"
                    }`}
                    style={{
                      width: `${Math.min(
                        (usage.sealed_agreements_this_period /
                          plan.plan.max_agreements_per_month) *
                          100,
                        100
                      )}%`,
                    }}
                  />
                </div>
                <span
                  className={`text-xs font-medium ${
                    usage.is_cap_reached
                      ? "text-red-600"
                      : usage.is_near_cap
                      ? "text-amber-600"
                      : "text-neutral-500"
                  }`}
                >
                  {usage.sealed_agreements_this_period} / {plan.plan.max_agreements_per_month}
                </span>
              </div>
            </div>
          )}

          {plan?.flags.show_upgrade_recommendation && plan.recommended_upgrades[0] && (
            <div className="flex items-center gap-3 px-4 py-3 bg-amber-50">
              <TrendingUp size={14} className="text-amber-600 shrink-0" strokeWidth={2} />
              <span className="text-xs text-amber-700 flex-1">
                Upgrade to <strong>{plan.recommended_upgrades[0].name}</strong> for more seals and longer retention.
              </span>
              <Link
                href="/pricing"
                className="text-xs font-semibold text-amber-700 hover:underline shrink-0"
              >
                Upgrade →
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Links */}
      <div className="rounded-2xl border border-neutral-100 overflow-hidden">
        {[
          { label: "How Kotoku works", href: "/how-it-works" },
          { label: "Ghana Digital Evidence Law", href: "/legal" },
          { label: "Pricing", href: "/pricing" },
        ].map(({ label, href }) => (
          <Link
            key={href}
            href={href}
            className="flex items-center justify-between px-4 py-3 hover:bg-neutral-50 transition-colors border-b border-neutral-50 last:border-0"
          >
            <span className="text-sm text-neutral-700">{label}</span>
            <ChevronRight size={15} className="text-neutral-300" strokeWidth={2} />
          </Link>
        ))}
      </div>

      {/* Sign out */}
      <button
        onClick={handleSignOut}
        className="flex items-center gap-3 px-4 py-3 rounded-2xl border border-neutral-100 hover:bg-neutral-50 transition-colors w-full text-left"
      >
        <div className="w-7 h-7 rounded-lg bg-red-50 flex items-center justify-center">
          <LogOut size={13} className="text-red-500" strokeWidth={2} />
        </div>
        <span className="text-sm font-medium text-red-600">Sign out</span>
      </button>
    </div>
  );
}
