"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircle, CheckCircle2, Clock3, ExternalLink, RefreshCw, ShieldCheck } from "lucide-react";
import { paymentsApi, type CheckoutStatusResponse } from "@/api/payments";
import { useInvalidatePlan } from "@/hooks/usePlan";

const MOBILE_CALLBACK_SCHEME = "kotoku://payment/callback";
const CONFIRMATION_TIMEOUT_MS = 45_000;

export default function PaymentCallbackPage() {
  return (
    <Suspense fallback={<PaymentCallbackFallback />}>
      <PaymentCallbackContent />
    </Suspense>
  );
}

function PaymentCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const invalidatePlan = useInvalidatePlan();
  const [attemptedDeepLink, setAttemptedDeepLink] = useState(false);

  const source = searchParams.get("source");
  const reference = searchParams.get("reference");
  const planId = searchParams.get("plan_id");
  const paymentState = searchParams.get("payment_state");
  const [status, setStatus] = useState<CheckoutStatusResponse | null>(null);
  const [loading, setLoading] = useState(source !== "mobile");
  const [error, setError] = useState<string | null>(null);
  const [timedOut, setTimedOut] = useState(false);
  const [cancelSyncing, setCancelSyncing] = useState(paymentState === "cancelled" && source !== "mobile");

  const mobileTarget = useMemo(() => {
    const mobileParams = new URLSearchParams();
    if (reference) mobileParams.set("reference", reference);
    if (planId) mobileParams.set("plan_id", planId);
    if (paymentState) mobileParams.set("payment_state", paymentState);
    return mobileParams.toString()
      ? `${MOBILE_CALLBACK_SCHEME}?${mobileParams.toString()}`
      : MOBILE_CALLBACK_SCHEME;
  }, [paymentState, planId, reference]);

  useEffect(() => {
    invalidatePlan();

    if (source === "mobile") {
      setAttemptedDeepLink(true);
      window.location.replace(mobileTarget);
      return;
    }

  }, [invalidatePlan, mobileTarget, source]);

  useEffect(() => {
    if (source === "mobile" || paymentState === "cancelled" || !reference || timedOut) return;
    const timer = setTimeout(() => setTimedOut(true), CONFIRMATION_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, [paymentState, reference, source, timedOut]);

  useEffect(() => {
    if (source === "mobile" || paymentState === "cancelled" || !reference) return;

    let active = true;
    let intervalId: ReturnType<typeof setInterval> | null = null;

    const loadStatus = async () => {
      try {
        const next = await paymentsApi.checkoutStatus(reference);
        if (!active) return;
        setStatus(next);
        setError(null);
        if (next.checkout_status === "succeeded") {
          invalidatePlan();
          setLoading(false);
          window.setTimeout(() => {
            if (active) router.replace("/plans");
          }, 1200);
          return;
        }
        if (next.checkout_status === "failed" || next.checkout_status === "cancelled") {
          setLoading(false);
          if (intervalId) clearInterval(intervalId);
          return;
        }
        setLoading(false);
      } catch (err) {
        if (!active) return;
        const message = err instanceof Error ? err.message : "Could not confirm payment yet.";
        setError(message);
        setLoading(false);
      }
    };

    void loadStatus();
    intervalId = setInterval(() => {
      if (timedOut) return;
      void loadStatus();
    }, 2000);

    return () => {
      active = false;
      if (intervalId) clearInterval(intervalId);
    };
  }, [invalidatePlan, paymentState, reference, router, source, timedOut]);

  useEffect(() => {
    if (source === "mobile" || paymentState !== "cancelled") return;

    let active = true;
    const syncCancellation = async () => {
      setCancelSyncing(true);
      try {
        await paymentsApi.cancelCheckout();
      } catch {
        // Ignore: plans screen still offers manual cancel/retry if needed.
      } finally {
        if (active) setCancelSyncing(false);
      }
    };
    void syncCancellation();
    return () => {
      active = false;
    };
  }, [paymentState, source]);

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

  if (paymentState === "cancelled") {
    return (
      <div className="min-h-screen bg-neutral-50 px-5 py-8 flex items-center justify-center">
        <div className="w-full max-w-sm rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm text-center">
          <div className="w-16 h-16 rounded-full bg-amber-50 flex items-center justify-center mx-auto mb-5">
            <AlertCircle size={28} className="text-amber-600" strokeWidth={1.8} />
          </div>

          <h1 className="text-xl font-bold text-neutral-900">Payment cancelled</h1>
          <p className="text-sm text-neutral-500 mt-3 leading-relaxed">
            {cancelSyncing
              ? "Finalising the cancelled checkout before you return to plans."
              : "Your checkout was cancelled before confirmation. You can start again whenever you're ready."}
          </p>

          {reference ? (
            <p className="text-xs text-neutral-500 mt-4 break-all">
              Reference: <span className="font-medium text-neutral-700">{reference}</span>
            </p>
          ) : null}

          <div className="mt-6">
            <Link
              href="/plans"
              className="inline-flex items-center justify-center rounded-2xl border border-neutral-300 px-4 py-3 text-sm font-medium text-neutral-700"
            >
              Back to plans
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!reference) {
    return (
      <div className="min-h-screen bg-neutral-50 px-5 py-8 flex items-center justify-center">
        <div className="w-full max-w-sm rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm text-center">
          <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-5">
            <AlertCircle size={28} className="text-red-600" strokeWidth={1.8} />
          </div>
          <h1 className="text-xl font-bold text-neutral-900">Missing payment reference</h1>
          <p className="text-sm text-neutral-500 mt-3 leading-relaxed">
            We could not confirm this payment session. Return to plans and try again if needed.
          </p>
          <div className="mt-6">
            <Link
              href="/plans"
              className="inline-flex items-center justify-center rounded-2xl border border-neutral-300 px-4 py-3 text-sm font-medium text-neutral-700"
            >
              Back to plans
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (status?.checkout_status === "failed" || status?.checkout_status === "cancelled") {
    const cancelled = status.checkout_status === "cancelled";
    return (
      <div className="min-h-screen bg-neutral-50 px-5 py-8 flex items-center justify-center">
        <div className="w-full max-w-sm rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm text-center">
          <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-5 ${cancelled ? "bg-amber-50" : "bg-red-50"}`}>
            <AlertCircle size={28} className={cancelled ? "text-amber-600" : "text-red-600"} strokeWidth={1.8} />
          </div>
          <h1 className="text-xl font-bold text-neutral-900">
            {cancelled ? "Payment cancelled" : "Payment not confirmed"}
          </h1>
          <p className="text-sm text-neutral-500 mt-3 leading-relaxed">
            {status.detail}
          </p>
          <p className="text-xs text-neutral-500 mt-4 break-all">
            Reference: <span className="font-medium text-neutral-700">{reference}</span>
          </p>
          <div className="mt-6">
            <Link
              href="/plans"
              className="inline-flex items-center justify-center rounded-2xl border border-neutral-300 px-4 py-3 text-sm font-medium text-neutral-700"
            >
              Back to plans
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (timedOut) {
    return (
      <div className="min-h-screen bg-neutral-50 px-5 py-8 flex items-center justify-center">
        <div className="w-full max-w-sm rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm text-center">
          <div className="w-16 h-16 rounded-full bg-amber-50 flex items-center justify-center mx-auto mb-5">
            <Clock3 size={28} className="text-amber-600" strokeWidth={1.8} />
          </div>
          <h1 className="text-xl font-bold text-neutral-900">Still confirming payment</h1>
          <p className="text-sm text-neutral-500 mt-3 leading-relaxed">
            {status?.detail ?? "Your payment may still be processing. Check again in a moment."}
          </p>
          {error ? <p className="text-sm text-amber-700 mt-3">{error}</p> : null}
          <p className="text-xs text-neutral-500 mt-4 break-all">
            Reference: <span className="font-medium text-neutral-700">{reference}</span>
          </p>
          <div className="mt-6 flex flex-col gap-3">
            <button
              type="button"
              onClick={() => {
                setTimedOut(false);
                setLoading(true);
              }}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-neutral-900 px-4 py-3 text-sm font-medium text-white"
            >
              Check again <RefreshCw size={14} strokeWidth={2} />
            </button>
            <Link
              href="/plans"
              className="inline-flex items-center justify-center rounded-2xl border border-neutral-300 px-4 py-3 text-sm font-medium text-neutral-700"
            >
              Back to plans
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-50 px-5 py-8 flex items-center justify-center">
      <div className="w-full max-w-sm rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm text-center">
        <div className="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center mx-auto mb-5">
          {status?.checkout_status === "pending" ? (
            <Clock3 size={28} className="text-blue-600" strokeWidth={1.8} />
          ) : status?.checkout_status === "succeeded" ? (
            <CheckCircle2 size={28} className="text-green-600" strokeWidth={1.8} />
          ) : (
            <ShieldCheck size={28} className="text-blue-600" strokeWidth={1.8} />
          )}
        </div>

        <h1 className="text-xl font-bold text-neutral-900">
          {status?.checkout_status === "succeeded" ? "Upgrade confirmed" : "Confirming payment"}
        </h1>
        <p className="text-sm text-neutral-500 mt-3 leading-relaxed">
          {status?.detail ??
            "Your plan is being updated. We only complete this flow after the backend confirms the transaction."}
        </p>

        {error ? <p className="text-sm text-amber-700 mt-3">{error}</p> : null}
        <p className="text-xs text-neutral-500 mt-4 break-all">
          Reference: <span className="font-medium text-neutral-700">{reference}</span>
        </p>

        <div className="flex justify-center gap-1.5 mt-6">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className={`w-1.5 h-1.5 rounded-full ${loading ? "bg-blue-400 animate-bounce" : "bg-green-400"}`}
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

function PaymentCallbackFallback() {
  return (
    <div className="min-h-screen bg-neutral-50 px-5 py-8 flex items-center justify-center">
      <div className="w-full max-w-sm rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm text-center">
        <div className="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center mx-auto mb-5">
          <ShieldCheck size={28} className="text-blue-600" strokeWidth={1.8} />
        </div>

        <h1 className="text-xl font-bold text-neutral-900">Loading payment status</h1>
        <p className="text-sm text-neutral-500 mt-3 leading-relaxed">
          Preparing your return flow.
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
      </div>
    </div>
  );
}
