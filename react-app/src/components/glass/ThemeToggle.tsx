import React, { useCallback, useMemo, useState } from 'react';
import { setThemeCookie, getThemeCookie, applyThemeClass } from '../../services/theme/persistence';

export const ThemeToggle: React.FC = () => {
  const initialTheme = useMemo(() => {
    const cookieTheme = getThemeCookie();
    if (cookieTheme) return cookieTheme;
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' : 'light';
  }, []);

  const [theme, setTheme] = useState<'light' | 'dark'>(initialTheme);

  const toggle = useCallback(() => {
    const next: 'light' | 'dark' = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    setThemeCookie(next);
    applyThemeClass(next);
  }, [theme]);

  return (
    <button aria-label="Toggle theme" className="glass glass-interactive" onClick={toggle}>
      {theme === 'dark' ? '🌙' : '☀️'}
    </button>
  );
};

export default ThemeToggle;
