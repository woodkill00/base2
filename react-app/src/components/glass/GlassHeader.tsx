import React, { useMemo } from 'react';
import ThemeToggle from './ThemeToggle';
import GlassInput from './GlassInput';

type Props = { title?: string };

export const GlassHeader: React.FC<Props> = ({ title = 'App Shell' }) => {
  const isPublic = useMemo(() => title?.toLowerCase() === 'home', [title]);
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
      <h1 style={{ fontSize: 18, margin: 0 }}>{title}</h1>
      {isPublic ? (
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
