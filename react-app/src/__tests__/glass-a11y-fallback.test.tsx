import React from 'react';
import { render } from '@testing-library/react';
import { axe } from 'jest-axe';
import GlassButton from '../components/glass/GlassButton';

describe('Accessibility in fallback mode', () => {
  test('no violations on button in fallback', async () => {
    document.documentElement.classList.add('no-backdrop');
    const { container } = render(<GlassButton variant="primary">Click</GlassButton>);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
