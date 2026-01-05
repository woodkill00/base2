import React from 'react';
import { render, screen } from '@testing-library/react';
import GlassButton from '../components/glass/GlassButton';

describe('GlassButton variants', () => {
  test('renders primary variant with classes', () => {
    render(<GlassButton variant="primary">Primary</GlassButton>);
    const btn = screen.getByRole('button', { name: 'Primary' });
    expect(btn.className).toContain('glass');
    expect(btn.className).toContain('glass-interactive');
    expect(btn.className).toContain('glass-btn');
    expect(btn.className).toContain('glass-btn-primary');
  });

  test('renders secondary variant with classes', () => {
    render(<GlassButton variant="secondary">Secondary</GlassButton>);
    const btn = screen.getByRole('button', { name: 'Secondary' });
    expect(btn.className).toContain('glass-btn-secondary');
  });

  test('renders ghost variant and disabled state', () => {
    render(<GlassButton variant="ghost" disabled>Ghost</GlassButton>);
    const btn = screen.getByRole('button', { name: 'Ghost' });
    expect(btn.className).toContain('glass-btn-ghost');
    expect(btn).toBeDisabled();
  });
});
