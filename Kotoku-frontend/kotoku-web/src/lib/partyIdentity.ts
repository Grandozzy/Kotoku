import type { Party } from "@/types/agreement";

export const GHANA_CARD_PIN_REGEX = /^GHA-\d{9}-\d$/;

const IDENTITY_FAILURE_MESSAGES: Record<string, string> = {
  ghana_card_markers_missing: "The uploaded document does not look like a Ghana Card. Upload a clear photo of the actual card.",
  ocr_pin_missing: "We could not read the Ghana Card PIN from the card image. Retake the photo with sharper focus and less glare.",
  ocr_pin_mismatch: "The Ghana Card PIN on the image does not match the PIN entered for this party.",
  ocr_name_mismatch: "The name read from the Ghana Card does not match the party name entered.",
  selfie_face_missing: "No face was detected in the selfie. Retake the selfie with the full face visible.",
  face_match_failed: "The selfie does not appear to match the Ghana Card portrait. Retake both images in better lighting.",
  face_match_manual_review: "The selfie and card portrait are close, but need manual review.",
  verification_unavailable: "Identity verification is temporarily unavailable. Kotoku will retry automatically.",
  verification_unexpected_failure: "Identity verification failed unexpectedly. Retry the uploads for this party.",
};

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

export function identityEvidenceType(role: string, side: "front" | "back" | "selfie"): string {
  if (side === "selfie") return `${role}_selfie`;
  return `${role}_ghana_card_${side}`;
}

export function isPartyIdentityComplete(party: Party): boolean {
  if (party.role === "witness") return true;
  return (
    GHANA_CARD_PIN_REGEX.test(normalizeGhanaCardPin(party.id_number ?? "")) &&
    party.ghana_card_front_uploaded &&
    party.ghana_card_back_uploaded &&
    party.identity_selfie_uploaded &&
    party.identity_verification_status === "verified"
  );
}

export function describeIdentityFailureCodes(codes: string[]): string[] {
  return codes
    .map((code) => IDENTITY_FAILURE_MESSAGES[code] ?? null)
    .filter((message): message is string => Boolean(message));
}

export function buildIdentityStatusMessage(party: Party): string {
  const detail = party.identity_verification_detail?.trim();
  const mapped = describeIdentityFailureCodes(party.identity_verification_failure_codes ?? []);
  if (mapped.length > 0) return mapped.join(" ");
  if (detail) return detail;
  if (party.identity_verification_status === "processing") {
    return "We are checking the Ghana Card details and selfie match now.";
  }
  if (party.identity_verification_status === "pending") {
    return "Finish the uploads and wait for the backend verification result.";
  }
  return "Awaiting Ghana Card verification.";
}
