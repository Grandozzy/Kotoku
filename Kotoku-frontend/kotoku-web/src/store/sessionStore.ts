import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SessionState {
  // accessToken is intentionally NOT persisted — lives in memory only.
  // On page refresh it starts null; the first 401 triggers a silent refresh
  // via refreshToken which restores it without the user noticing.
  accessToken: string | null;
  // refreshToken IS persisted so the session survives page refreshes.
  refreshToken: string | null;
  accountId: number | null;
  phone: string | null;
  isAuthenticated: boolean;
  setSession: (accessToken: string, refreshToken: string, accountId: number, phone: string) => void;
  setAccessToken: (accessToken: string) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      accountId: null,
      phone: null,
      isAuthenticated: false,
      setSession: (accessToken, refreshToken, accountId, phone) =>
        set({ accessToken, refreshToken, accountId, phone, isAuthenticated: true }),
      setAccessToken: (accessToken) => set({ accessToken }),
      clearSession: () =>
        set({ accessToken: null, refreshToken: null, accountId: null, phone: null, isAuthenticated: false }),
    }),
    {
      name: "kotoku-session",
      // Only persist what's needed for session restore — never the access token.
      partialize: (state) => ({
        refreshToken: state.refreshToken,
        accountId: state.accountId,
        phone: state.phone,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
