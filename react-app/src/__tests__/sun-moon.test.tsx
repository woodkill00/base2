import React from 'react';
import { render, screen } from '@testing-library/react';
import SunMoon from '../components/glass/icons/SunMoon';

describe('SunMoon icon', () => {
  test('renders sun variant with aria', () => {
    render(<SunMoon theme="light" />);
    expect(screen.getByRole('img', { name: /sun/i })).toBeInTheDocument();
  });
  test('renders moon variant with aria', () => {
    render(<SunMoon theme="dark" />);
    expect(screen.getByRole('img', { name: /moon/i })).toBeInTheDocument();
  });
});
