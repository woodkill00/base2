import React from 'react';
import { render, screen } from '@testing-library/react';
import GlassCard from '../components/glass/GlassCard';

describe('GlassCard extra coverage', () => {
  test('interactive + variant + custom className', () => {
    render(
      <GlassCard interactive variant="elevated" className="extra">
        <p>Content</p>
      </GlassCard>
    );
    const card = screen.getByTestId('glass-card');
    expect(card.className).toContain('glass-interactive');
    expect(card.className).toContain('glass-card-elevated');
    expect(card.className).toContain('extra');
  });
});
