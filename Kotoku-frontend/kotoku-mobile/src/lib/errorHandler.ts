import { AxiosError } from "axios";

/**
 * Pulls a user-facing message out of an Axios error response.
 * Falls back to `fallback` if the shape is unexpected.
 *
 * Backend returns: { status: "error", message: "..." }
 * DRF validation returns: { detail: "..." } or { field: ["msg"] }
 */
export function getApiErrorMessage(
  error: unknown,
  fallback = "Something went wrong. Please try again.",
): string {
  if (error instanceof AxiosError) {
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
  return fallback;
}
