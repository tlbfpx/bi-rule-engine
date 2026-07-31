import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  token: string | null;
  username: string | null;
  role: string | null;
  displayName: string | null;
  isAuthenticated: boolean;
  login: (data: { token: string; username: string; role: string; display_name?: string | null }) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      username: null,
      role: null,
      displayName: null,
      isAuthenticated: false,
      login: (data) =>
        set({
          token: data.token,
          username: data.username,
          role: data.role,
          displayName: data.display_name || null,
          isAuthenticated: true,
        }),
      logout: () =>
        set({
          token: null,
          username: null,
          role: null,
          displayName: null,
          isAuthenticated: false,
        }),
    }),
    { name: 'auth-store' },
  ),
);
