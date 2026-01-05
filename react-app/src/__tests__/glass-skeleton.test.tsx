import React from 'react';
import { render, screen } from '@testing-library/react';
import GlassSkeleton from '../components/glass/GlassSkeleton';

describe('GlassSkeleton', () => {
  test('renders with width and height', () => {
    render(<GlassSkeleton width={100} height={20} />);
    expect(screen.getByTestId('glass-skeleton')).toBeInTheDocument();
  });
});
