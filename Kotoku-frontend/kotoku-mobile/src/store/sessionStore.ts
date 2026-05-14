import { create } from "zustand";

interface SessionState {
  token: string | null;
  phone: string | null;
  accountId: number | null;
  pinConfigured: boolean;
  isAuthenticated: boolean;
  setSession: (token: string, phone: string, accountId: number, pinConfigured?: boolean) => void;
  setPinConfigured: (configured: boolean) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  token: null,
  phone: null,
  accountId: null,
  pinConfigured: false,
  isAuthenticated: false,
  setSession: (token, phone, accountId, pinConfigured = false) =>
    set({ token, phone, accountId, pinConfigured, isAuthenticated: true }),
  setPinConfigured: (configured) =>
    set({ pinConfigured: configured }),
  clearSession: () =>
    set({ token: null, phone: null, accountId: null, pinConfigured: false, isAuthenticated: false }),
}));
