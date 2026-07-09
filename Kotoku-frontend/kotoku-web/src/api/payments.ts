import { api } from "@/lib/apiClient";

interface InitiateResponse {
  authorization_url: string;
  access_code: string;
  reference: string;
}

export type PaymentChannel = "card" | "mobile_money";
export type PaymentInitiationMode = "subscription" | "recovery";

export interface SubscriptionStatusResponse {
  has_subscription: boolean;
  plan_id: string | null;
  status: "pending" | "active" | "paused" | "cancelled" | "past_due" | "expired" | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

export type CheckoutStatus =
  | "pending"
  | "processing"
  | "succeeded"
  | "failed"
  | "cancelled";

export interface CheckoutStatusResponse {
  reference: string;
  checkout_status: CheckoutStatus;
  target_plan_id: string;
  current_plan_id: string | null;
  subscription_status: string | null;
  detail: string;
}

export const paymentsApi = {
  initiate: (
    planId: string,
    callbackUrl: string,
    options?: {
      mode?: PaymentInitiationMode;
      channels?: PaymentChannel[];
    }
  ) =>
    api.post<InitiateResponse>("/api/payments/initiate/", {
      plan_id: planId,
      callback_url: callbackUrl,
      ...(options?.mode ? { mode: options.mode } : {}),
      ...(options?.channels?.length ? { channels: options.channels } : {}),
    }),

  subscriptionStatus: () =>
    api.get<SubscriptionStatusResponse>("/api/payments/subscription/"),

  cancelCheckout: () =>
    api.post<{ cancelled: boolean }>("/api/payments/checkout/cancel/", {}),

  checkoutStatus: (reference: string) =>
    api.get<CheckoutStatusResponse>(
      `/api/payments/checkout-status/?reference=${encodeURIComponent(reference)}`
    ),
};
