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
): Promise<InitiatePaymentResponse> {
  const res = await apiClient.post<ApiResponse<InitiatePaymentResponse>>(
    "/payments/initiate/",
    callbackUrl ? { plan_id: planId, callback_url: callbackUrl } : { plan_id: planId }
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
