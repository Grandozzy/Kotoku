import { api } from "@/lib/apiClient";

export interface PlanInfo {
  id: string;
  family: "personal" | "enterprise";
  name: string;
  price_currency: string;
  price_amount_monthly: number;
  max_agreements_per_month: number;
  retention_months: number;
  features: {
    team_seats: number;
    bulk_creation: boolean;
    reporting: boolean;
    archive_search: boolean;
  };
}

export interface PlanUsage {
  period: { start: string; end: string };
  sealed_agreements_this_period: number;
  remaining_agreements_this_period: number;
  is_cap_reached: boolean;
  is_near_cap: boolean;
}

export interface PlanFlags {
  is_personal: boolean;
  is_enterprise: boolean;
  business_usage_suspected: boolean;
  show_upgrade_recommendation: boolean;
}

export interface UpgradeOption {
  id: string;
  name: string;
  family: string;
  price_currency: string;
  price_amount_monthly: number;
  max_agreements_per_month: number;
}

export interface CurrentPlanResponse {
  plan: PlanInfo;
  usage: PlanUsage;
  flags: PlanFlags;
  recommended_upgrades: UpgradeOption[];
}

export const billingApi = {
  currentPlan: () =>
    api
      .get<{ status: string; data: CurrentPlanResponse }>("/api/billing/current-plan/")
      .then((r) => r.data),
};
