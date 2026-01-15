import React, { useMemo } from 'react';
import ThemeToggle from './ThemeToggle';
import GlassInput from './GlassInput';

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
  const inferredPublic = useMemo(() => title?.toLowerCase() === 'home', [title]);
  const isPublic = variant ? variant === 'public' : inferredPublic;
  const showSearch = isPublic && inferredPublic;
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
      {isPublic ? (
        <div style={{ width: 40 }} />
      ) : (
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
      )}

      <h1 style={{ fontSize: 18, margin: 0 }}>{title}</h1>
      {showSearch ? (
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center', padding: '0 8px' }}>
          <GlassInput
            id="header-search"
            label={undefined}
            name="headerSearch"
            type="text"
            value={''}
            onChange={() => {}}
            placeholder="Search…"
            ariaInvalid="false"
          />
        </div>
      ) : (
        <div style={{ flex: 1 }} />
      )}
      <ThemeToggle />
    </header>
  );
};

export default GlassHeader;
