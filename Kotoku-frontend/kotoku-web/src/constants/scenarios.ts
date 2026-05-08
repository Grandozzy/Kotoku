import type { PartyRole, IdType } from "@/types/party";

export interface FieldDef {
  key: string;
  label: string;
  type: "text" | "number" | "select" | "date" | "boolean";
  placeholder?: string;
  required?: boolean;
  options?: { value: string; label: string }[];
  section: string;
}

export interface ScenarioDef {
  id: string;
  label: string;
  description: string;
  icon: string;
  roles: PartyRole[];
  fields: FieldDef[];
  evidenceRequirements: string[];
}

export const SCENARIOS: ScenarioDef[] = [
  {
    id: "used_vehicle_sale",
    label: "Used vehicle sale",
    description: "Buying or selling a used car, motorbike, or other vehicle.",
    icon: "🚗",
    roles: ["seller", "buyer"],
    evidenceRequirements: [
      "At least 3 vehicle photos",
      "ID photo for seller",
      "ID photo for buyer",
    ],
    fields: [
      { key: "vehicle_type", label: "Vehicle type", type: "select", section: "Vehicle", required: true, options: [{ value: "car", label: "Car" }, { value: "motorbike", label: "Motorbike" }, { value: "other", label: "Other" }] },
      { key: "make", label: "Make", type: "text", placeholder: "e.g. Toyota", section: "Vehicle", required: true },
      { key: "model", label: "Model", type: "text", placeholder: "e.g. Corolla", section: "Vehicle", required: true },
      { key: "year_of_manufacture", label: "Year", type: "number", placeholder: "e.g. 2018", section: "Vehicle", required: true },
      { key: "registration_number", label: "Registration number", type: "text", placeholder: "e.g. GR-1234-21", section: "Vehicle" },
      { key: "vin_or_chassis", label: "VIN / Chassis number", type: "text", section: "Vehicle" },
      { key: "current_mileage", label: "Current mileage (km)", type: "number", section: "Vehicle" },
      { key: "colour", label: "Colour", type: "text", section: "Vehicle" },
      { key: "overall_condition", label: "Overall condition", type: "select", section: "Condition", required: true, options: [{ value: "excellent", label: "Excellent" }, { value: "good", label: "Good" }, { value: "fair", label: "Fair" }, { value: "poor", label: "Poor" }] },
      { key: "known_mechanical_issues", label: "Known mechanical issues", type: "text", placeholder: "None, or describe...", section: "Condition" },
      { key: "accident_history_notes", label: "Accident history", type: "text", placeholder: "None, or describe...", section: "Condition" },
      { key: "seller_is_owner_confirmed", label: "Seller is the registered owner", type: "boolean", section: "Ownership", required: true },
      { key: "vehicle_not_under_finance_confirmed", label: "Vehicle is not under finance", type: "boolean", section: "Ownership", required: true },
      { key: "registration_documents_available", label: "Registration documents available at handover", type: "boolean", section: "Ownership" },
      { key: "total_price_amount", label: "Agreed price (GHS)", type: "number", section: "Price & Payment", required: true },
      { key: "payment_type", label: "Payment method", type: "select", section: "Price & Payment", required: true, options: [{ value: "cash", label: "Cash" }, { value: "mobile_money", label: "Mobile money" }, { value: "bank_transfer", label: "Bank transfer" }, { value: "instalment", label: "Instalments" }] },
      { key: "agreement_date", label: "Agreement date", type: "date", section: "Handover", required: true },
      { key: "handover_date", label: "Handover date", type: "date", section: "Handover" },
      { key: "handover_location", label: "Handover location", type: "text", placeholder: "e.g. Seller's address", section: "Handover" },
    ],
  },
  {
    id: "room_rental",
    label: "Room rental",
    description: "Renting a room, apartment, or property.",
    icon: "🏠",
    roles: ["landlord", "tenant"],
    evidenceRequirements: [
      "At least 2 property photos",
      "ID photo for landlord",
      "ID photo for tenant",
      "Condition photo (if deposit set)",
    ],
    fields: [
      { key: "property_address", label: "Property address", type: "text", placeholder: "Full address", section: "Property", required: true },
      { key: "room_or_unit_description", label: "Room / unit description", type: "text", placeholder: "e.g. Self-contained room, 2nd floor", section: "Property", required: true },
      { key: "property_type", label: "Property type", type: "select", section: "Property", options: [{ value: "room", label: "Single room" }, { value: "apartment", label: "Apartment" }, { value: "house", label: "House" }, { value: "other", label: "Other" }] },
      { key: "furnished", label: "Furnished", type: "boolean", section: "Property" },
      { key: "monthly_rent_amount", label: "Monthly rent (GHS)", type: "number", section: "Rent & Deposit", required: true },
      { key: "advance_months", label: "Advance (months)", type: "number", placeholder: "e.g. 2", section: "Rent & Deposit" },
      { key: "deposit_amount", label: "Security deposit (GHS)", type: "number", placeholder: "0 if none", section: "Rent & Deposit" },
      { key: "deposit_conditions", label: "Deposit return conditions", type: "text", placeholder: "e.g. Full refund if no damage", section: "Rent & Deposit" },
      { key: "payment_due_day", label: "Rent due day of month", type: "number", placeholder: "e.g. 1", section: "Rent & Deposit" },
      { key: "lease_start_date", label: "Lease start date", type: "date", section: "Duration", required: true },
      { key: "lease_end_date", label: "Lease end date", type: "date", section: "Duration" },
      { key: "lease_type", label: "Lease type", type: "select", section: "Duration", options: [{ value: "fixed", label: "Fixed term" }, { value: "periodic", label: "Periodic (month-to-month)" }] },
      { key: "notice_period_days", label: "Notice period (days)", type: "number", placeholder: "e.g. 30", section: "Duration" },
      { key: "utilities_included", label: "Utilities included", type: "text", placeholder: "e.g. Water, not electricity", section: "Terms" },
      { key: "subletting_allowed", label: "Subletting allowed", type: "boolean", section: "Terms" },
      { key: "pets_allowed", label: "Pets allowed", type: "boolean", section: "Terms" },
    ],
  },
];

export const SCENARIO_MAP = Object.fromEntries(SCENARIOS.map((s) => [s.id, s]));

export const ROLE_LABEL: Record<string, string> = {
  buyer: "Buyer",
  seller: "Seller",
  landlord: "Landlord",
  tenant: "Tenant",
  witness: "Witness",
};

export const ID_TYPE_LABEL: Record<string, string> = {
  ghana_card: "Ghana Card",
  passport: "Passport",
  other: "Other ID",
};
