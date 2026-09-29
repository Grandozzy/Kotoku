import type { Party } from "@/types/agreement";

export const GHANA_CARD_PIN_REGEX = /^GHA-\d{9}-\d$/;

const IDENTITY_FAILURE_MESSAGES: Record<string, string> = {
  ghana_card_markers_missing: "The uploaded document does not look like a Ghana Card. Upload a clear photo of the actual card.",
  ocr_pin_missing: "We could not read the Ghana Card Number from the card image. Retake the photo with sharper focus and less glare.",
  ocr_pin_mismatch: "The Ghana Card Number on the image does not match the number entered for this party.",
  ocr_name_mismatch: "The name read from the Ghana Card does not match the party name entered.",
  selfie_face_missing: "No face was detected. Try the face check again in better lighting.",
  face_match_failed: "The face check did not match the Ghana Card portrait. Try again in better lighting.",
  face_match_manual_review: "The face and card portrait are close, but need manual review.",
  verification_unavailable: "Identity verification is temporarily unavailable. Kotoku will retry automatically.",
  verification_unexpected_failure: "Identity verification failed unexpectedly. Retry the uploads for this party.",
  card_front_invalid: "The Ghana Card front image could not be read. Retake it as a JPG image.",
  card_back_invalid: "The Ghana Card back image could not be read. Retake it as a JPG image.",
  card_front_resolution_too_low: "The Ghana Card front image is too small. Move closer and retake it.",
  card_back_resolution_too_low: "The Ghana Card back image is too small. Move closer and retake it.",
  card_front_blurry: "The Ghana Card front image is blurry. Hold steady and retake it.",
  card_back_blurry: "The Ghana Card back image is blurry. Hold steady and retake it.",
  card_front_too_dark: "The Ghana Card front image is too dark. Retake it in even lighting.",
  card_back_too_dark: "The Ghana Card back image is too dark. Retake it in even lighting.",
  card_front_overexposed: "The Ghana Card front has too much glare. Change the angle and retake it.",
  card_back_overexposed: "The Ghana Card back has too much glare. Change the angle and retake it.",
  manual_review_rejected: "The identity check was rejected after review. Retake the card photos and face check.",
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

export function identityEvidenceType(role: Party["role"], side: "front" | "back" | "selfie"): string {
  if (side === "selfie") return `${role}_selfie`;
  return `${role}_ghana_card_${side}`;
}

export function isPartyIdentityComplete(party: Party): boolean {
  if (party.role === "witness") return true;
  const livenessOrSelfie = party.livenessStatus === "passed" || party.identitySelfieUploaded;
  return (
    GHANA_CARD_PIN_REGEX.test(normalizeGhanaCardPin(party.idNumber)) &&
    party.ghanaCardFrontUploaded &&
    party.ghanaCardBackUploaded &&
    livenessOrSelfie &&
    party.identityVerificationStatus === "verified"
  );
}

export function describeIdentityFailureCodes(codes: string[]): string[] {
  return codes
    .map((code) => IDENTITY_FAILURE_MESSAGES[code] ?? null)
    .filter((message): message is string => Boolean(message));
}

export function buildIdentityStatusMessage(party: Party): string {
  const detail = party.identityVerificationDetail?.trim();
  const mapped = describeIdentityFailureCodes(party.identityVerificationFailureCodes);
  if (mapped.length > 0) {
    return mapped.join(" ");
  }
  if (detail) {
    return detail;
  }
  if (party.identityVerificationStatus === "processing") {
    return "Verifying Ghana Card details now.";
  }
  if (party.livenessStatus === "failed") {
    return "Face check failed. Try again.";
  }
  if (party.livenessStatus === "passed") {
    return "Face check passed. Upload the Ghana Card images to complete verification.";
  }
  return "Awaiting Ghana Card verification.";
}
