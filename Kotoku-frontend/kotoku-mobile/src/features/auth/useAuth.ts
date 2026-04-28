import { useSessionStore } from "@/store/sessionStore";
import { useMe } from "./otpFlow";

/**
 * Single hook for auth state consumed by screens and guards.
 * Combines the Zustand session (token, phone) with the server profile (useMe).
 */
export function useAuth() {
  const { token, phone, accountId, isAuthenticated, clearSession } =
    useSessionStore();
  const { data: profile, isLoading: profileLoading } = useMe();

  return {
    isAuthenticated,
    token,
    phone: profile?.phone ?? phone,
    accountId: profile?.id ?? accountId,
    profileLoading,
    clearSession,
  };
}
