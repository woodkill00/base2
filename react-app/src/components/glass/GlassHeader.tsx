import React from 'react';
import ThemeToggle from './ThemeToggle';

type Props = { title?: string };

export const GlassHeader: React.FC<Props> = ({ title = 'App Shell' }) => {
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
      <ThemeToggle />
    </header>
  );
};

export default GlassHeader;
