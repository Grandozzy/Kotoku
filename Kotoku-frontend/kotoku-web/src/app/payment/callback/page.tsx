"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ExternalLink, RefreshCw, ShieldCheck } from "lucide-react";
import { useInvalidatePlan } from "@/hooks/usePlan";

const MOBILE_CALLBACK_SCHEME = "kotoku://payment/callback";

export default function PaymentCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const invalidatePlan = useInvalidatePlan();
  const [attemptedDeepLink, setAttemptedDeepLink] = useState(false);

  const source = searchParams.get("source");
  const reference = searchParams.get("reference");
  const planId = searchParams.get("plan_id");

  const mobileTarget = useMemo(() => {
    const mobileParams = new URLSearchParams();
    if (reference) mobileParams.set("reference", reference);
    if (planId) mobileParams.set("plan_id", planId);
    return mobileParams.toString()
      ? `${MOBILE_CALLBACK_SCHEME}?${mobileParams.toString()}`
      : MOBILE_CALLBACK_SCHEME;
  }, [planId, reference]);

  useEffect(() => {
    invalidatePlan();

    if (source === "mobile") {
      setAttemptedDeepLink(true);
      window.location.replace(mobileTarget);
      return;
    }

    const timer = setTimeout(() => {
      router.replace("/plans");
    }, 2500);
    return () => clearTimeout(timer);
  }, [invalidatePlan, mobileTarget, router, source]);

  if (source === "mobile") {
    return (
      <div className="min-h-screen bg-neutral-50 px-5 py-8 flex items-center justify-center">
        <div className="w-full max-w-sm rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 flex items-center justify-center mb-5">
            <ShieldCheck size={24} className="text-blue-600" strokeWidth={1.8} />
          </div>

          <h1 className="text-xl font-semibold text-neutral-900">
            Payment received
          </h1>
          <p className="text-sm text-neutral-600 mt-3 leading-relaxed">
            We&apos;re confirming your upgrade and sending you back to the Kotoku app.
            If the app did not open automatically, tap the button below.
          </p>

          {reference ? (
            <p className="text-xs text-neutral-500 mt-4 break-all">
              Reference: <span className="font-medium text-neutral-700">{reference}</span>
            </p>
          ) : null}

          <div className="mt-6 flex flex-col gap-3">
            <a
              href={mobileTarget}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-neutral-900 px-4 py-3 text-sm font-medium text-white"
            >
              Return to Kotoku <ExternalLink size={14} strokeWidth={2} />
            </a>
            <button
              type="button"
              onClick={() => {
                setAttemptedDeepLink(true);
                window.location.replace(mobileTarget);
              }}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border border-neutral-300 px-4 py-3 text-sm font-medium text-neutral-700"
            >
              Try again <RefreshCw size={14} strokeWidth={2} />
            </button>
          </div>

          <p className="text-xs text-neutral-500 mt-5">
            {attemptedDeepLink
              ? "If nothing happens, open the Kotoku app manually and check your subscription."
              : "This page will try to reopen the app automatically."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-50 px-5 py-8 flex items-center justify-center">
      <div className="w-full max-w-sm rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm text-center">
        <div className="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center mx-auto mb-5">
          <ShieldCheck size={28} className="text-blue-600" strokeWidth={1.8} />
        </div>

        <h1 className="text-xl font-bold text-neutral-900">Payment received</h1>
        <p className="text-sm text-neutral-500 mt-3 leading-relaxed">
          Your plan is being updated. You&apos;ll be redirected back to plans shortly.
        </p>

        <div className="flex justify-center gap-1.5 mt-6">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>

        <div className="mt-6">
          <Link
            href="/plans"
            className="inline-flex items-center justify-center rounded-2xl border border-neutral-300 px-4 py-3 text-sm font-medium text-neutral-700"
          >
            Go to plans now
          </Link>
        </div>
      </div>
    </div>
  );
}
