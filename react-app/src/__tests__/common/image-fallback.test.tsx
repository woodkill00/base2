import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ImageWithFallback from '../../components/common/ImageWithFallback';

describe('ImageWithFallback', () => {
  test('renders with alt text and role img', () => {
    render(<ImageWithFallback src="/non-existent.svg" alt="Hero" onErrorSrc="/fallback.svg" />);
    const img = screen.getByRole('img', { name: /Hero/i });
    expect(img).toBeInTheDocument();
  });
});
