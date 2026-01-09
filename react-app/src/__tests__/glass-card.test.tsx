import React from 'react';
import { render, screen } from '@testing-library/react';
import GlassCard from '../components/glass/GlassCard';

describe('GlassCard', () => {
  test('renders with base glass classes', () => {
    render(<GlassCard><p>Content</p></GlassCard>);
    const card = screen.getByTestId('glass-card');
    expect(card.className).toContain('glass');
    expect(card.className).toContain('glass-card');
  });
});
