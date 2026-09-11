import type { ReactNode } from 'react';

export interface AuthUser {
  permissions?: string[];
  [field: string]: unknown;
}
export interface AuthState {
  user: AuthUser | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  register(email: string, password: string, name?: string): Promise<unknown>;
  loginWithEmail(email: string, password: string): Promise<unknown>;
  completeMfaLogin(challengeToken: string, code: string): Promise<unknown>;
  loginWithGoogle(credential: string): Promise<unknown>;
  login(user: AuthUser, token?: string | null): void;
  logout(): Promise<void>;
  updateUser(user: Partial<AuthUser>): void;
  verifyEmail(token: string): Promise<unknown>;
  forgotPassword(email: string): Promise<unknown>;
  resetPassword(token: string, password: string): Promise<unknown>;
}
export function useAuth(): AuthState;
export function AuthProvider(props: { children?: ReactNode }): ReactNode;
