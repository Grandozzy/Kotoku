import type { Party } from "@/types/agreement";

export const GHANA_CARD_PIN_REGEX = /^GHA-\d{9}-\d$/;

export function normalizeGhanaCardPin(value: string): string {
  return value.trim().toUpperCase();
}

export function formatGhanaCardPin(raw: string): string {
  const digits = raw.replace(/\D/g, "").slice(0, 10);
  if (!digits) return "";
  let out = "GHA-" + digits.slice(0, 9);
  if (digits.length > 9) out += "-" + digits[9];
  return out;
}

export function identityEvidenceType(role: string, side: "front" | "back"): string {
  return `${role}_ghana_card_${side}`;
}

export function isPartyIdentityComplete(party: Party): boolean {
  if (party.role === "witness") return true;
  return (
    GHANA_CARD_PIN_REGEX.test(normalizeGhanaCardPin(party.id_number ?? "")) &&
    party.ghana_card_front_uploaded &&
    party.ghana_card_back_uploaded
  );
}
