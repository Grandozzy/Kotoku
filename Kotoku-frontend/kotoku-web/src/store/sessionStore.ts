import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SessionState {
  accountId: number | null;
  phone: string | null;
  token: string | null;
  isAuthenticated: boolean;
  setSession: (token: string, accountId: number, phone: string) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      accountId: null,
      phone: null,
      token: null,
      isAuthenticated: false,
      setSession: (token, accountId, phone) =>
        set({ token, accountId, phone, isAuthenticated: true }),
      clearSession: () =>
        set({ token: null, accountId: null, phone: null, isAuthenticated: false }),
    }),
    { name: "kotoku-session" }
  )
);
