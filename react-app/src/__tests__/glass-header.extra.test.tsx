import React from 'react';
import { render, screen } from '@testing-library/react';
import GlassHeader from '../components/glass/GlassHeader';

describe('GlassHeader extra coverage', () => {
  test('renders with default title when none provided', () => {
    render(<GlassHeader />);
    expect(screen.getByText('App Shell')).toBeInTheDocument();
  });
});
