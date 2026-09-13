import { AxiosError } from "axios";

function retryAfterSeconds(error: AxiosError): number | null {
  const header = error.response?.headers?.["retry-after"];
  const parsedHeader = Number(Array.isArray(header) ? header[0] : header);
  if (Number.isFinite(parsedHeader) && parsedHeader > 0) {
    return Math.ceil(parsedHeader);
  }

  const data = error.response?.data as { detail?: unknown } | undefined;
  const detail = typeof data?.detail === "string" ? data.detail : "";
  const match = detail.match(/(?:available|retry|again)\D+(\d+)\s*seconds?/i);
  return match ? Number(match[1]) : null;
}

function formatRetryDuration(seconds: number): string {
  if (seconds < 60) return `${seconds} second${seconds === 1 ? "" : "s"}`;
  const minutes = Math.ceil(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"}`;
  const hours = Math.ceil(minutes / 60);
  return `${hours} hour${hours === 1 ? "" : "s"}`;
}

/**
 * Pulls a user-facing message out of an Axios error response.
 * Falls back to `fallback` if the shape is unexpected.
 *
 * Backend returns: { status: "error", message: "..." }
 * DRF validation returns: { detail: "..." } or { field: ["msg"] }
 */
/** Returns true when the backend rejected because the account is at its monthly seal cap. */
export function isCapReachedError(error: unknown): boolean {
  if (error instanceof AxiosError) {
    const msg: string = error.response?.data?.message ?? "";
    return msg.startsWith("PLAN_CAP_REACHED");
  }
  return false;
}

export function getApiErrorCode(error: unknown): string | null {
  if (error instanceof AxiosError) {
    const code = error.response?.data?.code;
    return typeof code === "string" ? code : null;
  }
  return null;
}

export function getApiErrorMessage(
  error: unknown,
  fallback = "Something went wrong. Please try again.",
): string {
  if (error instanceof AxiosError) {
    if (error.response?.status === 429) {
      const seconds = retryAfterSeconds(error);
      return seconds
        ? `Too many requests. Try again in ${formatRetryDuration(seconds)}.`
        : "Too many requests. Please wait before trying again.";
    }
    const data = error.response?.data;
    if (!data) return fallback;

    // Kotoku envelope
    if (typeof data.message === "string") return data.message;
    // DRF detail
    if (typeof data.detail === "string") return data.detail;
    // DRF field errors — return first one
    const firstField = Object.values(data)[0];
    if (Array.isArray(firstField) && typeof firstField[0] === "string") {
      return firstField[0];
    }
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}
