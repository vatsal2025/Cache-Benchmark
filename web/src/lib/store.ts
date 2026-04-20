import { create } from "zustand";

interface AuthState {
  token: string | null;
  orgId: string | null;
  login: (token: string, orgId: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: sessionStorage.getItem("token"),
  orgId: sessionStorage.getItem("orgId"),
  login: (token, orgId) => {
    sessionStorage.setItem("token", token);
    sessionStorage.setItem("orgId", orgId);
    set({ token, orgId });
  },
  logout: () => {
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("orgId");
    set({ token: null, orgId: null });
  },
}));
