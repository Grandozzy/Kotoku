import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface SessionState {
  // accessToken lives in memory only — never persisted.
  accessToken: string | null;
  // refreshToken is HttpOnly-cookie backed by the API and is never readable
  // from JavaScript. Access recovers through /auth/token/refresh/.
  accountId: number | null;
  phone: string | null;
  isAuthenticated: boolean;
  hasHydrated: boolean;
  isBootstrapping: boolean;
  setSession: (accessToken: string, accountId: number, phone: string) => void;
  setAccessToken: (accessToken: string | null) => void;
  setHasHydrated: (hasHydrated: boolean) => void;
  setBootstrapping: (isBootstrapping: boolean) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      accessToken: null,
      accountId: null,
      phone: null,
      isAuthenticated: false,
      hasHydrated: false,
      isBootstrapping: false,
      setSession: (accessToken, accountId, phone) =>
        set({
          accessToken,
          accountId,
          phone,
          isAuthenticated: true,
          isBootstrapping: false,
        }),
      setAccessToken: (accessToken) => set({ accessToken }),
      setHasHydrated: (hasHydrated) => set({ hasHydrated }),
      setBootstrapping: (isBootstrapping) => set({ isBootstrapping }),
      clearSession: () =>
        set({
          accessToken: null,
          accountId: null,
          phone: null,
          isAuthenticated: false,
          isBootstrapping: false,
        }),
    }),
    {
      name: "kotoku-session",
      storage: createJSONStorage(() => localStorage),
      // Never persist the access token — it lives in memory only.
      partialize: (state) => ({
        accountId: state.accountId,
        phone: state.phone,
        isAuthenticated: state.isAuthenticated,
      }),
      version: 3,
      migrate: (persistedState) => {
        const state = persistedState as Partial<SessionState> & { refreshToken?: string };
        delete state.refreshToken;
        return state;
      },
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
        state?.setBootstrapping(false);
      },
    }
  )
);
