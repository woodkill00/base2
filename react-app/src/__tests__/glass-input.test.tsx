import React from 'react';
import { render, screen } from '@testing-library/react';
import GlassInput from '../components/glass/GlassInput';

describe('GlassInput', () => {
  test('associates label and input', () => {
    render(<GlassInput id="email" label="Email" value="" onChange={() => {}} />);
    const input = screen.getByLabelText('Email');
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('id', 'email');
  });

  test('shows error state', () => {
    render(<GlassInput id="email" label="Email" value="" error="Required" onChange={() => {}} />);
    expect(screen.getByText('Required')).toBeInTheDocument();
  });
});
