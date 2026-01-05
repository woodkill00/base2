import React from 'react';
import { render } from '@testing-library/react';
import { ensureBackdropSupport } from '../services/glass/supports';
import GlassCard from '../components/glass/GlassCard';
import GlassButton from '../components/glass/GlassButton';

describe('Glass components fallback when backdrop-filter unsupported', () => {
  afterEach(() => {
    document.documentElement.classList.remove('no-backdrop');
  });

  it('adds no-backdrop root class and renders components', () => {
    global.CSS = { supports: () => false } as any;
    ensureBackdropSupport();
    const { getByTestId } = render(<GlassCard><button className="glass glass-interactive">Click</button></GlassCard>);
    expect(document.documentElement.classList.contains('no-backdrop')).toBe(true);
    expect(getByTestId('glass-card')).toBeInTheDocument();
  });
});
