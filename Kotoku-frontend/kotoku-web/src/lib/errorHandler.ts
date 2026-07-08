export function getApiErrorMessage(
  error: unknown,
  fallback = "Something went wrong. Please try again.",
): string {
  const candidate = error as {
    response?: { data?: Record<string, unknown> };
    message?: string;
  } | null;

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
