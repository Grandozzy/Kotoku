import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SessionState {
  accountId: number | null;
  phone: string | null;
  isAuthenticated: boolean;
  setSession: (accountId: number, phone: string) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      accountId: null,
      phone: null,
      isAuthenticated: false,
      setSession: (accountId, phone) =>
        set({ accountId, phone, isAuthenticated: true }),
      clearSession: () =>
        set({ accountId: null, phone: null, isAuthenticated: false }),
    }),
    { name: "kotoku-session" }
  )
);
