import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface SessionState {
  // accessToken lives in memory only — never persisted.
  accessToken: string | null;
  // refreshToken is HttpOnly-cookie backed by the API and is never readable
  // from JavaScript. Same-tab reloads recover through /auth/token/refresh/.
  accountId: number | null;
  phone: string | null;
  isAuthenticated: boolean;
  setSession: (accessToken: string, accountId: number, phone: string) => void;
  setAccessToken: (accessToken: string) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      accessToken: null,
      accountId: null,
      phone: null,
      isAuthenticated: false,
      setSession: (accessToken, accountId, phone) =>
        set({ accessToken, accountId, phone, isAuthenticated: true }),
      setAccessToken: (accessToken) => set({ accessToken }),
      clearSession: () =>
        set({ accessToken: null, accountId: null, phone: null, isAuthenticated: false }),
    }),
    {
      name: "kotoku-session",
      storage: createJSONStorage(() => sessionStorage),
      // Never persist the access token — it lives in memory only.
      partialize: (state) => ({
        accountId: state.accountId,
        phone: state.phone,
        isAuthenticated: state.isAuthenticated,
      }),
      version: 2,
      migrate: (persistedState) => {
        const state = persistedState as Partial<SessionState> & { refreshToken?: string };
        delete state.refreshToken;
        return state;
      },
    }
  )
);
