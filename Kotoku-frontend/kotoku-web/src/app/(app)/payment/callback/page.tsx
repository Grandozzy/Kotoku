"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ShieldCheck } from "lucide-react";
import { useInvalidatePlan } from "@/hooks/usePlan";

// Paystack redirects here after the user completes (or closes) checkout.
// The actual plan change is applied by the backend webhook → Celery task,
// so we just invalidate the plan cache and send the user back to /plans.

const MOBILE_CALLBACK_SCHEME = "kotoku://payment/callback";

export default function PaymentCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const invalidatePlan = useInvalidatePlan();

  useEffect(() => {
    // Bust the cached plan so /plans shows fresh state after the redirect.
    invalidatePlan();

    const source = searchParams.get("source");
    const reference = searchParams.get("reference");
    const planId = searchParams.get("plan_id");

    if (source === "mobile") {
      const mobileParams = new URLSearchParams();
      if (reference) mobileParams.set("reference", reference);
      if (planId) mobileParams.set("plan_id", planId);
      const target = mobileParams.toString()
        ? `${MOBILE_CALLBACK_SCHEME}?${mobileParams.toString()}`
        : MOBILE_CALLBACK_SCHEME;
      window.location.replace(target);
    }

    const timer = setTimeout(() => {
      router.replace("/plans");
    }, 3000);

    return () => clearTimeout(timer);
  }, [invalidatePlan, router, searchParams]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 text-center">
      <div className="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center">
        <ShieldCheck size={28} className="text-blue-600" strokeWidth={1.8} />
      </div>

      <div>
        <h1 className="text-xl font-bold text-neutral-900">Payment received</h1>
        <p className="text-sm text-neutral-500 mt-2 max-w-xs mx-auto leading-relaxed">
          Your plan is being updated. If you started payment from the app, you can return there now.
        </p>
      </div>

      <div className="flex gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  );
}
