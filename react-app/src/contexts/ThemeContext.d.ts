import type { Context, ReactNode } from 'react';
import type { Transition } from 'motion/react';

export interface AppearancePreferences {
  version: number;
  theme: 'system' | 'light' | 'dark';
  contrast: 'system' | 'standard' | 'high';
  motion: 'system' | 'full' | 'reduced';
  density: 'comfortable' | 'compact';
}
export interface ThemeValue {
  hasProvider: boolean;
  theme: 'light' | 'dark';
  motion: 'full' | 'reduced';
  setTheme: (theme: 'light' | 'dark') => void;
  toggleTheme: () => void;
  applyAccountPreferences: (
    preferences: AppearancePreferences,
    accountId: string | number,
    options?: { preserveTemporary?: boolean }
  ) => boolean;
}
export const ThemeContext: Context<ThemeValue>;
export function ThemeProvider(props: {
  children?: ReactNode;
  accountId?: string | number | null;
  authenticationLoading?: boolean;
}): ReactNode;
export function useAppearanceMotion(): {
  reducedMotion: boolean;
  transition: (value: Transition) => Transition;
};
export default ThemeProvider;
