import React from 'react';
import { render, screen } from '@testing-library/react';
import GlassSpinner from '../components/glass/GlassSpinner';

describe('GlassSpinner', () => {
  test('renders with size', () => {
    render(<GlassSpinner size="md" />);
    expect(screen.getByTestId('glass-spinner')).toBeInTheDocument();
  });
});
