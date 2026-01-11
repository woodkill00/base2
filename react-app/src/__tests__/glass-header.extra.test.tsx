import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import GlassHeader from '../components/glass/GlassHeader';

describe('GlassHeader extra coverage', () => {
  test('renders with default title when none provided', () => {
    render(<GlassHeader />);
    expect(screen.getByText('App Shell')).toBeInTheDocument();
  });

  test('renders public search input when title is Home', () => {
    render(<GlassHeader title="Home" />);
    // Decorative search input should be present
    expect(screen.getByPlaceholderText('Search…')).toBeInTheDocument();
    const input = screen.getByPlaceholderText('Search…') as HTMLInputElement;
    input.focus();
    // Trigger onChange to cover inline handler via React change event
    fireEvent.change(input, { target: { value: 'abc' } });
  });
});
