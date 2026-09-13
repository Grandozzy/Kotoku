export function getApiErrorMessage(
  error: unknown,
  fallback = "Something went wrong. Please try again.",
): string {
  const candidate = error as {
    response?: { data?: Record<string, unknown> };
    status?: number;
    body?: Record<string, unknown>;
    retryAfter?: string | null;
    message?: string;
  } | null;

  if (candidate?.status === 429) {
    const headerSeconds = Number(candidate.retryAfter);
    const detail = typeof candidate.body?.detail === "string"
      ? candidate.body.detail
      : candidate.message ?? "";
    const match = detail.match(/(?:available|retry|again)\D+(\d+)\s*seconds?/i);
    const seconds = Number.isFinite(headerSeconds) && headerSeconds > 0
      ? Math.ceil(headerSeconds)
      : match
        ? Number(match[1])
        : null;
    if (!seconds) return "Too many requests. Please wait before trying again.";
    if (seconds < 60) {
      return `Too many requests. Try again in ${seconds} second${seconds === 1 ? "" : "s"}.`;
    }
    const minutes = Math.ceil(seconds / 60);
    if (minutes < 60) {
      return `Too many requests. Try again in ${minutes} minute${minutes === 1 ? "" : "s"}.`;
    }
    const hours = Math.ceil(minutes / 60);
    return `Too many requests. Try again in ${hours} hour${hours === 1 ? "" : "s"}.`;
  }

  if (candidate?.response?.data) {
    const data = candidate.response.data;
    if (!data) return fallback;
    if (typeof data.message === "string") return data.message;
    if (typeof data.detail === "string") return data.detail;
    const firstField = Object.values(data)[0];
    if (Array.isArray(firstField) && typeof firstField[0] === "string") {
      return firstField[0];
    }
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

export function getApiErrorCode(error: unknown): string | null {
  const candidate = error as {
    response?: { data?: Record<string, unknown> };
  } | null;
  const code = candidate?.response?.data?.code;
  return typeof code === "string" ? code : null;
}
