import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Moon, Sun } from 'lucide-react';
import { motion } from 'motion/react';

import ThemeToggle from './ThemeToggle';
import GlassButton from './GlassButton';
import { applyThemeClass, setThemeCookie } from '../../services/theme/persistence';

type Props = {
  title?: string;
  variant?: 'public' | 'app';
  menuControlsId?: string;
  isMenuOpen?: boolean;
  onToggleMenu?: () => void;
};

export const GlassHeader: React.FC<Props> = ({
  title = 'App Shell',
  variant,
  menuControlsId,
  isMenuOpen,
  onToggleMenu,
}) => {
  const navigate = useNavigate();
  const inferredPublic = useMemo(() => title?.toLowerCase() === 'home', [title]);
  const isPublic = variant ? variant === 'public' : inferredPublic;

  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    if (!isPublic) return;
    const isDarkMode = document.documentElement.classList.contains('dark');
    setIsDark(isDarkMode);
  }, [isPublic]);

  const toggleTheme = () => {
    const nextTheme: 'light' | 'dark' = isDark ? 'light' : 'dark';
    setIsDark(!isDark);
    applyThemeClass(nextTheme);
    setThemeCookie(nextTheme);
  };

  if (isPublic) {
    return (
      <header className="sticky top-0 z-50 w-full">
        <nav
          aria-label="Public header"
          className="backdrop-blur-2xl bg-white/25 dark:bg-black/40 border-b border-white/30 dark:border-white/20 shadow-[0_4px_16px_0_rgba(31,38,135,0.1)] dark:shadow-[0_4px_16px_0_rgba(0,0,0,0.3)]"
          style={{ height: 'calc(3.5rem + 1px)' }}
        >
          <div
            className="mx-auto flex items-center justify-between h-full"
            style={{
              padding: 'calc(0.75rem) calc(max(1rem, calc((100vw - 1200px) / 2)))',
            }}
          >
            <div className="flex items-center gap-2">
              <svg
                width="32"
                height="32"
                viewBox="0 0 32 32"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="text-foreground"
                aria-hidden="true"
              >
                <path d="M16 4L4 10L16 16L28 10L16 4Z" fill="currentColor" opacity="0.3" />
                <path
                  d="M4 16L16 22L28 16"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M4 22L16 28L28 22"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span className="text-lg font-medium">SpecKit</span>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={toggleTheme}
                className="p-2 rounded-[var(--radius-lg)] hover:bg-white/30 dark:hover:bg-black/50 transition-all duration-300 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40 dark:focus-visible:ring-white/30 hover:-translate-y-0.5"
                aria-label="Toggle theme"
              >
                <motion.div
                  animate={{ rotate: isDark ? 180 : 0 }}
                  transition={{ duration: 0.3, ease: 'easeOut' }}
                >
                  {isDark ? (
                    <Sun className="w-5 h-5" aria-hidden="true" />
                  ) : (
                    <Moon className="w-5 h-5" aria-hidden="true" />
                  )}
                </motion.div>
              </button>

              <div className="hidden sm:flex items-center gap-2">
                <GlassButton
                  variant="ghost"
                  className="text-sm px-4 py-2"
                  onClick={() => navigate('/login')}
                >
                  Login
                </GlassButton>
                <GlassButton
                  variant="primary"
                  className="text-sm px-4 py-2"
                  onClick={() => navigate('/signup')}
                >
                  Sign Up
                </GlassButton>
              </div>
            </div>
          </div>
        </nav>
      </header>
    );
  }

  return (
    <header
      className="glass"
      style={{
        height: 'var(--header-h)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
      }}
    >
      <button
        type="button"
        className="glass glass-interactive glass-btn glass-btn-ghost"
        aria-label="Menu"
        aria-controls={menuControlsId}
        aria-expanded={Boolean(isMenuOpen)}
        onClick={onToggleMenu}
        style={{ width: 40, height: 40, display: 'grid', placeItems: 'center', padding: 0 }}
      >
        <svg
          role="img"
          aria-label="Menu"
          viewBox="0 0 24 24"
          width="18"
          height="18"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </button>

      <h1 style={{ fontSize: 18, margin: 0 }}>{title}</h1>
      <div style={{ flex: 1 }} />
      <ThemeToggle />
    </header>
  );
};

export default GlassHeader;
