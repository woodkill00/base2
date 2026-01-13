import React, { createContext, useCallback, useEffect, useMemo, useState } from 'react';
import { setThemeCookie, getThemeCookie, applyThemeClass } from '../services/theme/persistence';

export const ThemeContext = createContext({
  theme: 'light',
  setTheme: (_t) => {},
  toggleTheme: () => {},
});

export const ThemeProvider = ({ children }) => {
  const initialTheme = useMemo(() => {
    const cookieTheme = typeof document !== 'undefined' ? getThemeCookie() : null;
    if (cookieTheme) return cookieTheme;
    const prefersDark =
      typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' : 'light';
  }, []);

  const [theme, setThemeState] = useState(initialTheme);

  useEffect(() => {
    applyThemeClass(theme);
    setThemeCookie(theme);
  }, [theme]);

  const setTheme = useCallback((next) => {
    setThemeState(next === 'dark' ? 'dark' : 'light');
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export default ThemeProvider;
