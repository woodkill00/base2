import React from 'react';
import { render, screen } from '@testing-library/react';
import GlassSpinner from '../components/glass/GlassSpinner';

describe('GlassSpinner extra coverage', () => {
  test('renders sm, default md, and lg sizes with custom class', () => {
    const { rerender } = render(<GlassSpinner size="sm" className="extra" />);
    let spinner = screen.getByTestId('glass-spinner');
    expect(spinner.querySelector('.glass-spinner-circle')!.className).toContain('glass-spinner-sm');
    expect(spinner.className).toContain('extra');

    // default (md)
    rerender(<GlassSpinner />);
    spinner = screen.getByTestId('glass-spinner');
    expect(spinner.querySelector('.glass-spinner-circle')!.className).toContain('glass-spinner-md');

    rerender(<GlassSpinner size="lg" />);
    spinner = screen.getByTestId('glass-spinner');
    expect(spinner.querySelector('.glass-spinner-circle')!.className).toContain('glass-spinner-lg');
  });
});
