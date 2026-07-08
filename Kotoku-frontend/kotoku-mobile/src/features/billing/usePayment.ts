import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";

import { cancelCheckout, cancelSubscription, initiatePayment } from "@/api/payments";
import { WEB_BASE_URL } from "@/constants/config";
import { getApiErrorMessage } from "@/lib/errorHandler";

/**
 * Initiate a Paystack subscription checkout for the given plan.
 * On success, navigates to the checkout WebView with the authorization URL.
 * The backend creates a pending Subscription row; the plan is only promoted
 * after Paystack delivers a verified charge.success webhook.
 */
export function useInitiatePayment() {
  const router = useRouter();

  return useMutation({
    mutationFn: (planId: string) =>
      initiatePayment(
        planId,
        `${WEB_BASE_URL}/payment/callback?source=mobile&plan_id=${encodeURIComponent(planId)}`,
      ),
    onSuccess: (data, planId) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      router.push({
        pathname: "/(main)/payment/checkout" as any,
        params: {
          authorization_url: data.authorization_url,
          reference: data.reference,
          plan_id: planId,
        },
      });
    },
    onError: (error) => {
      // Caller is responsible for surfacing this via getApiErrorMessage(error)
      console.warn("[useInitiatePayment] error:", getApiErrorMessage(error));
    },
  });
}

/**
 * Cancel an open (pending/charged) checkout so the account can start a new
 * payment attempt. Safe to call after the user abandons the Paystack WebView —
 * if they actually paid, the webhook will have already closed the checkout.
 */
export function useCancelCheckout() {
  return useMutation({
    mutationFn: cancelCheckout,
    onError: (error) => {
      console.warn("[useCancelCheckout] error:", getApiErrorMessage(error));
    },
  });
}

/**
 * Cancel the active subscription at the end of the current billing period.
 * Account.plan is NOT changed immediately — the backend downgrades it when
 * the period expires via the expire_lapsed_subscriptions task.
 * Invalidates both subscription and plan queries so the UI reflects the
 * cancel_at_period_end flag immediately.
 */
export function useCancelSubscription() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: cancelSubscription,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billing", "subscription"] });
      queryClient.invalidateQueries({ queryKey: ["billing", "current-plan"] });
    },
    onError: (error) => {
      console.warn("[useCancelSubscription] error:", getApiErrorMessage(error));
    },
  });
}
