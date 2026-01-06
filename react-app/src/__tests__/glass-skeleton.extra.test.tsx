import React from 'react';
import { render, screen } from '@testing-library/react';
import GlassSkeleton from '../components/glass/GlassSkeleton';

describe('GlassSkeleton extra coverage', () => {
  test('renders rounded variant', () => {
    render(<GlassSkeleton width={80} height={16} rounded className="extra" />);
    const skel = screen.getByTestId('glass-skeleton');
    expect(skel.className).toContain('glass-skeleton-rounded');
    expect(skel.className).toContain('extra');
  });
});
