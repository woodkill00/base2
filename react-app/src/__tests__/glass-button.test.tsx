import React from 'react';
import { render, screen } from '@testing-library/react';
import GlassButton from '../components/glass/GlassButton';

describe('GlassButton variants', () => {
  test('renders primary variant with classes', () => {
    render(<GlassButton variant="primary">Primary</GlassButton>);
    const btn = screen.getByRole('button', { name: 'Primary' });
    expect(btn.className).toContain('backdrop-blur-2xl');
    expect(btn.className).toContain('bg-white/25');
    expect(btn.className).toContain('border-white/40');
  });

  test('renders secondary variant with classes', () => {
    render(<GlassButton variant="secondary">Secondary</GlassButton>);
    const btn = screen.getByRole('button', { name: 'Secondary' });
    expect(btn.className).toContain('bg-white/20');
    expect(btn.className).toContain('border-white/30');
  });

  test('renders ghost variant and disabled state', () => {
    render(<GlassButton variant="ghost" disabled>Ghost</GlassButton>);
    const btn = screen.getByRole('button', { name: 'Ghost' });
    expect(btn.className).toContain('bg-transparent');
    expect(btn).toBeDisabled();
  });
});
