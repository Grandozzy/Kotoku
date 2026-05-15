import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface SessionState {
  // accessToken lives in memory only — never persisted.
  accessToken: string | null;
  // refreshToken is persisted to sessionStorage (not localStorage) so it:
  //   1. Survives same-tab page refreshes (user can navigate back without re-login).
  //   2. Is cleared automatically when the tab/window closes.
  //   3. Is NOT shared across tabs, limiting the blast radius of an XSS leak.
  // NOTE: sessionStorage is still JS-readable. The proper long-term fix is
  // httpOnly cookies for the refresh token + CSRF tokens for mutations.
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
      storage: createJSONStorage(() => sessionStorage),
      // Never persist the access token — it lives in memory only.
      partialize: (state) => ({
        refreshToken: state.refreshToken,
        accountId: state.accountId,
        phone: state.phone,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
