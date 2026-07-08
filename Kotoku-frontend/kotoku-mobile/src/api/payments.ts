import { apiClient } from "@/api/client";
import type { ApiResponse } from "@/types/api";

export interface PaymentConfig {
  paystack_public_key: string;
}

export interface InitiatePaymentResponse {
  authorization_url: string;
  access_code: string;
  reference: string;
}

export type PaymentInitiationMode = "subscription" | "recovery";
export type PaymentChannel = "card" | "mobile_money";

export type SubscriptionStatus =
  | "pending"
  | "active"
  | "paused"
  | "cancelled"
  | "past_due"
  | "expired";

export interface SubscriptionStatusResponse {
  has_subscription: boolean;
  plan_id: string | null;
  status: SubscriptionStatus | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

export async function getPaymentConfig(): Promise<PaymentConfig> {
  const res = await apiClient.get<ApiResponse<PaymentConfig>>(
    "/payments/config/"
  );
  return res.data.data;
}

export async function initiatePayment(
  planId: string,
  callbackUrl?: string,
  options?: {
    mode?: PaymentInitiationMode;
    channels?: PaymentChannel[];
  },
): Promise<InitiatePaymentResponse> {
  const payload: {
    plan_id: string;
    callback_url?: string;
    mode?: PaymentInitiationMode;
    channels?: PaymentChannel[];
  } = { plan_id: planId };
  if (callbackUrl) {
    payload.callback_url = callbackUrl;
  }
  if (options?.mode) {
    payload.mode = options.mode;
  }
  if (options?.channels?.length) {
    payload.channels = options.channels;
  }

  const res = await apiClient.post<ApiResponse<InitiatePaymentResponse>>(
    "/payments/initiate/",
    payload,
  );
  return res.data.data;
}

export async function getSubscriptionStatus(): Promise<SubscriptionStatusResponse> {
  const res = await apiClient.get<ApiResponse<SubscriptionStatusResponse>>(
    "/payments/subscription/"
  );
  return res.data.data;
}

export async function cancelSubscription(): Promise<void> {
  await apiClient.post("/payments/cancel/");
}

export async function cancelCheckout(): Promise<{ cancelled: boolean }> {
  const res = await apiClient.post<ApiResponse<{ cancelled: boolean }>>(
    "/payments/checkout/cancel/",
  );
  return res.data.data;
}
