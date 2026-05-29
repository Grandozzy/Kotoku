import { api } from "@/lib/apiClient";

interface InitiateResponse {
  authorization_url: string;
  access_code: string;
  reference: string;
}

export const paymentsApi = {
  initiate: (planId: string, callbackUrl: string) =>
    api.post<InitiateResponse>("/api/payments/initiate/", {
      plan_id: planId,
      callback_url: callbackUrl,
    }),
};
