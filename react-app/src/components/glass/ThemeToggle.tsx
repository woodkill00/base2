import React, { useCallback, useContext, useMemo, useState } from 'react';
import { ThemeContext } from '../../contexts/ThemeContext';
import { setThemeCookie, getThemeCookie, applyThemeClass } from '../../services/theme/persistence';

export const ThemeToggle: React.FC<{ label?: string }> = ({ label = 'Toggle theme' }) => {
  const context = useContext(ThemeContext);
  const initialTheme = useMemo(() => {
    const cookieTheme = getThemeCookie();
    if (cookieTheme) return cookieTheme;
    const prefersDark =
      window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' : 'light';
  }, []);

  const [theme, setTheme] = useState<'light' | 'dark'>(initialTheme);

  const toggle = useCallback(() => {
    if (context.hasProvider) {
      context.toggleTheme();
      return;
    }
    const next: 'light' | 'dark' = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    setThemeCookie(next);
    applyThemeClass(next);
  }, [theme, context]);

  return (
    <button
      aria-label={label}
      className="glass glass-interactive glass-pill min-h-11 min-w-11"
      onClick={toggle}
    >
      {(context.hasProvider ? context.theme : theme) === 'dark' ? '🌙' : '☀️'}
    </button>
  );
};

export default ThemeToggle;
