import { create } from "zustand";

interface SessionState {
  token: string | null;
  phone: string | null;
  accountId: number | null;
  isAuthenticated: boolean;
  setSession: (token: string, phone: string, accountId: number) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  token: null,
  phone: null,
  accountId: null,
  isAuthenticated: false,
  setSession: (token, phone, accountId) =>
    set({ token, phone, accountId, isAuthenticated: true }),
  clearSession: () =>
    set({ token: null, phone: null, accountId: null, isAuthenticated: false }),
}));
